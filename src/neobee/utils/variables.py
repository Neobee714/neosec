"""变量替换工具"""
import re
from typing import Any


def replace_variables(obj: Any, context: dict[str, Any]) -> Any:
    """递归替换对象中的变量

    Args:
        obj: 要处理的对象
        context: 变量上下文

    Returns:
        替换后的对象
    """
    if isinstance(obj, dict):
        return {key: replace_variables(value, context) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [replace_variables(item, context) for item in obj]
    elif isinstance(obj, str):
        return replace_string_variables(obj, context)
    else:
        return obj


def replace_string_variables(text: str, context: dict[str, Any]) -> Any:
    """替换字符串中的变量

    支持格式：
    - {{variable}}
    - {{result.field}}
    - {{result.nested.field}}

    Args:
        text: 要处理的字符串
        context: 变量上下文

    Returns:
        替换后的值（可能是字符串、数字、列表等）
    """
    # 匹配 {{variable}} 或 {{variable.field}}
    pattern = re.compile(r"\{\{(\w+(?:\.\w+)*)\}\}")

    # 如果整个字符串就是一个变量引用，直接返回值（保持类型）
    match = pattern.fullmatch(text)
    if match:
        var_path = match.group(1)
        return get_nested_value(context, var_path)

    # 否则进行字符串替换
    def replacer(match):
        var_path = match.group(1)
        value = get_nested_value(context, var_path)
        return str(value) if value is not None else match.group(0)

    return pattern.sub(replacer, text)


def get_nested_value(data: dict[str, Any], path: str, default: Any = None) -> Any:
    """获取嵌套字典的值

    Args:
        data: 数据字典
        path: 点���分隔的路径，如 "result.data.ports"
        default: 默认值

    Returns:
        获取的值
    """
    keys = path.split(".")
    value = data

    for key in keys:
        if isinstance(value, dict):
            value = value.get(key)
            if value is None:
                return default
        else:
            return default

    return value


def set_nested_value(data: dict[str, Any], path: str, value: Any) -> None:
    """设置嵌套字典的值

    Args:
        data: 数据字典
        path: 点号分隔的路径
        value: 要设置的值
    """
    keys = path.split(".")
    current = data

    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]

    current[keys[-1]] = value
