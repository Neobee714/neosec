"""测试配置模块"""
import pytest
from pathlib import Path
from neosec.core.config import Config


def test_config_default_values():
    """测试默认配置值"""
    config = Config()
    assert config.neosec_dir == Path.home() / ".neosec"
    assert config.templates_dir == config.neosec_dir / "templates"
    assert config.log_dir == config.neosec_dir / "log"
    assert config.history_dir == config.neosec_dir / "history"


def test_config_merge():
    """测试配置合并"""
    config = Config()
    default = {"a": 1, "b": {"c": 2, "d": 3}}
    user = {"b": {"c": 5}, "e": 6}

    result = config._merge_config(default, user)

    assert result["a"] == 1
    assert result["b"]["c"] == 5
    assert result["b"]["d"] == 3
    assert result["e"] == 6


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
    assert config.get("nonexistent", "default") == "default"


def test_get_tool_path():
    """测试获取工具路径"""
    config = Config()
    config.config_data = {
        "tools": {
            "nmap": "/usr/bin/nmap"
        }
    }

    assert config.get_tool_path("nmap") == "/usr/bin/nmap"
    assert config.get_tool_path("ffuf") == "ffuf"  # 未配置时返回工具名本身
