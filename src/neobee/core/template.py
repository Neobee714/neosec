"""模板管理模块"""
import json
from pathlib import Path
from typing import Any, Optional
from rich.console import Console

console = Console()


class TemplateManager:
    """模板管理类"""

    def __init__(self, builtin_templates_dir: Path, user_templates_dir: Path):
        """初始化模板管理器

        Args:
            builtin_templates_dir: 内置模板目录
            user_templates_dir: 用户模板目录
        """
        self.builtin_templates_dir = builtin_templates_dir
        self.user_templates_dir = user_templates_dir

    def list_templates(self) -> dict[str, list[dict[str, str]]]:
        """列出所有可用模板

        Returns:
            {"builtin": [...], "user": [...]}
        """
        result = {"builtin": [], "user": []}

        # 列出内置模板
        if self.builtin_templates_dir.exists():
            for template_file in self.builtin_templates_dir.glob("*.json"):
                try:
                    with open(template_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    result["builtin"].append({
                        "name": template_file.stem,
                        "description": data.get("description", "无描述"),
                        "path": str(template_file),
                    })
                except Exception as e:
                    console.print(f"[yellow]警告:[/yellow] 无法读取模板 {template_file.name}: {e}")

        # 列出用户模板
        if self.user_templates_dir.exists():
            for template_file in self.user_templates_dir.glob("*.json"):
                try:
                    with open(template_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    result["user"].append({
                        "name": template_file.stem,
                        "description": data.get("description", "无描述"),
                        "path": str(template_file),
                    })
                except Exception as e:
                    console.print(f"[yellow]警告:[/yellow] 无法读取模板 {template_file.name}: {e}")

        return result

    def find_template(self, template_name: str) -> Optional[Path]:
        """查找模板文件

        查找顺序：用户模板 > 内置模板 > 文件路径

        Args:
            template_name: 模板名称或路径

        Returns:
            模板文件路径，如果未找到返回 None
        """
        # 如果是文件路径
        template_path = Path(template_name)
        if template_path.exists() and template_path.is_file():
            return template_path

        # 查找用户模板
        user_template = self.user_templates_dir / f"{template_name}.json"
        if user_template.exists():
            return user_template

        # 查找内置模板
        builtin_template = self.builtin_templates_dir / f"{template_name}.json"
        if builtin_template.exists():
            return builtin_template

        return None

    def load_template(self, template_name: str) -> dict[str, Any]:
        """加载模板

        Args:
            template_name: 模板名称或路径

        Returns:
            模板数据字典

        Raises:
            FileNotFoundError: 模板文件不存在
            json.JSONDecodeError: JSON 格式错误
        """
        template_path = self.find_template(template_name)

        if not template_path:
            raise FileNotFoundError(f"模板未找到: {template_name}")

        with open(template_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def validate_template(self, template_data: dict[str, Any]) -> tuple[bool, list[str]]:
        """验证模板格式

        Args:
            template_data: 模板数据

        Returns:
            (是否有效, 错误信息列表)
        """
        errors = []

        # 检查必需字段
        if "name" not in template_data:
            errors.append("缺少必需字段: name")

        if "steps" not in template_data:
            errors.append("缺少必需字段: steps")
        elif not isinstance(template_data["steps"], list):
            errors.append("steps 必须是数组")
        else:
            # 验证每个步骤
            step_ids = set()
            for i, step in enumerate(template_data["steps"]):
                step_errors = self._validate_step(step, i, step_ids)
                errors.extend(step_errors)
                if "id" in step:
                    step_ids.add(step["id"])

            # 检查依赖关系
            dep_errors = self._validate_dependencies(template_data["steps"], step_ids)
            errors.extend(dep_errors)

        # 检查变量引用
        var_errors = self._validate_variables(template_data)
        errors.extend(var_errors)

        return len(errors) == 0, errors

    def _validate_step(self, step: dict, index: int, existing_ids: set) -> list[str]:
        """验证单个步骤

        Args:
            step: 步骤数据
            index: 步骤索引
            existing_ids: 已存在的步骤 ID 集合

        Returns:
            错误信息列表
        """
        errors = []
        prefix = f"步骤 [{index}]"

        # 检查必需字段
        required_fields = ["id", "order", "tool", "args"]
        for field in required_fields:
            if field not in step:
                errors.append(f"{prefix} 缺少必需字段: {field}")

        # 检查 ID 唯一性
        if "id" in step:
            if step["id"] in existing_ids:
                errors.append(f"{prefix} ID 重复: {step['id']}")

        # 检查 order 类型
        if "order" in step and not isinstance(step["order"], int):
            errors.append(f"{prefix} order 必须是整数")

        # 检查 args 类型
        if "args" in step and not isinstance(step["args"], dict):
            errors.append(f"{prefix} args 必须是对象")

        # 检查 timeout 类型
        if "timeout" in step and not isinstance(step["timeout"], (int, float)):
            errors.append(f"{prefix} timeout 必须是数字")

        # 检查 retry 类型
        if "retry" in step and not isinstance(step["retry"], int):
            errors.append(f"{prefix} retry 必须是整数")

        # 检查 when 条件
        if "when" in step:
            when_errors = self._validate_when_condition(step["when"], prefix)
            errors.extend(when_errors)

        return errors

    def _validate_when_condition(self, when: dict, prefix: str) -> list[str]:
        """验证 when 条件

        Args:
            when: when 条件数据
            prefix: 错误信息前缀

        Returns:
            错误信息列表
        """
        errors = []

        if "type" not in when:
            errors.append(f"{prefix} when 条件缺少 type 字段")
        elif when["type"] not in [
            "contains",
            "contains_any",
            "not_contains_any",
            "equals",
            "greater_than",
            "less_than",
        ]:
            errors.append(f"{prefix} when 条件类型无效: {when['type']}")

        if "source" not in when:
            errors.append(f"{prefix} when 条件缺少 source 字段")

        # 检查 value 或 values
        if when.get("type") in ["contains_any", "not_contains_any"]:
            if "values" not in when:
                errors.append(f"{prefix} when 条件缺少 values 字段")
            elif not isinstance(when["values"], list):
                errors.append(f"{prefix} when 条件的 values 必须是数组")
        else:
            if "value" not in when:
                errors.append(f"{prefix} when 条件缺少 value 字段")

        return errors

    def _validate_dependencies(self, steps: list[dict], step_ids: set) -> list[str]:
        """验证依赖关系

        Args:
            steps: 步骤列表
            step_ids: 所有步骤 ID 集合

        Returns:
            错误信息列表
        """
        errors = []

        for step in steps:
            if "depends_on" in step:
                if not isinstance(step["depends_on"], list):
                    errors.append(f"步骤 {step.get('id', '?')} 的 depends_on 必须是数组")
                    continue

                for dep_id in step["depends_on"]:
                    if dep_id not in step_ids:
                        errors.append(
                            f"步骤 {step.get('id', '?')} 依赖的步骤不存在: {dep_id}"
                        )

        # 检查循环依赖
        cycle_errors = self._check_circular_dependencies(steps)
        errors.extend(cycle_errors)

        return errors

    def _check_circular_dependencies(self, steps: list[dict]) -> list[str]:
        """检查循环依赖

        Args:
            steps: 步骤列表

        Returns:
            错误信息列表
        """
        errors = []
        graph = {}

        # 构建依赖图
        for step in steps:
            step_id = step.get("id")
            if step_id:
                graph[step_id] = step.get("depends_on", [])

        # DFS 检测环
        visited = set()
        rec_stack = set()

        def has_cycle(node: str, path: list[str]) -> bool:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor, path):
                        return True
                elif neighbor in rec_stack:
                    cycle_path = path[path.index(neighbor):] + [neighbor]
                    errors.append(f"检测到循环依赖: {' -> '.join(cycle_path)}")
                    return True

            path.pop()
            rec_stack.remove(node)
            return False

        for node in graph:
            if node not in visited:
                has_cycle(node, [])

        return errors

    def _validate_variables(self, template_data: dict[str, Any]) -> list[str]:
        """验证变量引用

        Args:
            template_data: 模板数据

        Returns:
            错误信息列表
        """
        errors = []
        defined_vars = set(template_data.get("variables", {}).keys())

        # 收集所有变量引用
        import re

        var_pattern = re.compile(r"\{\{(\w+(?:\.\w+)*)\}\}")

        def find_variables(obj: Any, path: str = "") -> None:
            if isinstance(obj, dict):
                for key, value in obj.items():
                    find_variables(value, f"{path}.{key}" if path else key)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    find_variables(item, f"{path}[{i}]")
            elif isinstance(obj, str):
                matches = var_pattern.findall(obj)
                for match in matches:
                    var_name = match.split(".")[0]
                    # 检查是否是定义的变量或结果引用
                    if var_name not in defined_vars and not self._is_result_reference(
                        var_name, template_data
                    ):
                        errors.append(f"未定义的变量引用: {{{{{match}}}}} (位置: {path})")

        find_variables(template_data.get("steps", []))

        return errors

    def _is_result_reference(self, var_name: str, template_data: dict) -> bool:
        """检查是否是结果引用

        Args:
            var_name: 变量名
            template_data: 模板数据

        Returns:
            是否是结果引用
        """
        for step in template_data.get("steps", []):
            if step.get("save_result_as") == var_name:
                return True
        return False
