"""测试模板管理模块"""
import pytest
import json
from pathlib import Path
from neosec.core.template import TemplateManager


@pytest.fixture
def template_manager(tmp_path):
    """创建临时模板管理器"""
    builtin_dir = tmp_path / "builtin"
    user_dir = tmp_path / "user"
    builtin_dir.mkdir()
    user_dir.mkdir()

    return TemplateManager(builtin_dir, user_dir)


def test_validate_template_valid(template_manager):
    """测试验证有效模板"""
    template = {
        "name": "test_workflow",
        "steps": [
            {
                "id": "step1",
                "order": 1,
                "tool": "nmap",
                "args": {"target": "{{target}}"}
            }
        ]
    }

    is_valid, errors = template_manager.validate_template(template)
    assert is_valid
    assert len(errors) == 0


def test_validate_template_missing_name(template_manager):
    """测试缺少 name 字段"""
    template = {
        "steps": []
    }

    is_valid, errors = template_manager.validate_template(template)
    assert not is_valid
    assert any("name" in error for error in errors)


def test_validate_template_missing_steps(template_manager):
    """测试缺少 steps 字段"""
    template = {
        "name": "test"
    }

    is_valid, errors = template_manager.validate_template(template)
    assert not is_valid
    assert any("steps" in error for error in errors)


def test_validate_template_duplicate_id(template_manager):
    """测试重复的步骤 ID"""
    template = {
        "name": "test",
        "steps": [
            {"id": "step1", "order": 1, "tool": "nmap", "args": {}},
            {"id": "step1", "order": 2, "tool": "ffuf", "args": {}}
        ]
    }

    is_valid, errors = template_manager.validate_template(template)
    assert not is_valid
    assert any("重复" in error for error in errors)


def test_validate_template_invalid_dependency(template_manager):
    """测试无效的依赖"""
    template = {
        "name": "test",
        "steps": [
            {
                "id": "step1",
                "order": 1,
                "tool": "nmap",
                "args": {},
                "depends_on": ["nonexistent"]
            }
        ]
    }

    is_valid, errors = template_manager.validate_template(template)
    assert not is_valid
    assert any("不存在" in error for error in errors)


def test_validate_template_circular_dependency(template_manager):
    """测试循环依赖"""
    template = {
        "name": "test",
        "steps": [
            {"id": "step1", "order": 1, "tool": "nmap", "args": {}, "depends_on": ["step2"]},
            {"id": "step2", "order": 2, "tool": "ffuf", "args": {}, "depends_on": ["step1"]}
        ]
    }

    is_valid, errors = template_manager.validate_template(template)
    assert not is_valid
    assert any("循环依赖" in error for error in errors)


def test_find_template_builtin(template_manager, tmp_path):
    """测试查找内置模板"""
    builtin_template = tmp_path / "builtin" / "test.json"
    builtin_template.write_text(json.dumps({"name": "test"}))

    found = template_manager.find_template("test")
    assert found == builtin_template


def test_find_template_user_priority(template_manager, tmp_path):
    """测试用户模板优先级"""
    builtin_template = tmp_path / "builtin" / "test.json"
    user_template = tmp_path / "user" / "test.json"

    builtin_template.write_text(json.dumps({"name": "builtin"}))
    user_template.write_text(json.dumps({"name": "user"}))

    found = template_manager.find_template("test")
    assert found == user_template


def test_find_template_file_path(template_manager, tmp_path):
    """测试直接文件路径"""
    custom_template = tmp_path / "custom.json"
    custom_template.write_text(json.dumps({"name": "custom"}))

    found = template_manager.find_template(str(custom_template))
    assert found == custom_template
