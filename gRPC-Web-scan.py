"""
gRPC-Web-Scan
Extracting Methods, Services and Messages (Routes) in JS files (grpc-web)
"""

import re
from argparse import ArgumentParser
import sys
import jsbeautifier
from texttable import Texttable
import glob
import os
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict
import json
from colorama import init, Fore, Style  # 添加颜色支持
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

# 初始化colorama
init()

# 在文件开头添加 HTML_TEMPLATE 的定义
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>gRPC-Web-Scan Report</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.24.1/themes/prism-tomorrow.min.css" rel="stylesheet" />
    <link href="https://fonts.googleapis.com/css2?family=SF+Pro+Display:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {{
            --primary-color: #007AFF;
            --secondary-color: #5856D6;
            --success-color: #34C759;
            --bg-color: #F5F5F7;
            --card-bg: #FFFFFF;
            --text-primary: #1D1D1F;
            --text-secondary: #86868B;
            --border-radius: 12px;
            --spacing: 24px;
        }}

        body {{
            font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-primary);
            line-height: 1.6;
            padding: var(--spacing);
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: var(--spacing);
        }}

        .header {{
            text-align: center;
            margin-bottom: calc(var(--spacing) * 2);
        }}

        .header h1 {{
            font-weight: 600;
            font-size: 2.5rem;
            margin-bottom: var(--spacing);
            background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}

        .lead {{
            font-size: 1.1rem;
            color: #4a4a4a;
            line-height: 1.6;
        }}

        .workflow-list {{
            padding-left: 20px;
            margin-top: 10px;
        }}

        .workflow-list li {{
            margin-bottom: 8px;
            color: #4a4a4a;
            line-height: 1.5;
        }}

        .tool-description {{
            background-color: var(--card-bg);
            border-radius: var(--border-radius);
            padding: calc(var(--spacing) * 1.5);
            margin-bottom: calc(var(--spacing) * 1.5);
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
        }}

        .feature-list {{
            list-style: none;
            padding-left: 0;
        }}

        .feature-list li {{
            margin-bottom: 12px;
            padding-left: 28px;
            position: relative;
            color: #4a4a4a;
        }}

        .feature-list li:before {{
            content: "✓";
            position: absolute;
            left: 0;
            color: var(--success-color);
            font-weight: bold;
        }}

        .summary-card {{
            background-color: var(--card-bg);
            border-radius: var(--border-radius);
            padding: calc(var(--spacing) * 1.5);
            margin-bottom: calc(var(--spacing) * 1.5);
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
        }}

        .example-data {{
            background-color: #1E1E1E;
            border-radius: var(--border-radius);
            padding: calc(var(--spacing));
            margin: var(--spacing) 0;
            border: 1px solid #2D2D2F;
        }}

        .example-title {{
            color: #E0E0E0;
            margin-bottom: calc(var(--spacing) / 2);
            font-size: 1rem;
            font-weight: 500;
            padding-bottom: 8px;
            border-bottom: 1px solid #404040;
        }}

        .example-data pre {{
            margin: 0;
            padding: 12px;
            background-color: #2D2D2F !important;
            border-radius: 6px;
        }}

        .example-data code {{
            color: #56B6C2 !important;
            font-family: 'SF Mono', Menlo, Monaco, Consolas, monospace !important;
            font-size: 0.9rem !important;
            line-height: 1.5 !important;
        }}

        .proto-section {{
            background-color: #1E1E1E;
            border-radius: var(--border-radius);
            padding: calc(var(--spacing) * 1.5);
            margin-top: calc(var(--spacing) * 2);
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
        }}

        .proto-title {{
            color: #E0E0E0;
            margin-bottom: var(--spacing);
            font-size: 1.2rem;
            font-weight: 500;
            border-bottom: 1px solid #404040;
            padding-bottom: 10px;
        }}

        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: var(--spacing);
            margin-top: var(--spacing);
        }}

        .stat-item {{
            text-align: center;
            padding: var(--spacing);
            background: linear-gradient(135deg, rgba(0, 122, 255, 0.1), rgba(88, 86, 214, 0.1));
            border-radius: calc(var(--border-radius) / 2);
        }}

        .stat-value {{
            font-size: 2rem;
            font-weight: 600;
            color: var(--primary-color);
        }}

        .stat-label {{
            color: var(--text-secondary);
            font-size: 0.9rem;
            margin-top: 5px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>gRPC-Web-Scan Report</h1>
            <p class="text-secondary">Generated on {timestamp}</p>
        </div>

        <div class="tool-description">
            <h4 class="mb-4">关于 gRPC-Web-Scan</h4>
            <p class="lead mb-4">gRPC-Web-Scan 是一个专门用于分析和逆向工程 gRPC-Web 应用的自动化工具。它能够从 JavaScript/TypeScript 文件中提取 gRPC 服务定义，生成示例数据并自动生成对应的 Proto 文件。</p>
            
            <div class="row mt-4">
                <div class="col-md-6">
                    <h5 class="mb-3">核心功能</h5>
                    <ul class="feature-list">
                        <li>自动扫描并解析 gRPC-Web 的 JavaScript/TypeScript 文件</li>
                        <li>提取 gRPC 服务定义、消息类型和端点信息</li>
                        <li>从 JS/TS 代码逆向生成 Proto 文件定义</li>
                        <li>自动生成字段类型和示例数据</li>
                        <li>支持递归扫描目录和并发处理</li>
                        <li>生成结构化的HTML报告</li>
                    </ul>
                </div>
                <div class="col-md-6">
                    <h5 class="mb-3">应用场景</h5>
                    <ul class="feature-list">
                        <li>gRPC-Web 应用的逆向工程</li>
                        <li>API 接口分析和文档生成</li>
                        <li>服务端点和消息结构的快速发现</li>
                        <li>Proto 文件的自动重建</li>
                        <li>gRPC 服务的安全测试</li>
                        <li>API 兼容性验证</li>
                    </ul>
                </div>
            </div>
        </div>

        <div class="summary-card">
            <h4>扫描概要</h4>
            <div class="summary-grid">
                <div class="stat-item">
                    <div class="stat-value">{total_files}</div>
                    <div class="stat-label">扫描文件数</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{total_services}</div>
                    <div class="stat-label">发现服务数</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{total_messages}</div>
                    <div class="stat-label">消息类型数</div>
                </div>
            </div>
        </div>

        {file_results}
    </div>
</body>
</html>
"""

FILE_SECTION_TEMPLATE = """
<div class="file-section">
    <h3>{file_path}</h3>
    {error_section}
    {messages_section}
    {proto_section}
</div>
"""

@dataclass
class FileResult:
    file_path: str
    endpoints: List[str] = field(default_factory=list)
    messages: Dict[str, List[List[str]]] = field(default_factory=dict)
    services: List[str] = field(default_factory=list)
    metadata: List[str] = field(default_factory=list)  # 新增：元数据
    error_handlers: List[str] = field(default_factory=list)  # 新增：错误处理
    interceptors: List[str] = field(default_factory=list)  # 新增：拦截器
    error: str = None
    proto_content: str = None

@dataclass
class ScanResult:
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    files: List[FileResult] = field(default_factory=list)
    
    def add_file_result(self, result: FileResult):
        self.files.append(result)
        
    @property
    def total_files(self):
        return len(self.files)
        
    @property
    def total_endpoints(self):
        return sum(len(f.endpoints) for f in self.files if f.error is None)
        
    @property
    def total_messages(self):
        return sum(len(f.messages) for f in self.files if f.error is None)
        
    @property
    def total_services(self):
        return sum(len(f.services) for f in self.files if f.error is None)

@dataclass
class ProtoResult:
    """Proto文件解析结果"""
    package: str
    services: List[Dict[str, any]] = field(default_factory=list)
    messages: List[Dict[str, any]] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    options: Dict[str, str] = field(default_factory=dict)

def create_table(columns_list, rows_list):
    table = Texttable()

    table_list = [columns_list]
    for i in rows_list:
        table_list.append(i)
    table.add_rows(table_list)
    table_string = table.draw()
    # indented_table_string = '    ' + table_string.replace('\n', '\n    ')  # Add space before each line

    return table_string


def beautify_js_content(content):
    try:
        beautified = jsbeautifier.beautify(content)

    except Exception as e:
        print('An error occurred in beautifying Javascript code: ' + str(e))
        print('Enter valid javascript code. Do not copy js code '
              'from browser dev tools directly! try to download it directly!')
        print('If you are still getting this error, try to beautify Javascript code online and then use this tool!')
        exit(1)

    return beautified


def extract_endpoints(content):
    """提取gRPC端点"""
    patterns = [
        # 基本端点模式
        r'MethodDescriptor\("(\/[^"]+)"',  # 标准gRPC-web端
        r'\.([a-zA-Z]+Service)\.([a-zA-Z]+)\s*=\s*{',  # 服务方法定义
        r'\.unary\([\'"](.+?)[\'"]\s*,',  # unary调用
        r'\.serverStreaming\([\'"](.+?)[\'"]\s*,',  # 流式调用
        
        # 新增：更多端点模
        r'@rpc\.method\([\'"]([^\'\"]+)[\'"]\)',  # RPC方法装饰器
        r'\.registerService\([\'"]([^\'\"]+)[\'"]\)',  # 服务注册
        r'\.handleUnaryCall\([\'"]([^\'\"]+)[\'"]\)',  # 一元调用处理
        r'\.handleServerStreamingCall\([\'"]([^\'\"]+)[\'"]\)',  # 服务端流式处理
        r'\.handleClientStreamingCall\([\'"]([^\'\"]+)[\'"]\)',  # 客户端流式处理
        r'\.handleBidiStreamingCall\([\'"]([^\'\"]+)[\'"]\)',  # 双向流式处理
    ]
    
    endpoints = set()
    for pattern in patterns:
        matches = re.finditer(pattern, content)
        for match in matches:
            endpoint = match.group(1)
            if not endpoint.startswith('/'):
                endpoint = f"/{endpoint}"
            endpoints.add(endpoint)
    
    return list(endpoints)


def extract_messages(content):
    """提取gRPC消息定义"""
    patterns = [
        # 基本消息模式
        r'proto\.(.*)\.prototype\.set(.*).*=.*function\(.*\).*{\s*.*set(.*)\(.*?,(.*?),',
        
        # 新增：更多消息模式
        r'message\s+([a-zA-Z0-9_]+)\s*{([^}]+)}',  # proto消息定义
        r'class\s+([a-zA-Z0-9_]+)\s+extends\s+protobuf\.Message',  # 继承自Message
        r'@protobuf\.Type\([\'"]([^\'\"]+)[\'"]\)',  # 类型装饰器
        r'new\s+proto\.([a-zA-Z0-9_]+)\(',  # 消息实例化
    ]
    
    message_list = {}
    
    # 处理基本消息模式
    basic_pattern = re.compile(patterns[0])
    matched_items = basic_pattern.findall(content)
    for m in matched_items:
        if m[0].strip() not in message_list:
            message_list[m[0]] = []
        if m[1].strip() not in message_list[m[0].strip()]:
            temp_list = [m[1].strip(), m[2].strip(), m[3].strip()]
            message_list[m[0]].append(temp_list)
    
    # 处理新增的消息模式
    for pattern in patterns[1:]:
        matches = re.finditer(pattern, content)
        for match in matches:
            msg_name = match.group(1)
            if msg_name not in message_list:
                message_list[msg_name] = []
            # 尝试提取字段信息
            if len(match.groups()) > 1:
                fields_content = match.group(2)
                field_pattern = r'(\w+)\s+(\w+)\s*=\s*(\d+)'
                field_matches = re.finditer(field_pattern, fields_content)
                for field_match in field_matches:
                    field_type, field_name, field_number = field_match.groups()
                    if [field_name, field_type, field_number] not in message_list[msg_name]:
                        message_list[msg_name].append([field_name, field_type, field_number])
    
    return message_list


def extract_services(content):
    """Extract gRPC service definitions"""
    patterns = [
        r'class\s+([a-zA-Z0-9_]+)Client\s*{',  # Client class
        r'\.([a-zA-Z0-9_]+Service)\s*=\s*{',  # Service definition
        r'@protobuf\.Service\([\'"]([^\'\"]+)[\'"]\)',  # Protobuf decorator
        r'class\s+([a-zA-Z0-9_]+)ServiceImpl\s*',  # Service implementation
        r'class\s+([a-zA-Z0-9_]+)Server\s*',  # Server class
        r'\.addService\(([a-zA-Z0-9_]+)\.service\)',  # Service addition
        r'@Service\([\'"]([^\'\"]+)[\'"]\)',  # Service annotation
        r'new\s+([a-zA-Z0-9_]+)Service\(',  # Service instantiation
        r'proto\.([a-zA-Z0-9_]+)Service\s*=',  # Proto service definition
        r'var\s+([a-zA-Z0-9_]+)Service\s*=',  # Service variable
        r'const\s+([a-zA-Z0-9_]+)Service\s*=',  # Service constant
        r'([a-zA-Z0-9_]+)Service\.service\s*=',  # Service object
        r'([a-zA-Z0-9_]+)Client\.service\s*=',  # Client service
        r'([a-zA-Z0-9_]+)\.ServiceClient\s*=',  # Service client definition
    ]
    
    services = set()
    for pattern in patterns:
        matches = re.finditer(pattern, content)
        for match in matches:
            service = match.group(1)
            # Clean up service name
            if service.endswith('Client'):
                service = service[:-6]
            elif service.endswith('ServiceImpl'):
                service = service[:-11]
            elif service.endswith('Server'):
                service = service[:-6]
            elif not service.endswith('Service'):
                service = f"{service}Service"
            services.add(service)
    
    return list(services)


def extract_metadata(content):
    """提取gRPC元数据处理"""
    patterns = [
        r'\.setMetadata\([\'"]([^\'\"]+)[\'"]\s*,',  # 设置元数据
        r'\.getMetadata\([\'"]([^\'\"]+)[\'"]\)',  # 获取元数据
        r'metadata\.set\([\'"]([^\'\"]+)[\'"]\s*,',  # 设置metadata
        r'metadata\.get\([\'"]([^\'\"]+)[\'"]\)',  # 获取metadata
    ]
    
    metadata = set()
    for pattern in patterns:
        matches = re.finditer(pattern, content)
        for match in matches:
            metadata.add(match.group(1))
    
    return list(metadata)


def extract_error_handlers(content):
    """提取gRPC错误处理"""
    patterns = [
        r'\.catch\(\s*function\s*\((.*?)\)',  # 错误捕获
        r'\.on\([\'"]error[\'"]\s*,',  # 错误事件处理
        r'new\s+Error\([\'"]([^\'\"]+)[\'"]\)',  # 错误创建
        r'status\.([A-Z_]+)',  # 状态码
    ]
    
    error_handlers = set()
    for pattern in patterns:
        matches = re.finditer(pattern, content)
        for match in matches:
            if len(match.groups()) > 0:
                error_handlers.add(match.group(1))
    
    return list(error_handlers)


def extract_interceptors(content):
    """提取gRPC拦截器"""
    patterns = [
        r'\.addInterceptor\(([^)]+)\)',  # 添加拦截器
        r'\.intercept\([^)]+\)',  # 拦截方法
        r'class\s+([a-zA-Z0-9_]+)\s+implements\s+Interceptor',  # 拦截器类
        r'@Interceptor\([\'"]([^\'\"]+)[\'"]\)',  # 拦截器装饰器
    ]
    
    interceptors = set()
    for pattern in patterns:
        matches = re.finditer(pattern, content)
        for match in matches:
            if len(match.groups()) > 0:
                interceptors.add(match.group(1))
    
    return list(interceptors)


def read_file(file):
    try:
        with open(file, 'r', encoding='utf-8') as file:
            return file.read()

    except Exception as e:
        print('Error occurred on opening file: ' + str(e))
        exit(1)


def read_standard_input():
    return sys.stdin.read()



def print_parser_help(prog):
    help_msg = f"""
╭──────────────────────── gRPC-Web ────────────────────────╮
│                      作者：荷花                            │
│  A powerful tool for analyzing gRPC services in JS/TS     │
│                                                           │
├──────────────────── Usage Examples ─────────────────────┤
│                                                           │
│  Single file:                                            │
│    {prog} --file example.js                              │
│                                                          │
│  Directory scan:                                         │
│    {prog} --dir ./src                                    │
│                                                          │
├─────────────────── Input Arguments ────────────────────┤
│                                                           │
│  --file    Scan single JavaScript file                   │
│  --dir     Recursively scan directory                    │
│  --stdin   Read from standard input                      │
│                                                          │
├────────────────── Output Arguments ───────────────────┤
│                                                           │
│  --report  Generate HTML report (optional)               │
│                                                          │
├────────────────── Other Arguments ────────────────────┤
│                                                           │
│  --workers Number of concurrent threads (default: 10)     │
│  --help    Show this help message                        │
│                                                           │
╰──────────────────────────────────────────────────────╯
"""
    print(f"{Fore.CYAN}{help_msg}{Style.RESET_ALL}")


def generate_example_value(field_type):
    """根据字段类型生成示例值"""
    type_examples = {
        'Proto3StringField': '{"example_string"}',  # 修正为正确的字符串格式
        'Proto3BytesField': '{"ZXhhbXBsZV9ieXRlcw=="}',  # base64编码的字节
        'Proto3IntField': '123456',  # 数字不需要大括号
        'Proto3UintField': '10000',
        'Proto3Int64Field': '9876543210',
        'Proto3Uint64Field': '9876543210',
        'Proto3BoolField': 'true',  # 布尔值不需要大括号
        'Proto3FloatField': '123.45',
        'Proto3DoubleField': '123.456789',
        'Proto3EnumField': '1',
        'Proto3BooleanField': 'true',  # 添加布尔字段
        'Proto3MessageField': '{}',  # 嵌套消息
        'Proto3TimestampField': '{"2024-03-21T10:00:00Z"}',  # 时间戳格式
        'Proto3DurationField': '{"3600s"}',  # 持续时间格式
    }
    
    # 处理数组类型
    if field_type.startswith('Array<'):
        inner_type = field_type[6:-1]  # 提取数组内部类型
        inner_value = type_examples.get(inner_type, "null")
        return f'[{inner_value}]'
    
    # 处理repeated类型
    if field_type.startswith('Repeated<'):
        inner_type = field_type[9:-1]  # 提取repeated部类型
        inner_value = type_examples.get(inner_type, "null")
        return f'[{inner_value}]'
    
    return type_examples.get(field_type, "null")

def generate_example_data(message_fields):
    """生成示例数据"""
    examples = []
    for field in message_fields:
        field_name, field_type, field_number = field
        example_value = generate_example_value(field_type)
        # 添加HTML span标签用于样式
        examples.append(f'<span class="field-number">{field_number}</span>: <span class="field-value">{example_value}</span>')
    return examples

def process_single_file(file_path, print_results=True):
    try:
        content = read_file(file_path)
        
        # 根据文件类型选择处理方式
        if file_path.endswith('.ts'):
            # 处理TypeScript文件
            ts_results = extract_typescript_grpc(content)
            if print_results:
                print(f"\n{Fore.CYAN}=== Processing TypeScript File: {file_path} ==={Style.RESET_ALL}")
                
                if ts_results['services']:
                    print(f"\n{Fore.GREEN}Found Services:{Style.RESET_ALL}")
                    for service in ts_results['services']:
                        print(f"  {Fore.YELLOW}{service}{Style.RESET_ALL}")
                
                if ts_results['messages']:
                    print(f"\n{Fore.GREEN}Found Messages:{Style.RESET_ALL}")
                    for msg_name, fields in ts_results['messages'].items():
                        print(f"\n{Fore.YELLOW}{msg_name}:{Style.RESET_ALL}")
                        if fields:
                            print(create_table(
                                columns_list=['Field Name', 'Field Type', 'Field Number'],
                                rows_list=fields
                            ))
                
                if ts_results['methods']:
                    print(f"\n{Fore.GREEN}Found Methods:{Style.RESET_ALL}")
                    for method in ts_results['methods']:
                        print(f"  {Fore.YELLOW}{method}{Style.RESET_ALL}")
                        
        else:
            # 处理JavaScript文件
            js_content = beautify_js_content(content)
            endpoints = extract_endpoints(js_content)
            messages = extract_messages(js_content)
            services = extract_services(js_content)
            metadata = extract_metadata(js_content)
            error_handlers = extract_error_handlers(js_content)
            interceptors = extract_interceptors(js_content)
            
            # 生成proto内容
            proto_content = None
            if messages:
                proto_content = generate_proto_content(messages, services)
            
            if print_results:
                print(f"\n{Fore.CYAN}=== Processing {file_path} ==={Style.RESET_ALL}")
                
                if endpoints:
                    print(f"\n{Fore.GREEN}Found Endpoints:{Style.RESET_ALL}")
                    for endpoint in endpoints:
                        print(f"  {Fore.YELLOW}{endpoint}{Style.RESET_ALL}")
                
                if services:
                    print(f"\n{Fore.GREEN}Found Services:{Style.RESET_ALL}")
                    for service in services:
                        print(f"  {Fore.YELLOW}{service}{Style.RESET_ALL}")
                
                if messages:
                    print(f"\n{Fore.GREEN}Found Messages:{Style.RESET_ALL}")
                    for msg_name, msg_fields in messages.items():
                        print(f"\n{Fore.YELLOW}{msg_name}:{Style.RESET_ALL}")
                        print(create_table(
                            columns_list=['Field Name', 'Field Type', 'Field Number'],
                            rows_list=msg_fields
                        ))
                        
                        # 添加示例数据输出
                        print(f"\n{Fore.BLUE}Example Data:{Style.RESET_ALL}")
                        examples = generate_example_data(msg_fields)
                        for example in examples:
                            print(f"  {Fore.CYAN}{example}{Style.RESET_ALL}")
                        print()  # 添加空行分隔
                    
                    # 添加proto文件内容输出
                    if proto_content:
                        print(f"\n{Fore.GREEN}Proto File Definition:{Style.RESET_ALL}")
                        print(f"{Fore.CYAN}{proto_content}{Style.RESET_ALL}")
            
            return FileResult(
                file_path=file_path,
                endpoints=endpoints,
                messages=messages,
                services=services,
                metadata=metadata,
                error_handlers=error_handlers,
                interceptors=interceptors,
                proto_content=proto_content  # 确保设置proto内容
            )
            
    except Exception as e:
        error_msg = str(e)
        if print_results:
            print(f"{Fore.RED}Error processing file {file_path}: {error_msg}{Style.RESET_ALL}")
        return FileResult(file_path=file_path, error=error_msg)

def process_directory(dir_path, print_results=True, max_workers=10):
    """使用并发处理目录"""
    if not os.path.exists(dir_path):
        print(f"{Fore.RED}Directory not found: {dir_path}{Style.RESET_ALL}")
        return ScanResult()  # 返回空的扫描结果而不是退出
        
    scan_result = ScanResult()
    
    if print_results:
        print(f"\n{Fore.CYAN}=== Scanning directory: {dir_path} ==={Style.RESET_ALL}\n")
    
    # 集所有处理的文件
    js_files = []
    ts_files = []
    proto_files = []
    for root, dirs, files in os.walk(dir_path):
        if 'node_modules' in dirs:
            dirs.remove('node_modules')
            
        for file in files:
            if file.endswith('.js'):
                js_files.append(os.path.join(root, file))
            elif file.endswith('.ts'):
                ts_files.append(os.path.join(root, file))
            elif file.endswith('.proto'):
                proto_files.append(os.path.join(root, file))
    
    # 处理所有文件类型
    all_files = js_files + ts_files
    if all_files:
        print(f"\n{Fore.CYAN}Processing Files...{Style.RESET_ALL}")
        # 创建进度条
        pbar = tqdm(total=len(all_files), desc="Scanning files", unit="file")
        
        # 使用线程池进行并发处理
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_file = {
                executor.submit(process_single_file, file_path, False): file_path 
                for file_path in all_files
            }
            
            # 处理完成的任务
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    result = future.result()
                    if result:  # 确保结果不为None
                        scan_result.add_file_result(result)
                    
                    # 更新进度条
                    pbar.update(1)
                    
                    # 如果需要打印结果，在这里打印
                    if print_results and result:
                        rel_path = os.path.relpath(file_path, dir_path)
                        if result.error:
                            pbar.write(f"{Fore.RED}Error in {rel_path}: {result.error}{Style.RESET_ALL}")
                        else:
                            pbar.write(f"\n{Fore.CYAN}=== Results for {rel_path} ==={Style.RESET_ALL}")
                            if result.endpoints:
                                pbar.write(f"{Fore.GREEN}Found Endpoints:{Style.RESET_ALL}")
                                for endpoint in result.endpoints:
                                    pbar.write(f"  {Fore.YELLOW}{endpoint}{Style.RESET_ALL}")
                            if result.services:
                                pbar.write(f"{Fore.GREEN}Found Services:{Style.RESET_ALL}")
                                for service in result.services:
                                    pbar.write(f"  {Fore.YELLOW}{service}{Style.RESET_ALL}")
                            if result.messages:
                                pbar.write(f"{Fore.GREEN}Found Messages:{Style.RESET_ALL}")
                                for msg_name, msg_fields in result.messages.items():
                                    pbar.write(f"\n{Fore.YELLOW}{msg_name}:{Style.RESET_ALL}")
                                    pbar.write(create_table(
                                        columns_list=['Field Name', 'Field Type', 'Field Number'],
                                        rows_list=msg_fields
                                    ))
                                    
                                    # 添加示例数据输出
                                    pbar.write(f"\n{Fore.BLUE}Example Data:{Style.RESET_ALL}")
                                    examples = generate_example_data(msg_fields)
                                    for example in examples:
                                        pbar.write(f"  {Fore.CYAN}{example}{Style.RESET_ALL}")
                                    pbar.write("")  # 添加空行分隔
                
                except Exception as e:
                    pbar.write(f"{Fore.RED}Error processing {file_path}: {str(e)}{Style.RESET_ALL}")
        
        pbar.close()
    
    return scan_result  # 保总是返回scan_result


def process_files(file_pattern, print_results=True, max_workers=10):
    """使用并发处理多个文件"""
    matched_files = glob.glob(file_pattern)
    if not matched_files:
        print(f"{Fore.RED}No files found matching pattern: {file_pattern}{Style.RESET_ALL}")
        exit(1)
    
    scan_result = ScanResult()
    pbar = tqdm(total=len(matched_files), desc="Scanning files", unit="file")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_file = {
            executor.submit(process_single_file, file_path, False): file_path 
            for file_path in matched_files
        }
        
        for future in as_completed(future_to_file):
            file_path = future_to_file[future]
            try:
                result = future.result()
                scan_result.add_file_result(result)
                
                pbar.update(1)
                
                if print_results and result:
                    if result.error:
                        pbar.write(f"{Fore.RED}Error in {file_path}: {result.error}{Style.RESET_ALL}")
                    else:
                        pbar.write(f"\n{Fore.CYAN}=== Results for {file_path} ==={Style.RESET_ALL}")
                        # ... (与上面相同的结果打印辑)
                
            except Exception as e:
                pbar.write(f"{Fore.RED}Error processing {file_path}: {str(e)}{Style.RESET_ALL}")
    
    pbar.close()
    return scan_result


def generate_html_report(scan_result: ScanResult, output_path: str):
    file_sections = []
    
    for file_result in scan_result.files:
        if file_result.error:
            error_section = f'<div class="alert alert-danger">错误: {file_result.error}</div>'
            messages_section = ""
            proto_section = ""
        else:
            error_section = ""
            
            # Messages section
            messages_html = ""
            if file_result.messages:
                messages_html = "<h4 class='mb-4'>发现的消息定义</h4>"
                for msg_name, msg_fields in file_result.messages.items():
                    messages_html += f"<h5 class='mt-4'>{msg_name}</h5>"
                    messages_html += '<table class="table table-striped">'
                    messages_html += "<thead><tr><th>字段名称</th><th>字段类型</th><th>字段编号</th></tr></thead>"
                    messages_html += "<tbody>"
                    for field in msg_fields:
                        messages_html += f"<tr><td>{field[0]}</td><td>{field[1]}</td><td>{field[2]}</td></tr>"
                    messages_html += "</tbody></table>"
                    
                    # 示例数据部分使用新的样式
                    messages_html += '<div class="example-data">'
                    messages_html += '<div class="example-title">示例数据</div>'
                    messages_html += '<pre><code class="language-json">'
                    examples = generate_example_data(msg_fields)
                    messages_html += '\n'.join(examples)
                    messages_html += '</code></pre></div>'
            messages_section = messages_html
            
            # Proto section使用新的样式
            proto_section = ""
            if file_result.proto_content:
                proto_section = '<div class="proto-section">'
                proto_section += '<div class="proto-title">Proto文件定义</div>'
                proto_section += '<pre><code class="language-protobuf">'
                proto_section += file_result.proto_content
                proto_section += '</code></pre></div>'
        
        # 只有当有内容时才添加section
        if messages_section or error_section or proto_section:
            file_sections.append(FILE_SECTION_TEMPLATE.format(
                file_path=file_result.file_path,
                error_section=error_section,
                messages_section=messages_section,
                proto_section=proto_section
            ))
    
    html_content = HTML_TEMPLATE.format(
        timestamp=scan_result.timestamp,
        total_files=scan_result.total_files,
        total_services=scan_result.total_services,
        total_messages=scan_result.total_messages,
        file_results="\n".join(file_sections)
    )
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"\nHTML报告已生成: {output_path}")


def extract_typescript_grpc(content):
    """提取TypeScript中的gRPC定义"""
    patterns = {
        'services': [
            r'@GrpcService\((.*?)\)',  # gRPC服务装饰器
            r'class\s+([a-zA-Z0-9_]+)Service\s+implements\s+([a-zA-Z0-9_]+)',  # 服务实现
            r'interface\s+([a-zA-Z0-9_]+)Client\s*{',  # 客户端接口
            r'@Injectable\(\)\s*export\s+class\s+([a-zA-Z0-9_]+)Service',  # Angular服务
        ],
        'messages': [
            r'interface\s+([a-zA-Z0-9_]+)\s*{([^}]+)}',  # 接口定义
            r'type\s+([a-zA-Z0-9_]+)\s*=\s*{([^}]+)}',  # 类型定义
            r'class\s+([a-zA-Z0-9_]+)\s+implements\s+([a-zA-Z0-9_]+Message)',  # 消息类
        ],
        'methods': [
            r'@GrpcMethod\([\'"]([^\'\"]+)[\'"]\)',  # gRPC方法装饰器
            r'@GrpcStreamMethod\([\'"]([^\'\"]+)[\'"]\)',  # 流式方法装饰器
            r'abstract\s+([a-zA-Z0-9_]+)\(.*\):\s*Observable<.*>;',  # 抽象方法
        ]
    }
    
    results = {
        'services': set(),
        'messages': {},
        'methods': set()
    }
    
    # 提取服务
    for pattern in patterns['services']:
        matches = re.finditer(pattern, content)
        for match in matches:
            service_name = match.group(1)
            if '(' in service_name:  # 处理装饰器参数
                service_name = re.search(r'name:\s*[\'"]([^\'\"]+)[\'"]', service_name)
                if service_name:
                    service_name = service_name.group(1)
            results['services'].add(service_name)
    
    # 提取消息
    for pattern in patterns['messages']:
        matches = re.finditer(pattern, content)
        for match in matches:
            msg_name = match.group(1)
            if msg_name not in results['messages']:
                results['messages'][msg_name] = []
            
            if len(match.groups()) > 1:
                fields_content = match.group(2)
                # 解析字段定义
                field_pattern = r'(\w+)\s*:\s*(\w+)(?:\s*\/\/\s*@field\((\d+)\))?'
                field_matches = re.finditer(field_pattern, fields_content)
                for field_match in field_matches:
                    field_name = field_match.group(1)
                    field_type = field_match.group(2)
                    field_number = field_match.group(3) or '0'  # 如果没有指定字段编号
                    results['messages'][msg_name].append([field_name, field_type, field_number])
    
    # 提取方法
    for pattern in patterns['methods']:
        matches = re.finditer(pattern, content)
        for match in matches:
            results['methods'].add(match.group(1))
    
    return results

def extract_version_info(content):
    """提取gRPC和protobuf的版本信息"""
    version_patterns = {
        'grpc': [
            r'\"@grpc/grpc-js\"\s*:\s*\"([^\"]+)\"',  # package.json中的版本
            r'\"grpc-web\"\s*:\s*\"([^\"]+)\"',
            r'\"@grpc/web\"\s*:\s*\"([^\"]+)\"',
            r'from\s+[\'"]@grpc/grpc-js@([^\'\"]+)[\'"]',  # import语句的版本
            r'GRPC_VERSION\s*=\s*[\'"]([^\'\"]+)[\'"]',  # 版本常量
        ],
        'protobuf': [
            r'\"google-protobuf\"\s*:\s*\"([^\"]+)\"',  # package.json中的版本
            r'\"protobufjs\"\s*:\s*\"([^\"]+)\"',
            r'from\s+[\'"]google-protobuf@([^\'\"]+)[\'"]',
            r'PROTOBUF_VERSION\s*=\s*[\'"]([^\'\"]+)[\'"]',
        ]
    }
    
    versions = {
        'grpc': set(),
        'protobuf': set()
    }
    
    for lib, patterns in version_patterns.items():
        for pattern in patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                versions[lib].add(match.group(1))
    
    return versions

def parse_proto_file(file_path):
    """解析.proto文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 使用正则表达式解析proto文件
        results = {
            'package': '',
            'services': [],
            'messages': [],
            'imports': [],
            'options': {}
        }
        
        # 提取包名
        package_match = re.search(r'package\s+([^;]+);', content)
        if package_match:
            results['package'] = package_match.group(1)
        
        # 提取导入
        import_matches = re.finditer(r'import\s+[\'"]([^\'\"]+)[\'"];', content)
        for match in import_matches:
            results['imports'].append(match.group(1))
        
        # 提取服务定义
        service_matches = re.finditer(
            r'service\s+(\w+)\s*{([^}]+)}',
            content
        )
        for match in service_matches:
            service_name = match.group(1)
            service_content = match.group(2)
            
            # 提取方法
            methods = []
            method_matches = re.finditer(
                r'rpc\s+(\w+)\s*\(([^)]+)\)\s*returns\s*\(([^)]+)\)',
                service_content
            )
            for method_match in method_matches:
                method = {
                    'name': method_match.group(1),
                    'input_type': method_match.group(2).strip(),
                    'output_type': method_match.group(3).strip(),
                    'client_streaming': 'stream' in method_match.group(2),
                    'server_streaming': 'stream' in method_match.group(3)
                }
                methods.append(method)
            
            results['services'].append({
                'name': service_name,
                'methods': methods
            })
        
        # 提取消息定义
        message_matches = re.finditer(
            r'message\s+(\w+)\s*{([^}]+)}',
            content
        )
        for match in message_matches:
            message_name = match.group(1)
            message_content = match.group(2)
            
            # 提取字段
            fields = []
            field_matches = re.finditer(
                r'(repeated|optional|required)?\s*(\w+)\s+(\w+)\s*=\s*(\d+)',
                message_content
            )
            for field_match in field_matches:
                field = {
                    'label': field_match.group(1) or 'optional',
                    'type': field_match.group(2),
                    'name': field_match.group(3),
                    'number': field_match.group(4)
                }
                fields.append(field)
            
            results['messages'].append({
                'name': message_name,
                'fields': fields
            })
        
        # 提取选项
        option_matches = re.finditer(
            r'option\s+(\w+)\s*=\s*[\'"]([^\'\"]+)[\'"];',
            content
        )
        for match in option_matches:
            results['options'][match.group(1)] = match.group(2)
            
        return results
        
    except Exception as e:
        print(f"{Fore.RED}Error parsing proto file {file_path}: {str(e)}{Style.RESET_ALL}")
        return None

def generate_proto_content(messages, services=None, package_name=None):
    """Generate proto file content"""
    proto_content = []
    
    proto_content.append('syntax = "proto3";\n')
    
    # Package name
    if package_name:
        proto_content.append(f'package {package_name};')
    else:
        first_msg = next(iter(messages))
        if '.' in first_msg:
            package_name = first_msg.split('.')[0]
            proto_content.append(f'package {package_name};')
    
    # Go package option
    if package_name:
        proto_content.append(f'option go_package = "go_grpc_{package_name}/proto";\n')
    
    # Service definition
    service_name = None
    
    # 1. 从services列表中获取服务名
    if services and len(services) > 0:
        service_name = services[0]
        if not service_name.endswith('Service'):
            service_name += 'Service'
    
    # 2. 如果没有找到服���名，从消息名中推断
    if not service_name:
        for msg_name in messages:
            if msg_name.endswith('Request'):
                service_name = msg_name.split('.')[0]
                if not service_name.endswith('Service'):
                    service_name += 'Service'
                break
    
    # 3. 如果还是没有找到，使用包名作为服务名
    if not service_name and package_name:
        service_name = package_name.capitalize() + 'Service'
    
    # 生成服务定义
    if service_name:
        proto_content.append(f'service {service_name} {{')
        
        # Find Request/Response pairs
        for msg_name in messages:
            if msg_name.endswith('Request'):
                base_name = msg_name.split('.')[-1]
                method_name = base_name.replace('Request', '')
                response_name = msg_name.replace('Request', 'Response')
                
                if response_name in messages:
                    response_base = response_name.split('.')[-1]
                    proto_content.append(f'  // {method_name} method')
                    proto_content.append(f'  rpc {method_name} ({base_name}) returns ({response_base}) {{}}\n')
        
        proto_content.append('}\n')
    
    # Message definitions
    for msg_name, msg_fields in messages.items():
        if '.' in msg_name:
            msg_name = msg_name.split('.')[-1]
        
        proto_content.append(f'message {msg_name} {{')
        
        for field in msg_fields:
            field_name, field_type, field_number = field
            proto_type = convert_field_type_to_proto(field_type)
            proto_content.append(f'  {proto_type} {field_name.lower()} = {field_number};')
        
        proto_content.append('}\n')
    
    return '\n'.join(proto_content)

def convert_field_type_to_proto(field_type):
    """转换字段类型为proto类型"""
    type_mapping = {
        'Proto3StringField': 'string',
        'Proto3BytesField': 'bytes',
        'Proto3IntField': 'int32',
        'Proto3UintField': 'uint32',
        'Proto3Int64Field': 'int64',
        'Proto3Uint64Field': 'uint64',
        'Proto3BoolField': 'bool',
        'Proto3BooleanField': 'bool',
        'Proto3FloatField': 'float',
        'Proto3DoubleField': 'double',
        'Proto3EnumField': 'int32',  # 默认枚举类型
        'Proto3TimestampField': 'google.protobuf.Timestamp',
        'Proto3DurationField': 'google.protobuf.Duration',
    }
    
    if field_type.startswith('Array<') or field_type.startswith('Repeated<'):
        inner_type = field_type[field_type.find('<')+1:field_type.find('>')]
        base_type = type_mapping.get(inner_type, 'string')
        return f'repeated {base_type}'
    
    return type_mapping.get(field_type, 'string')

if __name__ == "__main__":
    parser = ArgumentParser(usage='python3 %(prog)s [INPUT]',
                            allow_abbrev=False, add_help=False)

    parser.add_argument('--help', action='store_true', default=False)
    parser.add_argument('--file')
    parser.add_argument('--dir')
    parser.add_argument('--stdin', action='store_true', default=False)
    parser.add_argument('--report', help='Output report file name (default: grpc_scan_YYYYMMDD_HHMMSS.html)')
    parser.add_argument('--workers', type=int, default=10,
                       help='Number of worker threads (default: 10)')

    args, unknown = parser.parse_known_args()

    if (args.help is True) or (all(arg is None for arg in [args.file, args.dir])):
        if args.stdin is not True:
            print_parser_help(prog=parser.prog)
            exit(0)

    scan_result = ScanResult()

    if args.dir is not None:
        scan_result = process_directory(args.dir, print_results=True, max_workers=args.workers)
            
    elif args.file is not None:
        result = process_single_file(args.file, print_results=True)
        scan_result.add_file_result(result)
        
    else:
        # 处理标准输入
        js_content = read_standard_input()
        js_content = beautify_js_content(js_content)
        endpoints = extract_endpoints(js_content)
        messages = extract_messages(js_content)
        services = extract_services(js_content)
        
        print(f"{Fore.GREEN}Found Endpoints:{Style.RESET_ALL}")
        for endpoint in endpoints:
            print(f"  {Fore.YELLOW}{endpoint}{Style.RESET_ALL}")
            
        print(f"\n{Fore.GREEN}Found Services:{Style.RESET_ALL}")
        for service in services:
            print(f"  {Fore.YELLOW}{service}{Style.RESET_ALL}")
            
        print(f"\n{Fore.GREEN}Found Messages:{Style.RESET_ALL}")
        for msg_name, msg_fields in messages.items():
            print(f"\n{Fore.YELLOW}{msg_name}:{Style.RESET_ALL}")
            print(create_table(
                columns_list=['Field Name', 'Field Type', 'Field Number'],
                rows_list=msg_fields
            ))
            
        result = FileResult(
            file_path="stdin",
            endpoints=endpoints,
            messages=messages,
            services=services
        )
        scan_result.add_file_result(result)

    # 生成HTML报告
    if args.report is not None:
        report_path = args.report
    else:
        # 使用当前时间生成默认报告名称
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = f"grpc_scan_{timestamp}.html"
    
    generate_html_report(scan_result, report_path)
