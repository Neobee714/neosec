# Neosec 项目总结

## 项目概述

Neosec 是一款为渗透测试人员设计的工作流自动化 CLI 工具，支持复杂的安全测试场景编排。

## 已实现功能

### 核心模块

1. **配置管理 (config.py)**
   - 支持 YAML 配置文件
   - 工具路径配置
   - 默认参数配置
   - 输出路径配置
   - 配置合并和嵌套访问

2. **模板管理 (template.py)**
   - 内置模板和用户模板支持
   - 模板查找（优先级：用户 > 内置 > 文件路径）
   - 完整的模板验证
     - JSON 格式验证
     - 必需字段检查
     - 依赖关系验证
     - 循环依赖检测
     - 变量引用验证

3. **工作流引擎 (engine.py)**
   - 异步执行支持
   - 并行执行（parallel_group）
   - 条件执行（when）
   - 步骤间数据传递
   - 循环执行（for_each）
   - 依赖管理（depends_on）
   - 错误处理和重试机制
   - 超时控制

4. **变量系统 (variables.py)**
   - 变量替换（{{variable}}）
   - 嵌套字段访问（{{result.data.field}}）
   - 类型保持（数字、列表、对象）
   - 上下文管理

5. **CLI 接口 (cli/main.py)**
   - `neosec init` - 初始化配置
   - `neosec workflow` - 执行工作流
   - `neosec history` - 查看历史
   - 完整的命令行参数支持

6. **终端 UI (utils/ui.py)**
   - Rich 库集成
   - 实时表格显示
   - 进度状态图标
   - 详细模式和静默模式
   - 执行摘要

### 高级特性

1. **并行执行**
   - 使用 asyncio 实现真正的并行
   - parallel_group 分组
   - 自动等待所有并行任务完成

2. **条件执行**
   - 支持 6 种条件类型
   - contains, contains_any, not_contains_any
   - equals, greater_than, less_than

3. **数据传递**
   - save_result_as 保存结果
   - 点号访问嵌套��段
   - 支持复杂数据结构

4. **错误处理**
   - 自动重试（可配置次数和间隔）
   - continue_on_error 控制
   - 详细错误日志
   - 超时强制终止

5. **执行历史**
   - 自动保存执行结果
   - JSON 格式存储
   - 历史查询和筛选

6. **报告生成**
   - JSON 格式结果
   - Markdown 格式报告（可选）
   - 完整的执行信息

## 项目结构

```
Neosec/
├── src/
│   └── neosec/
│       ├── __init__.py
│       ├── cli/
│       │   ├── __init__.py
│       │   └── main.py          # CLI 入口
│       ├── core/
│       │   ├── __init__.py
│       │   ├── config.py        # 配置管理
│       │   ├── template.py      # 模板管理
│       │   └── engine.py        # 工作流引擎
│       ├── templates/           # 内置模板
│       │   ├── sequential_workflow.json
│       │   ├── parallel_workflow.json
│       │   ├── conditional_web_workflow.json
│       │   ├── conditional_service_workflow.json
│       │   ├── sequential_workflow_v2.json
│       │   └── data_passing_workflow.json
│       └── utils/
│           ├── __init__.py
│           ├── variables.py     # 变量替换
│           └── ui.py            # 终端 UI
├── tests/
│   ├── __init__.py
│   ├── test_config.py
│   ├── test_template.py
│   └── test_variables.py
├── docs/
│   └── GUIDE.md                 # 使用指南
├── examples/
│   └── example_workflow.json    # 示例工作流
├── information/                 # 原始需求文档
├── pyproject.toml              # Poetry 配置
├── README.md                   # 项目说明
├── LICENSE                     # MIT 许可证
└── .gitignore
```

## 使用示例

### 1. 初始化

```bash
neosec init
```

### 2. 列出模板

```bash
neosec workflow --list-templates
```

### 3. 验证模板

```bash
neosec workflow --validate examples/example_workflow.json
```

### 4. 执行工作流

```bash
# 基础执行
neosec workflow --template sequential_workflow --variables target:example.com

# 详细模式
neosec workflow --template parallel_workflow \
  --variables target:example.com \
  --verbose

# 干运行
neosec workflow --template example_workflow \
  --variables target:test.com \
  --dry-run

# 生成报告
neosec workflow --template full_scan \
  --variables target:example.com \
  --output ./results/scan.json \
  --report
```

### 5. 查看历史

```bash
neosec history --limit 20
neosec history --workflow parallel_workflow
```

## 技术栈

- **Python 3.10+**: 使用现代 Python 特性
- **Poetry**: 依赖管理和打包
- **Typer**: CLI 框架（基于类型提示）
- **Rich**: 终端 UI 和美化输出
- **PyYAML**: YAML 配置文件解析
- **asyncio**: 异步执行和并行控制
- **pytest**: 单元测试框架

## 配置文件示例

`~/.neosec/config.yaml`:

```yaml
tools:
  nmap: /usr/bin/nmap
  ffuf: /usr/local/bin/ffuf
  subfinder: /usr/bin/subfinder
  nuclei: /usr/bin/nuclei

defaults:
  wordlist: /usr/share/wordlists/dirb/common.txt
  timeout: 300
  retry: 1

output:
  default_path: ./
  default_filename: workflow_result.json
  log_path: ~/.neosec/log/

verbose: false
quiet: false
```

## 测试覆盖

- 配置管理测试
- 模板验证测试
- 变量替换测试
- 依赖关系测试
- 循环依赖检测测试

## 下一步计划

### 短期目标

1. **工具解析器**
   - 为常见工具（nmap, ffuf, nuclei）实现专用解析器
   - 标准化输出格式
   - 进度解析支持

2. **Copy 模块**
   - 实现快速复制功能
   - 报告复制
   - 命令复制
   - IP 地址管理

3. **增强 UI**
   - 实时进度百分比
   - 工具输出流式显示
   - 彩色日志

### 中期目标

1. **插件系统**
   - 自定义工具插件
   - 结果解析插件
   - 报告生成插件

2. **Web UI**
   - 基于 Web 的工作流编辑器
   - 实时执行监控
   - 历史查看和分析

3. **协作功能**
   - 工作流分享
   - 团队模板库
   - 执行结果共享

### 长期目标

1. **AI 集成**
   - 智能工作流推荐
   - 结果分析和建议
   - 自动化报告生成

2. **云端支持**
   - 云端执行
   - 分布式扫描
   - 结果聚合

## 贡献指南

1. Fork 项目
2. 创建特性分支
3. 编写测试
4. 提交 Pull Request

## 许可证

MIT License - 详见 LICENSE 文件

## 联系方式

- GitHub Issues: 报告问题和建议
- 文档: docs/GUIDE.md
- 示例: examples/

---

**项目状态**: ✅ 核心功能已完成，可以开始使用和测试
