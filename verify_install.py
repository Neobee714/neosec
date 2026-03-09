#!/usr/bin/env python3
"""
Neosec 安装验证脚本
运行此脚本以验证 Neosec 是否正确安装
"""

import sys
from pathlib import Path


def check_python_version():
    """检查 Python 版本"""
    print("检查 Python 版本...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 10:
        print(f"✓ Python {version.major}.{version.minor}.{version.micro} - 符合要求")
        return True
    else:
        print(f"✗ Python {version.major}.{version.minor}.{version.micro} - 需要 Python 3.10+")
        return False


def check_imports():
    """检查必需的包是否已安装"""
    print("\n检查依赖包...")
    packages = {
        "typer": "Typer",
        "rich": "Rich",
        "yaml": "PyYAML",
        "aiofiles": "aiofiles",
    }

    all_ok = True
    for module, name in packages.items():
        try:
            __import__(module)
            print(f"✓ {name} - 已安装")
        except ImportError:
            print(f"✗ {name} - 未安装")
            all_ok = False

    return all_ok


def check_neosec_module():
    """检查 Neosec 模块是否可导入"""
    print("\n检查 Neosec 模块...")
    try:
        import neosec
        print(f"✓ Neosec 模块 - 可导入")
        print(f"  版本: {neosec.__version__}")
        return True
    except ImportError as e:
        print(f"✗ Neosec 模块 - 导入失败: {e}")
        return False


def check_cli_command():
    """检查 CLI 命令是否可用"""
    print("\n检查 CLI 命令...")
    import shutil

    if shutil.which("neosec"):
        print("✓ neosec 命令 - 可用")
        return True
    else:
        print("✗ neosec 命令 - 不可用")
        print("  提示: 确保已激活虚拟环境或已正确安装")
        return False


def check_templates():
    """检查内置模板是否存在"""
    print("\n检查内置模板...")

    try:
        from neosec.core.template import TemplateManager
        from pathlib import Path

        builtin_dir = Path(__file__).parent / "src" / "neosec" / "templates"
        user_dir = Path.home() / ".neosec" / "templates"

        if builtin_dir.exists():
            templates = list(builtin_dir.glob("*.json"))
            print(f"✓ 内置模板目录 - 找到 {len(templates)} 个模板")
            for tmpl in templates:
                print(f"  - {tmpl.stem}")
            return True
        else:
            print(f"✗ 内置模板目录 - 未找到: {builtin_dir}")
            return False
    except Exception as e:
        print(f"✗ 检查模板失败: {e}")
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("Neosec 安装验证")
    print("=" * 60)

    checks = [
        ("Python 版本", check_python_version),
        ("依赖包", check_imports),
        ("Neosec 模块", check_neosec_module),
        ("CLI 命令", check_cli_command),
        ("内置模板", check_templates),
    ]

    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"✗ {name} - 检查失败: {e}")
            results.append((name, False))

    print("\n" + "=" * 60)
    print("验证结果")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{name:20} {status}")

    print(f"\n总计: {passed}/{total} 项检查通过")

    if passed == total:
        print("\n✓ 所有检查通过！Neosec 已正确安装。")
        print("\n下一步:")
        print("  1. 运行 'neosec init' 初始化配置")
        print("  2. 运行 'neosec workflow --list-templates' 查看可用模板")
        print("  3. 阅读 QUICKSTART.md 开始使用")
        return 0
    else:
        print("\n✗ 部分检查失败，请检查安装。")
        print("\n建议:")
        print("  1. 确保已安装 Python 3.10+")
        print("  2. 运行 'poetry install' 或 'pip install -e .'")
        print("  3. 激活虚拟环境: 'poetry shell'")
        return 1


if __name__ == "__main__":
    sys.exit(main())
