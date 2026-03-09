# 快速开始指南

## 安装

### 前置要求

- Python 3.10 或更高版本
- Poetry（推荐）或 pip

### 使用 Poetry 安装（推荐）

```bash
# 1. 克隆仓库
git clone https://github.com/yourusername/neosec.git
cd neosec

# 2. 安装依赖
poetry install

# 3. 激活虚拟环境
poetry shell

# 4. 验证安装
neosec --version
```

### 使用 pip 安装

```bash
# 1. 克隆仓库
git clone https://github.com/yourusername/neosec.git
cd neosec

# 2. 安装
pip install -e .

# 3. 验证安装
neosec --version
```

## 初始化

首次使用前需要初始化配置：

```bash
neosec init
```

这将创建以下目录和文件：
- `~/.neosec/config.yaml` - 配置文件
- `~/.neosec/templates/` - 用户模板目录（包含内置模板副本）
- `~/.neosec/log/` - 日志目录
- `~/.neosec/history/` - 执行历史目录

## 第一个工作流

### 1. 查看可用模板

```bash
neosec workflow --list-templates
```

输出示例：
```
内置模板:
  sequential_workflow              基础顺序执行工作流
  parallel_workflow                并行执行多个侦察任务
  conditional_web_workflow         条件执行 Web 扫描
  ...

用户模板 (~/.neosec/templates/):
  sequential_workflow              基础顺序执行工作流
  parallel_workflow                并行执行多个侦察任务
  ...
```

### 2. 执行内置模板

```bash
# 使用顺序执行模板
neosec workflow --template sequential_workflow --variables target:example.com

# 使用并行执行模板
neosec workflow --template parallel_workflow --variables target:example.com
```

### 3. 创建自定义工作流

创建文件 `my_scan.json`：

```json
{
  "name": "my_first_scan",
  "description": "我的第一个扫描工作流",
  "version": "1.0.0",
  "variables": {
    "target": "example.com"
  },
  "steps": [
    {
      "id": "port_scan",
      "order": 1,
      "name": "端口扫描",
      "tool": "nmap",
      "args": {
        "-sV": true,
        "-p": "80,443",
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

执行自定义工作流：

```bash
neosec workflow --template my_scan.json --variables target:192.168.1.1
```

### 4. 验证模板

在执行前验证模板格式：

```bash
neosec workflow --validate my_scan.json
```

### 5. 干运行测试

不实际执行工具，只显示将要执行的命令：

```bash
neosec workflow --template my_scan.json --variables target:test.com --dry-run
```

## 常用命令

### 执行工作流

```bash
# 基础执行
neosec workflow --template <template_name> --variables target:<target>

# 指定多个变量
neosec workflow --template <template_name> \
  --variables target:example.com \
  --variables wordlist:/path/to/wordlist.txt

# 详细输出模式
neosec workflow --template <template_name> \
  --variables target:example.com \
  --verbose

# 静默模式（只显示错误）
neosec workflow --template <template_name> \
  --variables target:example.com \
  --quiet

# 指定输出文件
neosec workflow --template <template_name> \
  --variables target:example.com \
  --output ./results/scan_result.json

# 生成 Markdown 报告
neosec workflow --template <template_name> \
  --variables target:example.com \
  --report
```

### 查看历史

```bash
# 查看最近 10 条历史
neosec history

# 查看最近 20 条
neosec history --limit 20

# 筛选特定工作流
neosec history --workflow parallel_workflow
```

### 其他命令

```bash
# 显示版本
neosec --version

# 显示帮助
neosec --help
neosec workflow --help
neosec history --help
```

## 配置工具路径

编辑 `~/.neosec/config.yaml`：

```yaml
tools:
  nmap: /usr/bin/nmap
  ffuf: /usr/local/bin/ffuf
  subfinder: /usr/bin/subfinder
  nuclei: /usr/bin/nuclei
  # 添加自定义工具
  custom_tool: /path/to/custom/tool.sh

defaults:
  wordlist: /usr/share/wordlists/dirb/common.txt
  timeout: 300
  retry: 1

output:
  default_path: ./
  default_filename: workflow_result.json
  log_path: ~/.neosec/log/
```

## 示例场景

### 场景 1: 快速端口扫描

```bash
neosec workflow --template sequential_workflow --variables target:192.168.1.1
```

### 场景 2: 完整的 Web 应用扫描

```bash
neosec workflow --template parallel_workflow \
  --variables target:example.com \
  --variables wordlist:/usr/share/wordlists/common.txt \
  --output ./results/web_scan.json \
  --report
```

### 场景 3: 条件执行（只在发现 Web 端口时扫描）

```bash
neosec workflow --template conditional_web_workflow \
  --variables target:example.com
```

### 场景 4: 测试新模板

```bash
# 1. 验证模板
neosec workflow --validate my_new_workflow.json

# 2. 干运行测试
neosec workflow --template my_new_workflow.json \
  --variables target:test.com \
  --dry-run

# 3. 实际执行
neosec workflow --template my_new_workflow.json \
  --variables target:example.com \
  --verbose
```

## 故障排查

### 问题 1: 工具未找到

**错误**: `工具未找到: nmap`

**解决方案**:
1. 确保工具已安装：`which nmap`
2. 在配置文件中指定完整路径：
   ```yaml
   tools:
     nmap: /usr/bin/nmap
   ```

### 问题 2: 模板验证失败

**错误**: `模板验证失败: 缺少必需字段: id`

**解决方案**:
检查模板中每个步骤是否包含所有必需字段：
- `id`
- `order`
- `tool`
- `args`

### 问题 3: 变量未定义

**错误**: `未定义的变量引用: {{target}}`

**解决方案**:
1. 在命令行中提供变量：`--variables target:example.com`
2. 或在模板的 `variables` 字段中定义默认值

### 问题 4: 执行超时

**错误**: `工具执行超时 (300秒)`

**解决方案**:
在模板中增加超时时间：
```json
{
  "timeout": 600
}
```

## 下一步

- 阅读完整文档：[docs/GUIDE.md](docs/GUIDE.md)
- 查看示例工作流：[examples/](examples/)
- 了解高级特性：并行��行、条件执行、数据传递
- 创建自己的工作流模板

## 获取帮助

- 查看文档：`docs/GUIDE.md`
- 提交问题：GitHub Issues
- 查看示例：`examples/` 目录

## 更新

```bash
# 使用 Poetry
cd neosec
git pull
poetry install

# 使用 pip
cd neosec
git pull
pip install -e . --upgrade
```

---

祝你使用愉快！🚀
