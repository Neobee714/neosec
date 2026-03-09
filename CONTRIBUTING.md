# 贡献指南

感谢你对 Neosec 项目的关注！我们欢迎各种形式的贡献。

## 如何贡献

### 报告问题

如果你发现了 bug 或有功能建议：

1. 在 [GitHub Issues](https://github.com/yourusername/neosec/issues) 中搜索是否已有相关问题
2. 如果没有，创建新的 Issue
3. 清楚地描述问题或建议
4. 如果是 bug，请提供：
   - 操作系统和 Python 版本
   - 完整的错误信息
   - 重现步骤
   - 相关的配置文件和模板

### 提交代码

1. **Fork 项目**
   ```bash
   # 在 GitHub 上 Fork 项目
   git clone https://github.com/your-username/neosec.git
   cd neosec
   ```

2. **创建分支**
   ```bash
   git checkout -b feature/your-feature-name
   # 或
   git checkout -b fix/your-bug-fix
   ```

3. **设置开发环境**
   ```bash
   poetry install
   poetry shell
   ```

4. **进行修改**
   - 遵循项目的代码风格
   - 添加必要的测试
   - 更新相关文档

5. **运行测试**
   ```bash
   # 运行所有测试
   poetry run pytest

   # 运行特定测试
   poetry run pytest tests/test_config.py

   # 代码格式化
   poetry run black src/

   # 代码检查
   poetry run ruff check src/
   ```

6. **提交更改**
   ```bash
   git add .
   git commit -m "feat: add new feature"
   # 或
   git commit -m "fix: fix bug description"
   ```

7. **推送到 GitHub**
   ```bash
   git push origin feature/your-feature-name
   ```

8. **创建 Pull Request**
   - 在 GitHub 上创建 Pull Request
   - 清楚地描述你的更改
   - 关联相关的 Issue

## 提交信息规范

使用 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

- `feat:` 新功能
- `fix:` Bug 修复
- `docs:` 文档更新
- `style:` 代码格式（不影响代���运行）
- `refactor:` 重构
- `test:` 测试相关
- `chore:` 构建过程或辅助工具的变动

示例：
```
feat: add support for custom tool parsers
fix: resolve circular dependency detection issue
docs: update installation guide
test: add tests for variable replacement
```

## 代码风格

### Python 代码

- 使用 Python 3.10+ 特性
- 遵循 PEP 8 规范
- 使用类型提示
- 使用 Black 格式化代码（行长度 100）
- 使用 Ruff 进行代码检查

示例：
```python
def execute_workflow(
    template: dict[str, Any],
    variables: dict[str, str],
    output_file: Optional[str] = None,
) -> dict[str, Any]:
    """执行工作流

    Args:
        template: 模板数据
        variables: 变量字典
        output_file: 输出文件路径

    Returns:
        执行结果
    """
    # 实现代码
    pass
```

### 文档

- 使用清晰简洁的中文
- 提供代码示例
- 更新相关的 Markdown 文档

## 测试

### 编写测试

- 为新功能添加测试
- 确保测试覆盖边界情况
- 使用 pytest 框架

示例：
```python
def test_config_get_nested():
    """测试嵌套配置获取"""
    config = Config()
    config.config_data = {
        "tools": {
            "nmap": "/usr/bin/nmap"
        }
    }

    assert config.get("tools.nmap") == "/usr/bin/nmap"
    assert config.get("tools.ffuf", "default") == "default"
```

### 运行测试

```bash
# 运行所有测试
poetry run pytest

# 运行特定测试文件
poetry run pytest tests/test_config.py

# 运行特定测试函数
poetry run pytest tests/test_config.py::test_config_get_nested

# 显示详细输出
poetry run pytest -v

# 显示覆盖率
poetry run pytest --cov=src/neosec
```

## 项目结构

```
Neosec/
├── src/neosec/              # 源代码
│   ├── cli/                 # CLI 接口
│   │   └── main.py          # 主命令入口
│   ├── core/                # 核心模块
│   │   ├── config.py        # 配置管理
│   │   ├── template.py      # 模板管理
│   │   └── engine.py        # 工作流引擎
│   ├── templates/           # 内置模板
│   └── utils/               # 工具函数
│       ├── variables.py     # 变量替换
│       └── ui.py            # 终端 UI
├── tests/                   # 测试文件
│   ├── test_config.py
│   ├── test_template.py
│   └── test_variables.py
├── docs/                    # 文档
│   └── GUIDE.md
├── examples/                # 示例
│   └── example_workflow.json
└── pyproject.toml          # Poetry 配置
```

## 添加新功能

### 1. 添加新的工具解析器

在 `src/neosec/utils/` 中创建新文件：

```python
# src/neosec/utils/parsers.py

def parse_nmap_output(output: str) -> dict:
    """解析 nmap 输出

    Args:
        output: nmap 原始输出

    Returns:
        标准化的结果字典
    """
    # 实现解析逻辑
    return {
        "status": "success",
        "data": {
            "open_ports": [80, 443],
            "services": ["http", "https"]
        }
    }
```

### 2. 添加新的内置模板

在 `src/neosec/templates/` 中创建新的 JSON 文件：

```json
{
  "name": "new_workflow",
  "description": "新工作流描述",
  "version": "1.0.0",
  "variables": {},
  "steps": []
}
```

### 3. 添加新的 CLI 命令

在 `src/neosec/cli/main.py` 中添加新命令：

```python
@app.command()
def new_command(
    option: str = typer.Option(..., "--option", help="选项说明")
):
    """新命令描述"""
    # 实现命令逻辑
    pass
```

## 文档更新

当你添加新功能时，请更新相关文档：

- `README.md` - 如果是重要功能
- `docs/GUIDE.md` - 详细使用说明
- `CHANGELOG.md` - 记录更改
- 代码注释和 docstring

## 发布流程

（仅限维护者）

1. 更新版本号（`pyproject.toml` 和 `src/neosec/__init__.py`）
2. 更新 `CHANGELOG.md`
3. 创建 Git tag
4. 推送到 GitHub
5. 创建 Release

```bash
# 更新版本
poetry version patch  # 或 minor, major

# 提交更改
git add .
git commit -m "chore: bump version to x.y.z"

# 创建 tag
git tag -a vx.y.z -m "Release version x.y.z"

# 推送
git push origin main --tags
```

## 社区准则

- 尊重所有贡献者
- 保持友好和专业
- 接受建设性的批评
- 关注项目的最佳利益

## 获取帮助

如果你有任何问题：

- 查看 [文档](docs/GUIDE.md)
- 搜索 [Issues](https://github.com/yourusername/neosec/issues)
- 创建新的 Issue 提问

## 许可证

通过贡献代码，你同意你的贡献将在 MIT 许可证下发布。

---

再次感谢你的贡献！🎉
