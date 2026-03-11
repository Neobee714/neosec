# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- 优化用户输入体验

---


## [0.1.1] - 2026-03-11

### Added
- **结构化输出目录** — 所有工具输出与结果统一归档至 `~/.neosec/result/<ip>/`，当前工作目录保持干净
  - `port_scan.txt` — nmap 原始 stdout（已过滤 SF 指纹 / HTTP 响应体噪声 / `service unrecognized` 提示行）
  - `ffuf_port_<port>.txt` — ffuf 原始 stdout
  - `ffuf_<port>_result.json` — ffuf JSON 结构化数据
  - `ffuf_<port>_result.txt` — ffuf 可读纯文本报告（含命令行、状态码分布、命中条目表）
  - `workflow_result.json` — 工作流执行汇总（JSON）
- **ffuf 纯文本报告**（`.txt`）— 替代原有 Markdown 报告，可直接 `cat` / `less` 阅读
  - 包含：原始命令行、扫描时间、命中数量、状态码分布、对齐列表（PATH / STATUS / SIZE / MS / REDIRECT）
- **`--report` Markdown 报告增强**
  - 端口服务表（端口 / 协议 / 服务 / 版本信息）
  - ffuf 命中条目直接嵌入（含状态码分布徽章）
  - 执行步骤耗时汇总
  - 跳过步骤说明（含端口未开放原因）
- **nmap 输出清洗** — 自动过滤 SF 指纹行、`fingerprint-strings` HTTP 响应体、`service unrecognized despite` 提示行
- **`nmap_ffuf_workflow.json`** — Nmap 端口扫描 + ffuf 多端口目录爆破内置模板（80 / 443 / 8080 / 8000 / 8888）
- **脚本插件机制** — 在 `~/.neosec/scripts/` 或 `neobee/scripts/` 放置脚本即可扩展新工具
  - 查找优先级：用户目录 > 内置目录
  - 支持语言：`.py` `.sh` `.rb` `.js` `.pl` `.php` 及可执行文件
  - 接口协议：stdin 传入 JSON 上下文，stdout 返回 JSON 结果，stderr 用于日志
- **`html_extraction` 内置脚本** — 批量抓取 URL 并清理 HTML 噪声后保存
  - 移除：`<script>` `<style>` `<svg>` `<img>` `<video>` `<iframe>` 外联 CSS 注释 事件属性
  - 保留：`<title>` `<h1-h6>` `<p>` `<a>` `<form>` `<input>` `<button>` 等语义标签
  - 结果保存至 `~/.neosec/result/<ip>/<step_id>.txt`
- **`html_extraction_workflow.json`** — nmap + ffuf + HTML 提取完整工作流模板
- 新增依赖：`beautifulsoup4 ^4.12`、`httpx ^0.27`

### Changed
- **ffuf 输出文件重定向** — `-o` 路径强制指向 `result_dir`，不再落入当前工作目录；仅当用户显式指定 `--output` 至非 cwd 目录时才跟随该目录
- **`workflow_result.json` 仅保存到 `result_dir`** — 不再在 cwd 生成副本，消除工作目录污染
- **ffuf 报告格式** — 由 `.md` Markdown 改为 `.txt` 纯文本，与其他工具输出格式统一
- `workflow_result.json` 移除噪声字段：`raw_output`、`format`、`hosts`
- 跳过的步骤不再写入 JSON 输出，减少冗余数据
- 跳过步骤的 `error` 字段置为 `null`（原为 `"condition not met"`）
- verbose 模式下 ffuf 输出改为对齐列表摘要，nmap 输出改为按服务分行的端口摘要
- ffuf `-o` 自动重定向到 `result_dir`，确保 entries 解析正确且文件整齐归档
- 脚本插件步骤跳过 `_save_tool_stdout`，避免覆盖插件自己写入的输出文件

---

## [0.1.0] - 2026-03-10

### Added

#### 核心功能
- 工作流执行引擎（asyncio 异步执行）
- 配置管理系统（YAML 配置文件，`~/.neosec/config.yaml`）
- 模板管理系统（内置模板 + 用户模板）
- 变量替换系统（支持嵌套字段访问 `{{result.field}}`）
- CLI 命令：`init` `workflow` `history` `version`
- Rich 终端 UI（实时进度显示）

#### 高级特性
- 并行执行（同一 `order` 的独立步骤自动并行）
- 条件执行（6 种条件类型：`contains` `contains_any` `not_contains_any` `equals` `greater_than` `less_than`）
- 步骤间数据传递（`save_result_as` + `{{variable}}`）
- 循环执行（`for_each`）
- 依赖管理（`depends_on`）
- 错误重试和超时控制
- 执行历史记录

#### 内置模板
- `sequential_workflow.json` — 基础顺序执行
- `sequential_workflow_v2.json` — 带超时和重试
- `parallel_workflow.json` — 并行侦察
- `conditional_web_workflow.json` — 条件执行 Web 扫描
- `conditional_service_workflow.json` — 按服务类型条件执行
- `data_passing_workflow.json` — 数据传递示例

#### 依赖
- Python 3.10+
- typer ^0.12.0
- rich ^13.7.0
- pyyaml ^6.0.1
- aiofiles ^23.2.1

---

[0.1.2]: https://github.com/Neobee714/neosec/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/Neobee714/neosec/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/Neobee714/neosec/releases/tag/v0.1.0
