# Neosec

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Neosec 是一款为渗透测试人员提供便捷的工作流自动化 CLI 工具。

## 特性

- 🚀 **工作流自动化**: 通过 JSON 模板定义和执行复杂的安全测试工作流
- ⚡ **并行执行**: 支持多个独立任务同时执行，提高测试效率
- 🔀 **条件执行**: 根据前置步骤的结果动态决定执行路径
- 🔗 **数据传递**: 步骤间无缝传递和引用执行结果
- 📊 **实时进度**: 美观的终端 UI 实时显示执行进度
- 🔄 **错误重试**: 自动重试失败的步骤，提高稳定性
- 📝 **执行历史**: 自动记录所有执行历史，方便回溯
- 🎨 **自定义工具**: 支持集成任何命令行工具或自定义脚本

## 安装

### 使用 Poetry（推荐）

```bash
# 克隆仓库
git clone https://github.com/yourusername/neosec.git
cd neosec

# 安装依赖
poetry install

# 激活虚拟环境
poetry shell

# 初始化配置
neosec init
```

### 使用 pip

```bash
# 克隆仓库
git clone https://github.com/yourusername/neosec.git
cd neosec

# 安装
pip install -e .

# 初始化配置
neosec init
```

## 快速开始

### 1. 初始化

首次使用需要初始化配置和目录结构：

```bash
neosec init
```

这将创建：
- `~/.neosec/config.yaml` - 配置文件
- `~/.neosec/templates/` - 用户模板目录
- `~/.neosec/log/` - 日志目录
- `~/.neosec/history/` - 执行历史目录

### 2. 查看可用模板

```bash
neosec workflow --list-templates
```

### 3. 执行工作流

```bash
# 使用内置模板
neosec workflow --template sequential_workflow --variables target:example.com

# 使用自定义模板
neosec workflow --template ./my_workflow.json --variables target:192.168.1.1

# 指定多个变量
neosec workflow --template parallel_workflow \
  --variables target:example.com \
  --variables wordlist:/usr/share/wordlists/common.txt

# 生成 Markdown 报告
neosec workflow --template full_scan \
  --variables target:example.com \
  --output ./results/scan.json \
  --report
```

### 4. 查看执行历史

```bash
# 查看最近 10 条历史
neosec history

# 查看最近 20 条
neosec history --limit 20

# 筛选特定工作流
neosec history --workflow parallel_workflow
```

## 工作流模板

### 模板结构

```json
{
  "name": "my_workflow",
  "description": "我的自定义工作流",
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
        "target": "{{target}}"
      },
      "save_result_as": "port_scan_result",
      "timeout": 300,
      "retry": 1,
      "continue_on_error": false
    }
  ]
}
```

### 核心功能

#### 1. 并行执行

使用 `parallel_group` 将多个步骤分组并行执行：

```json
{
  "id": "subdomain_enum",
  "order": 1,
  "parallel_group": "recon",
  "tool": "subfinder",
  "args": {"domain": "{{target}}"}
}
```

#### 2. 条件执行

使用 `when` 根据前置步骤结果决定是否执行：

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
- `contains`: 包含指定值
- `contains_any`: 包含任意一个值
- `not_contains_any`: 不包含任何值
- `equals`: 精确匹配
- `greater_than`: 大于
- `less_than`: 小于

#### 3. 数据传递

使用 `save_result_as` 保存结果，使用 `{{variable}}` 引用：

```json
{
  "id": "port_scan",
  "save_result_as": "ports",
  "tool": "nmap"
},
{
  "id": "service_scan",
  "depends_on": ["port_scan"],
  "args": {
    "ports": "{{ports.open_ports}}"
  }
}
```

#### 4. 循环执行

使用 `for_each` 对数组元素循环执行：

```json
{
  "id": "scan_ports",
  "for_each": "{{ports.open_ports}}",
  "args": {
    "port": "{{item.port}}",
    "service": "{{item.service}}"
  }
}
```

## 配置文件

配置文件位于 `~/.neosec/config.yaml`：

```yaml
# 工具路径配置
tools:
  nmap: /usr/bin/nmap
  ffuf: /usr/local/bin/ffuf
  subfinder: /usr/bin/subfinder
  nuclei: /usr/bin/nuclei

# 默认参数
defaults:
  wordlist: /usr/share/wordlists/dirb/common.txt
  timeout: 300
  retry: 1

# 输出配置
output:
  default_path: ./
  default_filename: workflow_result.json
  log_path: ~/.neosec/log/

# 其他配置
verbose: false
quiet: false
```

## 命令行选项

### 全局选项

```bash
neosec --version              # 显示版本信息
neosec --help                 # 显示帮助信息
```

### workflow 命令

```bash
neosec workflow [OPTIONS]

选项:
  --template, -t TEXT          模板名称或文件路径
  --list-templates            列出所有可用模板
  --validate TEXT             验证模板文件
  --variables, -v TEXT        变量值 (格式: key:value)
  --output, -o TEXT           输出文件路径
  --report                    生成 Markdown 报告
  --dry-run                   干运行模式，不实际执行
  --config, -c TEXT           自定义配置文件路径
  --verbose                   详细输出模式
  --quiet, -q                 静默模式
  --help                      显示帮助信息
```

### history 命令

```bash
neosec history [OPTIONS]

选项:
  --limit, -n INTEGER         显示最近 N 条记录 (默认: 10)
  --workflow, -w TEXT         筛选工作流名称
  --help                      显示帮助信息
```

## 内置模板

- `sequential_workflow` - 基础顺序执行工作流
- `sequential_workflow_v2` - 带超时和重试的顺序执行
- `conditional_web_workflow` - 条件执行 Web 扫描
- `conditional_service_workflow` - 根据服务类型条件执行
- `parallel_workflow` - 并行执行多个侦察任务
- `data_passing_workflow` - 步骤间数据传递示例

## 自定义工具集成

Neosec 支持集成任何命令行工具。只需在模板中指定工具路径和参数：

```json
{
  "id": "custom_scan",
  "tool": "/path/to/your/tool.sh",
  "args": {
    "target": "{{target}}",
    "--option": "value"
  }
}
```

建议自定义工具输出 JSON 格式以支持数据传递：

```json
{
  "status": "success",
  "data": {
    "key": "value"
  }
}
```

## 开发

### 运行测试

```bash
poetry run pytest
```

### 代码格式化

```bash
poetry run black src/
poetry run ruff check src/
```

## 贡献

欢迎贡献！请遵循以下步骤：

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 开启 Pull Request

## 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 致谢

- [Typer](https://typer.tiangolo.com/) - 优秀的 CLI 框架
- [Rich](https://rich.readthedocs.io/) - 美观的终端输出库

## 联系方式

如有问题或建议，请提交 [Issue](https://github.com/yourusername/neosec/issues)
