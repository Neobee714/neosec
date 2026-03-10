# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-03-10

### Added

#### Core Features
- 工作流执行引擎，支持异步执行
- 配置管理系统（YAML 配置文件）
- 模板管理系统（内置模板和用户模板）
- 变量替换系统（支持嵌套访问）
- CLI 命令接口（init、workflow、history、version）
- 终端 UI（Rich 库集成，实时表格显示）

#### Advanced Features
- 并行执行支持（parallel_group）
- 条件执行支持（6 种条件类型）
  - contains
  - contains_any
  - not_contains_any
  - equals
  - greater_than
  - less_than
- 步骤间数据传递（save_result_as）
- 循环执行支持（for_each）
- 依赖管理（depends_on）
- 错误处理和重试机制
- 超时控制
- 执行历史记录

#### CLI Commands
- `neosec init` - 初始化配置和目录结构
- `neosec version` - 显示版本信息
- `neosec workflow` - 执行工作流
  - `--template` - 指定模板
  - `--list-templates` - 列出所有可用模板
  - `--validate` - 验证模板文件
  - `--variables` - 传递变量
  - `--output` - 指定输出文件
  - `--report` - 生成 Markdown 报告
  - `--dry-run` - 干运行模式
  - `--config` - 自定义配置文件路径
  - `--verbose` - 详细输出模式
  - `--quiet` - 静默模式
- `neosec history` - 查看执行历史
  - `--limit` - 限制显示数量
  - `--workflow` - 筛选工作流名称

#### Built-in Templates
- sequential_workflow.json - 基础顺序执行工作流
- sequential_workflow_v2.json - 带超时和重试的顺序执行
- parallel_workflow.json - 并行执行多个侦察任务
- conditional_web_workflow.json - 条件执行 Web 扫描
- conditional_service_workflow.json - 根据服务类型条件执行
- data_passing_workflow.json - 步骤间数据传递示例

#### Documentation
- README.md - 项目说明和功能介绍
- QUICKSTART.md - 快速开始指南
- docs/GUIDE.md - 完整使用指南
- PROJECT_SUMMARY.md - 项目总结
- COMPLETION_REPORT.md - 开发完成报告
- FINAL_SUMMARY.md - 最终总结
- LICENSE - MIT 许可证

#### Tests
- test_config.py - 配置管理测试
- test_template.py - 模板管理测试
- test_variables.py - 变量替换测试

#### Examples
- examples/example_workflow.json - 完整示例工作流

#### Tools
- verify_install.py - 安装验证脚本

### Technical Details

#### Dependencies
- Python 3.10+
- typer ^0.12.0 - CLI 框架
- rich ^13.7.0 - 终端 UI
- pyyaml ^6.0.1 - YAML 配置解析
- aiofiles ^23.2.1 - 异步文件操作

#### Development Dependencies
- pytest ^8.0.0 - 测试框架
- pytest-asyncio ^0.23.0 - 异步测试支持
- black ^24.0.0 - 代码格式化
- ruff ^0.2.0 - 代码检查

#### Project Structure
```
src/neosec/
├── cli/main.py (14K) - CLI 入口
├── core/
│   ├── config.py (4.9K) - 配置管理
│   ├── template.py (12K) - 模板管理
│   └── engine.py (16K) - 工作流引擎
├── templates/ - 6 个内置模板
└── utils/
    ├── variables.py (2.6K) - 变量替换
    └── ui.py (11K) - 终端 UI
```

### Features Highlights

#### 1. Async Parallel Execution
使用 Python asyncio 实现真正的并行执行，支持同一 order 内的步骤并行和 parallel_group 分组并行。

#### 2. Flexible Condition System
支持 6 种条件类型，可以根据前置步骤的结果动态决定执行路径。

#### 3. Powerful Data Passing
支持嵌套字段访问、类型保持、循环执行和上下文管理。

#### 4. Comprehensive Error Handling
自动重试��制、超时控制、continue_on_error 控制和详细错误日志。

#### 5. Beautiful Terminal UI
Rich 库实现的表格显示、实时更新、多种显示模式和彩色输出。

### Known Limitations

1. 工具输出目前只支持 JSON 格式，其他格式会被包装为 raw_output
2. 进度显示使用简单动画，大多数工具不提供进度信息
3. 部分功能在 Windows 上可能需要调整（主要是路径处理）
4. 没有限制并发数量，可能导致资源耗尽

### Installation

```bash
# Using Poetry (recommended)
poetry install
poetry shell
neosec init

# Using pip
pip install -e .
neosec init
```

### Usage Example

```bash
# List templates
neosec workflow --list-templates

# Execute workflow
neosec workflow --template sequential_workflow --variables target:example.com

# View history
neosec history
```

---

## [Unreleased]

### Planned Features

#### Short-term (1-2 weeks)
- Tool output parsers for common tools (nmap, ffuf, nuclei)
- More built-in templates
- Enhanced logging system

#### Mid-term (1-2 months)
- Copy module implementation
- Tool progress parsing
- Web UI interface

#### Long-term (3-6 months)
- AI integration
- Cloud support
- Team collaboration features

---

[0.1.0]: https://github.com/Neobee714/neosec/releases/tag/v0.1.0
