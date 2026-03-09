"""终端 UI 和进度显示模块"""
import asyncio
from datetime import datetime
from typing import Any, Optional
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.spinner import Spinner
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

console = Console()


class WorkflowUI:
    """工作流 UI 显示类"""

    def __init__(self, workflow_name: str, total_steps: int, verbose: bool = False, quiet: bool = False):
        """初始化 UI

        Args:
            workflow_name: 工作流名称
            total_steps: 总步骤数
            verbose: 详细模式
            quiet: 静默模式
        """
        self.workflow_name = workflow_name
        self.total_steps = total_steps
        self.verbose = verbose
        self.quiet = quiet
        self.steps_status: dict[str, dict[str, Any]] = {}
        self.completed_steps = 0
        self.live: Optional[Live] = None

    def init_step(self, step_id: str, step_name: str, order: int):
        """初始化步骤状态

        Args:
            step_id: 步骤 ID
            step_name: 步骤名称
            order: 执行顺序
        """
        self.steps_status[step_id] = {
            "id": step_id,
            "name": step_name,
            "order": order,
            "status": "pending",
            "start_time": None,
            "duration": 0,
            "save_result_as": None,
        }

    def update_step(
        self,
        step_id: str,
        status: str,
        duration: Optional[float] = None,
        error: Optional[str] = None,
    ):
        """更新步骤状态

        Args:
            step_id: 步骤 ID
            status: 状态 (pending, running, success, failed, skipped)
            duration: 持续时间（秒）
            error: 错误信息
        """
        if step_id in self.steps_status:
            self.steps_status[step_id]["status"] = status
            if duration is not None:
                self.steps_status[step_id]["duration"] = duration
            if error:
                self.steps_status[step_id]["error"] = error

            if status in ["success", "failed", "skipped"]:
                self.completed_steps += 1

    def set_step_result_name(self, step_id: str, result_name: str):
        """设置步骤结果名称

        Args:
            step_id: 步骤 ID
            result_name: 结果名称
        """
        if step_id in self.steps_status:
            self.steps_status[step_id]["save_result_as"] = result_name

    def _create_table(self) -> Table:
        """创建状态表格

        Returns:
            Rich Table 对象
        """
        # 计算进度
        progress_text = f"{self.completed_steps}/{self.total_steps}"

        # 创建表格
        table = Table(
            title=f"Workflow: {self.workflow_name} | Progress: {progress_text}",
            show_header=True,
            header_style="bold cyan",
        )

        table.add_column("执行名称", style="white", width=25)
        table.add_column("order", justify="center", width=7)
        table.add_column("时间", justify="right", width=8)
        table.add_column("进度条", width=15)
        table.add_column("是否保存结果", width=20)

        # 按 order 排序
        sorted_steps = sorted(self.steps_status.values(), key=lambda x: (x["order"], x["name"]))

        for step in sorted_steps:
            status = step["status"]
            duration = step["duration"]
            save_as = step.get("save_result_as", "-")

            # 状态图标和进度
            if status == "success":
                progress_display = "[green]✓ 100%[/green]"
                time_display = f"{duration:.0f}s"
            elif status == "running":
                progress_display = "[blue]▶ 执行中[/blue]"
                time_display = f"{duration:.0f}s"
            elif status == "failed":
                progress_display = "[red]✗ Failed[/red]"
                time_display = f"{duration:.0f}s"
            elif status == "skipped":
                progress_display = "[yellow]⊘ Skipped[/yellow]"
                time_display = "-"
            else:  # pending
                progress_display = "[dim]⏸ 0%[/dim]"
                time_display = "-"

            table.add_row(
                step["name"][:24],
                str(step["order"]),
                time_display,
                progress_display,
                save_as if save_as != "-" else "[dim]-[/dim]",
            )

        return table

    def _create_summary(self) -> str:
        """创建摘要信息

        Returns:
            摘要字符串
        """
        success_count = sum(1 for s in self.steps_status.values() if s["status"] == "success")
        failed_count = sum(1 for s in self.steps_status.values() if s["status"] == "failed")
        skipped_count = sum(1 for s in self.steps_status.values() if s["status"] == "skipped")

        total_duration = sum(s["duration"] for s in self.steps_status.values())

        if self.completed_steps == self.total_steps:
            status_text = "[green]✓ Completed[/green]" if failed_count == 0 else "[red]✗ Completed with errors[/red]"
        else:
            status_text = "[blue]▶ Running[/blue]"

        summary = f"\n{status_text}\n"
        summary += f"Summary: [green]✓ {success_count} success[/green] | "
        summary += f"[red]✗ {failed_count} failed[/red] | "
        summary += f"[yellow]⊘ {skipped_count} skipped[/yellow] | "
        summary += f"Total: {total_duration:.0f}s"

        return summary

    async def start(self):
        """启动 UI 显示"""
        if self.quiet:
            # 静默模式：只显示简化进度
            return

        if self.verbose:
            # 详细模式：不使用 Live 表格，直接输出
            return

        # 正常模式：使用 Live 表格
        self.live = Live(self._create_table(), console=console, refresh_per_second=1)
        self.live.start()

        # 启动更新任务
        asyncio.create_task(self._update_loop())

    async def _update_loop(self):
        """更新循环"""
        while self.completed_steps < self.total_steps:
            if self.live:
                # 更新运行中步骤的时间
                for step in self.steps_status.values():
                    if step["status"] == "running" and step["start_time"]:
                        step["duration"] = (datetime.now() - step["start_time"]).total_seconds()

                self.live.update(self._create_table())

            await asyncio.sleep(1)

        # 最后更新一次
        if self.live:
            self.live.update(self._create_table())

    def stop(self):
        """停止 UI 显示"""
        if self.live:
            self.live.stop()

        # 显示摘要
        if not self.quiet:
            console.print(self._create_summary())

    def print_step_start(self, step_name: str):
        """打印步骤开始信息（详细模式）

        Args:
            step_name: 步骤名称
        """
        if self.verbose:
            console.print(f"[blue]▶[/blue] {step_name} - 执行中...")

    def print_step_success(self, step_name: str, duration: float):
        """打印步骤成功信息（详细模式）

        Args:
            step_name: 步骤名称
            duration: 持续时间
        """
        if self.verbose:
            console.print(f"[green]✓[/green] {step_name} - 完成 ({duration:.1f}s)")

    def print_step_failed(self, step_name: str, error: str):
        """打印步骤失败信息（详细模式）

        Args:
            step_name: 步骤名称
            error: 错误信息
        """
        if self.verbose or not self.quiet:
            console.print(f"[red]✗[/red] {step_name} - 失败: {error}")

    def print_step_skipped(self, step_name: str, reason: str):
        """打印步骤跳过信息（详细模式）

        Args:
            step_name: 步骤名称
            reason: 跳过原因
        """
        if self.verbose:
            console.print(f"[yellow]⊘[/yellow] {step_name} - 跳过 ({reason})")

    def print_step_retry(self, step_name: str, attempt: int, max_retry: int):
        """打印步骤重试信息

        Args:
            step_name: 步骤名称
            attempt: 当前尝试次数
            max_retry: 最大重试次数
        """
        if self.verbose or not self.quiet:
            console.print(f"[yellow]↻[/yellow] {step_name} - 重试 {attempt}/{max_retry}")

    def print_command(self, command: str):
        """打印执行的命令（详细模式）

        Args:
            command: 命令字符串
        """
        if self.verbose:
            console.print(f"[dim]命令:[/dim] {command}")

    def print_output(self, output: str):
        """打印工具输出（详细模式）

        Args:
            output: 输出内容
        """
        if self.verbose:
            console.print(f"[dim]输出:[/dim]\n{output}")

    def print_quiet_progress(self):
        """打印静默模式的简化进度"""
        if self.quiet:
            console.print(f"[{self.completed_steps}/{self.total_steps}] 执行中...")


class SimpleSpinner:
    """简单的加载动画"""

    def __init__(self, text: str):
        """初始化加载动画

        Args:
            text: 显示文本
        """
        self.text = text
        self.spinner = Spinner("dots", text=text)
        self.live: Optional[Live] = None

    def start(self):
        """启动动画"""
        self.live = Live(self.spinner, console=console)
        self.live.start()

    def stop(self):
        """停止动画"""
        if self.live:
            self.live.stop()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
