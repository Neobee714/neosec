"""工作流执行引擎"""
import asyncio
import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from rich.console import Console

from ..utils.variables import replace_variables, get_nested_value

console = Console()


class WorkflowEngine:
    """工作流执行引擎"""

    def __init__(self, config, verbose: bool = False, quiet: bool = False, dry_run: bool = False):
        """初始化执行引擎

        Args:
            config: 配置对象
            verbose: 详细模式
            quiet: 静默模式
            dry_run: 干运行模式
        """
        self.config = config
        self.verbose = verbose
        self.quiet = quiet
        self.dry_run = dry_run

        self.context: dict[str, Any] = {
            "variables": {},
            "results": {},
            "metadata": {},
        }

        self.steps_status: dict[str, dict[str, Any]] = {}

    async def execute(
        self,
        template: dict[str, Any],
        variables: dict[str, str],
        output_file: Optional[str] = None,
    ) -> dict[str, Any]:
        """执行工作流

        Args:
            template: 模板数据
            variables: 命令行变量
            output_file: 输出文件路径

        Returns:
            执行结果
        """
        # 初始化上下文
        self._init_context(template, variables)

        # 记录开始时间
        start_time = datetime.now()
        self.context["metadata"]["start_time"] = start_time.isoformat()
        self.context["metadata"]["workflow_name"] = template["name"]

        # 替换模板中的变量
        steps = replace_variables(template["steps"], self.context)

        # 按 order 分组
        order_groups = self._group_by_order(steps)

        # 执行每个 order 组
        for order in sorted(order_groups.keys()):
            await self._execute_order_group(order_groups[order])

        # 记录结束时间
        end_time = datetime.now()
        self.context["metadata"]["end_time"] = end_time.isoformat()
        self.context["metadata"]["duration"] = (end_time - start_time).total_seconds()

        # 生成执行结果
        result = self._generate_result(template)

        # 保存结果
        if output_file and not self.dry_run:
            self._save_result(result, output_file)

        return result

    def _init_context(self, template: dict[str, Any], variables: dict[str, str]) -> None:
        """初始化执行上下文

        Args:
            template: 模板数据
            variables: 命令行变量
        """
        # 优先级：命令行 > 模板默认值 > 配置文件
        template_vars = template.get("variables", {})
        config_defaults = self.config.get("defaults", {})

        # 合并变量
        self.context["variables"] = {**config_defaults, **template_vars, **variables}

    def _group_by_order(self, steps: list[dict]) -> dict[int, list[dict]]:
        """按 order 分组步骤

        Args:
            steps: 步骤列表

        Returns:
            {order: [steps]}
        """
        groups: dict[int, list[dict]] = {}

        for step in steps:
            order = step["order"]
            if order not in groups:
                groups[order] = []
            groups[order].append(step)

        return groups

    async def _execute_order_group(self, steps: list[dict]) -> None:
        """执行同一 order 的步骤组（支持并行）

        Args:
            steps: 步骤列表
        """
        # 按 parallel_group 分组
        parallel_groups: dict[Optional[str], list[dict]] = {}

        for step in steps:
            group_name = step.get("parallel_group")
            if group_name not in parallel_groups:
                parallel_groups[group_name] = []
            parallel_groups[group_name].append(step)

        # 执行每个并行组
        tasks = []
        for group_name, group_steps in parallel_groups.items():
            if group_name:
                # 并行组内的步骤并行执行
                for step in group_steps:
                    tasks.append(self._execute_step(step))
            else:
                # 没有 parallel_group 的步骤也可以并行（如果没有依赖冲突）
                for step in group_steps:
                    tasks.append(self._execute_step(step))

        # 等待所有任务完成
        await asyncio.gather(*tasks)

    async def _execute_step(self, step: dict[str, Any]) -> None:
        """执行单个步骤

        Args:
            step: 步骤数据
        """
        step_id = step["id"]
        step_name = step.get("name", step_id)

        # 初始化步骤状态
        self.steps_status[step_id] = {
            "id": step_id,
            "name": step_name,
            "status": "pending",
            "start_time": None,
            "end_time": None,
            "duration": None,
            "result": None,
            "error": None,
        }

        # 检查依赖
        if not self._check_dependencies(step):
            self.steps_status[step_id]["status"] = "skipped"
            self.steps_status[step_id]["error"] = "dependency failed"
            if self.verbose:
                console.print(f"[yellow]⊘[/yellow] {step_name} - 跳过（依赖失败）")
            return

        # 检查条件
        if not self._check_condition(step):
            self.steps_status[step_id]["status"] = "skipped"
            self.steps_status[step_id]["error"] = "condition not met"
            if self.verbose:
                console.print(f"[yellow]⊘[/yellow] {step_name} - 跳过（条件不满足）")
            return

        # 处理 for_each
        if "for_each" in step:
            await self._execute_for_each(step)
            return

        # 执行步骤
        start_time = datetime.now()
        self.steps_status[step_id]["start_time"] = start_time.isoformat()
        self.steps_status[step_id]["status"] = "running"

        if self.verbose:
            console.print(f"[blue]▶[/blue] {step_name} - 执行中...")

        # 重试机制
        retry_count = step.get("retry", 0)
        for attempt in range(retry_count + 1):
            try:
                if attempt > 0:
                    if self.verbose:
                        console.print(
                            f"[yellow]↻[/yellow] {step_name} - 重试 {attempt}/{retry_count}"
                        )
                    await asyncio.sleep(5)  # 等待 5 秒后重试

                result = await self._run_tool(step)

                # 成功
                end_time = datetime.now()
                self.steps_status[step_id]["status"] = "success"
                self.steps_status[step_id]["end_time"] = end_time.isoformat()
                self.steps_status[step_id]["duration"] = (end_time - start_time).total_seconds()
                self.steps_status[step_id]["result"] = result

                # 保存结果
                if "save_result_as" in step:
                    self.context["results"][step["save_result_as"]] = result

                if self.verbose:
                    console.print(f"[green]✓[/green] {step_name} - 完成")

                break

            except Exception as e:
                if attempt == retry_count:
                    # 最后一次重试失败
                    end_time = datetime.now()
                    self.steps_status[step_id]["status"] = "failed"
                    self.steps_status[step_id]["end_time"] = end_time.isoformat()
                    self.steps_status[step_id]["duration"] = (
                        end_time - start_time
                    ).total_seconds()
                    self.steps_status[step_id]["error"] = str(e)

                    if self.verbose or not self.quiet:
                        console.print(f"[red]✗[/red] {step_name} - 失败: {e}")

                    # 检查是否继续执行
                    if not step.get("continue_on_error", False):
                        raise

                    break

    def _check_dependencies(self, step: dict[str, Any]) -> bool:
        """检查步骤依赖是否满足

        Args:
            step: 步骤数据

        Returns:
            依赖是否满足
        """
        depends_on = step.get("depends_on", [])

        for dep_id in depends_on:
            dep_status = self.steps_status.get(dep_id, {}).get("status")
            if dep_status != "success":
                return False

        return True

    def _check_condition(self, step: dict[str, Any]) -> bool:
        """��查步骤条件是否满足

        Args:
            step: 步骤数据

        Returns:
            条件是否满足
        """
        if "when" not in step:
            return True

        when = step["when"]
        condition_type = when["type"]
        source = when["source"]

        # 获取源数据
        source_value = get_nested_value(self.context["results"], source)

        if source_value is None:
            return False

        # 检查条件
        if condition_type == "contains":
            value = when["value"]
            return value in source_value if isinstance(source_value, (list, str)) else False

        elif condition_type == "contains_any":
            values = when["values"]
            if isinstance(source_value, list):
                return any(v in source_value for v in values)
            return False

        elif condition_type == "not_contains_any":
            values = when["values"]
            if isinstance(source_value, list):
                return not any(v in source_value for v in values)
            return True

        elif condition_type == "equals":
            value = when["value"]
            return source_value == value

        elif condition_type == "greater_than":
            value = when["value"]
            return source_value > value

        elif condition_type == "less_than":
            value = when["value"]
            return source_value < value

        return False

    async def _execute_for_each(self, step: dict[str, Any]) -> None:
        """执行 for_each 循环

        Args:
            step: 步骤数据
        """
        for_each_path = step["for_each"].strip("{}")
        items = get_nested_value(self.context["results"], for_each_path, [])

        if not isinstance(items, list):
            console.print(f"[red]错误:[/red] for_each 的值不是数组: {for_each_path}")
            return

        # 为每个 item 执行步骤
        for item in items:
            # 创建临时上下文
            temp_context = {**self.context, "item": item}
            temp_step = replace_variables(step, temp_context)
            await self._execute_step(temp_step)

    async def _run_tool(self, step: dict[str, Any]) -> dict[str, Any]:
        """运行工具

        Args:
            step: 步骤数据

        Returns:
            工具执行结果
        """
        tool_name = step["tool"]
        args = step.get("args", {})
        timeout = step.get("timeout", self.config.get("defaults.timeout", 300))

        # 获取工具路径
        tool_path = self.config.get_tool_path(tool_name)

        # 检查工具是否存在
        if not self.dry_run and not shutil.which(tool_path):
            raise FileNotFoundError(f"工具未找到: {tool_path}")

        # 构建命令
        cmd = [tool_path]
        for key, value in args.items():
            if key.startswith("-"):
                # 选项参数
                if isinstance(value, bool):
                    if value:
                        cmd.append(key)
                else:
                    cmd.extend([key, str(value)])
            else:
                # 位置参数
                cmd.append(str(value))

        if self.verbose or self.dry_run:
            console.print(f"[dim]命令:[/dim] {' '.join(cmd)}")

        if self.dry_run:
            return {"status": "dry_run", "command": " ".join(cmd)}

        # 执行命令
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)

            if process.returncode != 0:
                raise RuntimeError(
                    f"工具执行失败 (退出码 {process.returncode}): {stderr.decode()}"
                )

            # 解析输出
            output = stdout.decode()

            if self.verbose:
                console.print(f"[dim]输出:[/dim]\n{output}")

            # 尝试解析为 JSON
            try:
                result = json.loads(output)
            except json.JSONDecodeError:
                # 如果不是 JSON，返回原始输出
                result = {"status": "success", "raw_output": output}

            return result

        except asyncio.TimeoutError:
            if process:
                process.kill()
                await process.wait()
            raise TimeoutError(f"工具执行超时 ({timeout}秒)")

    def _generate_result(self, template: dict[str, Any]) -> dict[str, Any]:
        """生成执行结果

        Args:
            template: 模板数据

        Returns:
            执行结果
        """
        steps_result = []
        summary = {"total_steps": 0, "successful": 0, "failed": 0, "skipped": 0}

        for step_id, status in self.steps_status.items():
            steps_result.append(status)
            summary["total_steps"] += 1

            if status["status"] == "success":
                summary["successful"] += 1
            elif status["status"] == "failed":
                summary["failed"] += 1
            elif status["status"] == "skipped":
                summary["skipped"] += 1

        return {
            "workflow": {
                "name": template["name"],
                "version": template.get("version", "1.0.0"),
                "start_time": self.context["metadata"].get("start_time"),
                "end_time": self.context["metadata"].get("end_time"),
                "duration": self.context["metadata"].get("duration"),
                "status": "completed" if summary["failed"] == 0 else "completed_with_errors",
            },
            "variables": self.context["variables"],
            "steps": steps_result,
            "summary": summary,
        }

    def _save_result(self, result: dict[str, Any], output_file: str) -> None:
        """保存执行结果

        Args:
            result: 执行结果
            output_file: 输出文件路径
        """
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        if not self.quiet:
            console.print(f"[green]✓[/green] 结果已保存: {output_path}")
