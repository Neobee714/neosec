"""测试变量替换工具"""
import pytest
from neosec.utils.variables import (
    replace_variables,
    replace_string_variables,
    get_nested_value,
    set_nested_value,
)


def test_replace_string_variables_simple():
    """测试简单变量替换"""
    context = {"target": "example.com"}
    result = replace_string_variables("{{target}}", context)
    assert result == "example.com"


def test_replace_string_variables_nested():
    """测试嵌套变量替换"""
    context = {"result": {"data": {"port": 80}}}
    result = replace_string_variables("{{result.data.port}}", context)
    assert result == 80


def test_replace_string_variables_in_text():
    """测试文本中的变量替换"""
    context = {"target": "example.com", "port": 80}
    result = replace_string_variables("Scan {{target}} on port {{port}}", context)
    assert result == "Scan example.com on port 80"


def test_replace_string_variables_preserve_type():
    """测试保持变量类型"""
    context = {"ports": [80, 443, 22]}
    result = replace_string_variables("{{ports}}", context)
    assert result == [80, 443, 22]
    assert isinstance(result, list)


def test_replace_variables_dict():
    """测试替换字典中的变量"""
    obj = {
        "target": "{{domain}}",
        "port": "{{port}}",
        "nested": {"value": "{{nested_var}}"},
    }
    context = {"domain": "example.com", "port": 80, "nested_var": "test"}

    result = replace_variables(obj, context)

    assert result["target"] == "example.com"
    assert result["port"] == 80
    assert result["nested"]["value"] == "test"


def test_replace_variables_list():
    """测试替换列表中的变量"""
    obj = ["{{item1}}", "{{item2}}", {"key": "{{item3}}"}]
    context = {"item1": "a", "item2": "b", "item3": "c"}

    result = replace_variables(obj, context)

    assert result[0] == "a"
    assert result[1] == "b"
    assert result[2]["key"] == "c"


def test_get_nested_value():
    """测试获取嵌套值"""
    data = {"a": {"b": {"c": 123}}}

    assert get_nested_value(data, "a.b.c") == 123
    assert get_nested_value(data, "a.b") == {"c": 123}
    assert get_nested_value(data, "nonexistent", "default") == "default"


def test_set_nested_value():
    """测试设置嵌套值"""
    data = {}

    set_nested_value(data, "a.b.c", 123)

    assert data["a"]["b"]["c"] == 123


def test_replace_variables_missing():
    """测试缺失变量的处理"""
    context = {"existing": "value"}
    result = replace_string_variables("{{missing}}", context)
    assert result is None

    result = replace_string_variables("text {{missing}} more", context)
    assert result == "text None more"
