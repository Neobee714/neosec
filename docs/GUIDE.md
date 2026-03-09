# Neosec 使用指南

## 目录

1. [快速开始](#快速开始)
2. [工作流模板详解](#工作流模板详解)
3. [高级特性](#高级特性)
4. [常见问题](#常见问题)
5. [最佳实践](#最佳实践)

## 快速开始

### 安装和初始化

```bash
# 安装
pip install -e .

# 初始化配置
neosec init
```

### 第一个工作流

创建一个简单的端口扫描工作流 `my_scan.json`：

```json
{
  "name": "simple_scan",
  "description": "简单的端口扫描",
  "version": "1.0.0",
  "variables": {
    "target": "example.com"
  },
  "steps": [
    {
      "id": "nmap_scan",
      "order": 1,
      "name": "Nmap 端口扫描",
      "tool": "nmap",
      "args": {
        "-sV": true,
        "-p": "1-1000",
        "target": "{{target}}"
      },
      "save_result_as": "scan_result",
      "timeout": 300,
      "retry": 1,
      "continue_on_error": false
    }
  ]
}
```

执行工作流：

```bash
neosec workflow --template my_scan.json --variables target:192.168.1.1
```

## 工作流模板详解

### 模板结构

```json
{
  "name": "workflow_name",           // 必需：工作流名称
  "description": "描述信息",          // 可选：描述
  "version": "1.0.0",                // 可选：版本号
  "variables": {                     // 可选：全局变量
    "target": "example.com"
  },
  "steps": [                         // 必需：步骤列表
    {
      "id": "step1",                 // 必需：唯一标识符
      "order": 1,                    // 必需：执行顺序
      "name": "步��名称",             // 可选：显示名称
      "tool": "nmap",                // 必需：工具名称或路径
      "args": {},                    // 必需：工具参数
      "parallel_group": "group1",    // 可选：并行组
      "depends_on": ["step0"],       // 可选：依赖的步骤
      "when": {},                    // 可选：条件执行
      "for_each": "{{items}}",       // 可选：循环执行
      "save_result_as": "result1",   // 可选：保存结果
      "timeout": 300,                // 可选：超时时间（秒）
      "retry": 1,                    // 可选：重试次数
      "continue_on_error": false     // 可选：失败时是否继续
    }
  ]
}
```

### 步骤字段说明

#### 必需字段

- `id`: 步骤的唯一标识符，用于依赖引用
- `order`: 执行顺序，数字越小越先执行
- `tool`: 工具名称（如 `nmap`）或完整路径（如 `/usr/bin/nmap`）
- `args`: 工具参数对象

#### 可选字段

- `name`: 步骤的显示名称，用于日志输出
- `parallel_group`: 并行组名称，相同组的步骤会并行执行
- `depends_on`: 依赖的步骤 ID 列表，只有依赖步骤成功后才执行
- `when`: 条件执行配置
- `for_each`: 循环执行的数据源
- `save_result_as`: 保存结果的变量名，供后续步骤引用
- `timeout`: 超时时间（秒），默认 300
- `retry`: 失败重试次数，默认 0
- `continue_on_error`: 失败时是否继续执行，默认 false

### 工具参数格式

```json
{
  "args": {
    "-sV": true,              // 布尔选项：只添加 -sV
    "-p": "1-1000",           // 值选项：添加 -p 1-1000
    "target": "{{target}}"    // 位置参数：直接添加值
  }
}
```

转换为命令：`nmap -sV -p 1-1000 example.com`

## 高级特性

### 1. 并行执行

使用 `parallel_group` 将多个独立步骤分组并行执行：

```json
{
  "steps": [
    {
      "id": "subdomain_enum",
      "order": 1,
      "parallel_group": "recon",
      "tool": "subfinder",
      "args": {"domain": "{{target}}"}
    },
    {
      "id": "dns_enum",
      "order": 1,
      "parallel_group": "recon",
      "tool": "dnsenum",
      "args": {"domain": "{{target}}"}
    },
    {
      "id": "whois_lookup",
      "order": 1,
      "parallel_group": "recon",
      "tool": "whois",
      "args": {"domain": "{{target}}"}
    }
  ]
}
```

这三个步骤会同时执行，提高效率。

### 2. 条件执行

使用 `when` 根据前置步骤的结果决定是否执行：

```json
{
  "id": "web_scan",
  "depends_on": ["port_scan"],
  "when": {
    "type": "contains_any",
    "source": "port_scan_result.open_ports",
    "values": [80, 443, 8080]
  },
  "tool": "ffuf"
}
```

支持的条件类型：

| 类型 | 说明 | 示例 |
|------|------|------|
| `contains` | 包含指定值 | `{"type": "contains", "source": "result.list", "value": 80}` |
| `contains_any` | 包含任意一个值 | `{"type": "contains_any", "source": "result.ports", "values": [80, 443]}` |
| `not_contains_any` | 不包含任何值 | `{"type": "not_contains_any", "source": "result.ports", "values": [22, 23]}` |
| `equals` | 精确匹配 | `{"type": "equals", "source": "result.status", "value": "success"}` |
| `greater_than` | 大于 | `{"type": "greater_than", "source": "result.count", "value": 10}` |
| `less_than` | 小于 | `{"type": "less_than", "source": "result.count", "value": 100}` |

### 3. 数据传递

#### 保存结果

使用 `save_result_as` 保存步骤执行结果：

```json
{
  "id": "port_scan",
  "tool": "nmap",
  "save_result_as": "port_scan_result"
}
```

#### 引用结果

使用 `{{variable}}` 或 `{{result.field}}` 引用数据：

```json
{
  "id": "service_scan",
  "depends_on": ["port_scan"],
  "args": {
    "ports": "{{port_scan_result.open_ports}}",
    "target": "{{target}}"
  }
}
```

支持嵌套访问：`{{result.data.nested.field}}`

### 4. 循环执行

使用 `for_each` 对数组中的每个元素执行步骤：

```json
{
  "id": "scan_each_port",
  "depends_on": ["port_scan"],
  "for_each": "{{port_scan_result.open_ports}}",
  "tool": "nmap",
  "args": {
    "-p": "{{item.port}}",
    "-sV": true,
    "target": "{{target}}"
  }
}
```

如果 `open_ports` 是对象数组，可以访问对象属性：

```json
{
  "for_each": "{{services}}",
  "args": {
    "port": "{{item.port}}",
    "service": "{{item.name}}"
  }
}
```

### 5. 依赖管理

使用 `depends_on` 声明步骤依赖：

```json
{
  "id": "web_scan",
  "depends_on": ["port_scan", "subdomain_enum"],
  "tool": "ffuf"
}
```

只有当 `port_scan` 和 `subdomain_enum` 都成功后，`web_scan` 才会执行。

### 6. 错误处理

#### 重试机制

```json
{
  "id": "unstable_scan",
  "tool": "tool",
  "retry": 3,                    // 失败后重试 3 次
  "timeout": 300                 // 每次尝试超时 300 秒
}
```

重试间隔为 5 秒。

#### 继续执行

```json
{
  "id": "optional_scan",
  "tool": "tool",
  "continue_on_error": true      // 失败后继续执行后续步骤
}
```

如果 `continue_on_error: false`（默认），步骤失败会终止整个工作流。

## 常见问题

### Q: 如何配置工具路径？

A: 编辑 `~/.neosec/config.yaml`：

```yaml
tools:
  nmap: /usr/bin/nmap
  custom_tool: /path/to/custom/tool.sh
```

### Q: 如何查看详细的执行日志？

A: 使用 `--verbose` 选项：

```bash
neosec workflow --template my_workflow --variables target:example.com --verbose
```

日志文件保存在 `~/.neosec/log/` 目录。

### Q: 如何验证模板是否正确？

A: 使用 `--validate` 选项：

```bash
neosec workflow --validate my_workflow.json
```

### Q: 如何在不实际执行的情况下测试工作流？

A: 使用 `--dry-run` 选项：

```bash
neosec workflow --template my_workflow --variables target:test.com --dry-run
```

### Q: 工具输出的结果格式是什么？

A: 建议工具输出 JSON 格式：

```json
{
  "status": "success",
  "data": {
    "open_ports": [80, 443, 22],
    "services": ["http", "https", "ssh"]
  }
}
```

如果工具不输出 JSON，Neosec 会将原始输出包装为：

```json
{
  "status": "success",
  "raw_output": "原始输出内容..."
}
```

## 最佳实践

### 1. 模板组织

- 将通用模板放在 `~/.neosec/templates/` 目录
- 项目特定模板放在项目目录中
- 使用有意义的模板名称和描述

### 2. 变量使用

- 在模板中定义默认变量值
- 通过命令行覆盖变量值
- 使用描述性的变量名

### 3. 错误处理

- 关键步骤设置 `continue_on_error: false`
- 不稳定的步骤设置合理的 `retry` 值
- 设置合理的 `timeout` 避免无限等待

### 4. 并行执行

- 只对独立的任务使用并行
- 避免资源竞争（如同时扫描同一目标）
- 使用 `depends_on` 确保执行顺序

### 5. 数据传递

- 保存需要传递的关键结果
- 使用清晰的结果变量名
- 验证数据格式的一致性

### 6. 性能优化

- 合理使用并行执行
- 设置合适的超时时间
- 避免不必要的步骤

### 7. 安全考虑

- 不要在模板中硬编码敏感信息
- 使用变量传递目标和凭证
- 定期审查执行历史

## 示例工作流

### 完整的 Web 应用扫描

```json
{
  "name": "web_app_scan",
  "description": "完整的 Web 应用安全扫描",
  "version": "1.0.0",
  "variables": {
    "target": "example.com",
    "wordlist": "/usr/share/wordlists/common.txt"
  },
  "steps": [
    {
      "id": "port_scan",
      "order": 1,
      "name": "端口扫描",
      "tool": "nmap",
      "args": {
        "-sV": true,
        "-p": "1-65535",
        "target": "{{target}}"
      },
      "save_result_as": "ports",
      "timeout": 600,
      "retry": 1
    },
    {
      "id": "subdomain_enum",
      "order": 2,
      "parallel_group": "recon",
      "name": "子域名枚举",
      "tool": "subfinder",
      "args": {
        "domain": "{{target}}"
      },
      "save_result_as": "subdomains",
      "timeout": 300
    },
    {
      "id": "dns_enum",
      "order": 2,
      "parallel_group": "recon",
      "name": "DNS 枚举",
      "tool": "dnsenum",
      "args": {
        "domain": "{{target}}"
      },
      "save_result_as": "dns_records",
      "timeout": 300
    },
    {
      "id": "dir_scan",
      "order": 3,
      "name": "目录扫描",
      "depends_on": ["port_scan"],
      "when": {
        "type": "contains_any",
        "source": "ports.open_ports",
        "values": [80, 443, 8080]
      },
      "tool": "ffuf",
      "args": {
        "--wordlist": "{{wordlist}}",
        "target": "{{target}}"
      },
      "save_result_as": "directories",
      "timeout": 600
    },
    {
      "id": "vuln_scan",
      "order": 4,
      "name": "漏洞扫描",
      "depends_on": ["port_scan", "dir_scan"],
      "tool": "nuclei",
      "args": {
        "target": "{{target}}"
      },
      "save_result_as": "vulnerabilities",
      "timeout": 900
    }
  ]
}
```

执行：

```bash
neosec workflow \
  --template web_app_scan.json \
  --variables target:example.com \
  --variables wordlist:/path/to/wordlist.txt \
  --output ./results/scan_$(date +%Y%m%d).json \
  --report
```
