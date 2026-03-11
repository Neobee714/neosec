"""CLI 主入口"""
import typer
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.table import Table

from .. import __version__
from ..core.config import Config
from ..core.template import TemplateManager
from ..core.engine import WorkflowEngine

app = typer.Typer(
    name="neosec",
    help="Neosec - 网络安全测试工具集",
    add_completion=False,
)

console = Console()


@app.command()
def version():
    """显示版本信息"""
    console.print(f"Neosec v{__version__}")


@app.command()
def init(
    force: bool = typer.Option(False, "--force", "-f", help="强制重新初始化，覆盖现有配置")
):
    """初始化 Neosec 配置和目录结构"""
    config = Config()

    # 检查是否已初始化
    if config.config_path.exists() and not force:
        console.print("[yellow]配置文件已存在，使用 --force 强制重新初始化[/yellow]")
        return

    # 创建目录结构
    config.init_directories()
    console.print(f"[green]✓[/green] 目录结构已创建: {config.neosec_dir}")

    # 创建配置文件
    config.create_default_config()

    # 复制内置模板到用户目录
    builtin_templates_dir = Path(__file__).parent.parent / "templates"
    if builtin_templates_dir.exists():
        import shutil

        for template_file in builtin_templates_dir.glob("*.json"):
            dest = config.templates_dir / template_file.name
            shutil.copy(template_file, dest)
            console.print(f"[green]✓[/green] 模板已复制: {template_file.name}")

    console.print("\n[green]初始化完成！[/green]")
    console.print(f"配置文件: {config.config_path}")
    console.print(f"模板目录: {config.templates_dir}")
    console.print(f"日志目录: {config.log_dir}")
    console.print(f"历史目录: {config.history_dir}")


@app.command()
def workflow(
    template: Optional[str] = typer.Option(None, "--template", "-t", help="模板名称或文件路径"),
    list_templates: bool = typer.Option(False, "--list-templates", help="列出所有可用模板"),
    validate: Optional[str] = typer.Option(None, "--validate", help="验证模板文件"),
    variables: Optional[list[str]] = typer.Option(
        None, "--variables", "-v", help="变量值 (格式: key:value)"
    ),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="输出文件路径"),
    report: bool = typer.Option(False, "--report", help="生成 Markdown 报告"),
    dry_run: bool = typer.Option(False, "--dry-run", help="干运行模式，不实际执行"),
    config_path: Optional[str] = typer.Option(None, "--config", "-c", help="自定义配置文件路径"),
    verbose: bool = typer.Option(False, "--verbose", help="详细输出模式"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="静默模式"),
):
    """执行安全测试工作流"""
    # 加载配置
    config = Config(Path(config_path) if config_path else None)
    config.load()

    # 获取模板目录
    builtin_templates_dir = Path(__file__).parent.parent / "templates"
    user_templates_dir = config.templates_dir

    template_manager = TemplateManager(builtin_templates_dir, user_templates_dir)

    # 列出模板
    if list_templates:
        _list_templates(template_manager)
        return

    # 验证模板
    if validate:
        _validate_template(template_manager, validate)
        return

    # 执行工作流
    if not template:
        console.print("[red]错误:[/red] 请使用 --template 指定模板")
        raise typer.Exit(1)

    _execute_workflow(
        template_manager,
        config,
        template,
        variables or [],
        output,
        report,
        dry_run,
        verbose,
        quiet,
    )


@app.command()
def history(
    limit: int = typer.Option(10, "--limit", "-n", help="显示最近 N 条记录"),
    workflow_name: Optional[str] = typer.Option(None, "--workflow", "-w", help="筛选工作流名称"),
):
    """查看工作流执行历史"""
    config = Config()
    config.load()

    history_dir = config.history_dir

    if not history_dir.exists():
        console.print("[yellow]暂无执行历史[/yellow]")
        return

    # 获取历史文件
    history_files = sorted(history_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)

    if not history_files:
        console.print("[yellow]暂无执行历史[/yellow]")
        return

    # 创建表格
    table = Table(title="工作流执行历史")
    table.add_column("时间", style="cyan")
    table.add_column("工作流", style="magenta")
    table.add_column("状态", style="green")
    table.add_column("耗时", style="yellow")
    table.add_column("成功/失败/跳过", style="blue")

    import json

    count = 0
    for history_file in history_files:
        if count >= limit:
            break

        try:
            with open(history_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            workflow = data.get("workflow", {})
            summary = data.get("summary", {})

            # 筛选
            if workflow_name and workflow.get("name") != workflow_name:
                continue

            # 状态图标
            status = workflow.get("status", "unknown")
            status_icon = "✓" if status == "completed" else "✗"

            # 添加行
            table.add_row(
                workflow.get("start_time", "N/A")[:19],
                workflow.get("name", "N/A"),
                f"{status_icon} {status}",
                f"{workflow.get('duration', 0):.1f}s",
                f"{summary.get('successful', 0)}/{summary.get('failed', 0)}/{summary.get('skipped', 0)}",
            )

            count += 1

        except Exception as e:
            console.print(f"[yellow]警告:[/yellow] 无法读取历史文件 {history_file.name}: {e}")

    console.print(table)


def _list_templates(template_manager: TemplateManager):
    """列出所有模板"""
    templates = template_manager.list_templates()

    # 内置模板
    if templates["builtin"]:
        console.print("\n[bold cyan]内置模板:[/bold cyan]")
        for tmpl in templates["builtin"]:
            console.print(f"  [green]{tmpl['name']:30}[/green] {tmpl['description']}")

    # 用户模板
    if templates["user"]:
        console.print("\n[bold cyan]用户模板 (~/.neosec/templates/):[/bold cyan]")
        for tmpl in templates["user"]:
            console.print(f"  [green]{tmpl['name']:30}[/green] {tmpl['description']}")

    if not templates["builtin"] and not templates["user"]:
        console.print("[yellow]暂无可用模板，请运行 'neosec init' 初始化[/yellow]")


def _validate_template(template_manager: TemplateManager, template_path: str):
    """验证模板"""
    try:
        # 加载模板
        template_data = template_manager.load_template(template_path)
        console.print(f"[green]✓[/green] 模板加载成功: {template_path}")

        # 验证模板
        is_valid, errors = template_manager.validate_template(template_data)

        if is_valid:
            console.print("[green]✓[/green] 模板验证通过")
        else:
            console.print("[red]✗[/red] 模板验证失败:")
            for error in errors:
                console.print(f"  [red]•[/red] {error}")
            raise typer.Exit(1)

    except FileNotFoundError as e:
        console.print(f"[red]错误:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]错误:[/red] {e}")
        raise typer.Exit(1)


def _execute_workflow(
    template_manager: TemplateManager,
    config: Config,
    template_name: str,
    variables: list[str],
    output: Optional[str],
    report: bool,
    dry_run: bool,
    verbose: bool,
    quiet: bool,
):
    """执行工作流"""
    import asyncio

    try:
        # 加载模板
        template_data = template_manager.load_template(template_name)

        # 验证模板
        is_valid, errors = template_manager.validate_template(template_data)
        if not is_valid:
            console.print("[red]✗[/red] 模板验证失败:")
            for error in errors:
                console.print(f"  [red]•[/red] {error}")
            raise typer.Exit(1)

        # 解析变量
        vars_dict = {}
        for var in variables:
            if ":" not in var:
                console.print(f"[red]错误:[/red] 变量格式错误: {var} (应为 key:value)")
                raise typer.Exit(1)
            key, value = var.split(":", 1)
            vars_dict[key.strip()] = value.strip()

        # 确定输出文件
        if not output:
            output = config.get("output.default_path", "./") + config.get(
                "output.default_filename", "workflow_result.json"
            )

        # 创建执行引擎
        engine = WorkflowEngine(config, verbose=verbose, quiet=quiet, dry_run=dry_run)

        # 执行工作流
        if not quiet:
            console.print(f"\n[bold cyan]执行工作流:[/bold cyan] {template_data['name']}")
            console.print(f"[dim]模板:[/dim] {template_name}")
            console.print(f"[dim]变量:[/dim] {vars_dict}")
            if dry_run:
                console.print("[yellow]干运行模式 - 不会实际执行工具[/yellow]\n")

        result = asyncio.run(engine.execute(template_data, vars_dict, output))

        # 显示摘要
        if not quiet:
            summary = result["summary"]
            workflow = result["workflow"]

            console.print(f"\n[bold]执行完成![/bold]")
            console.print(
                f"状态: {'[green]✓ 成功[/green]' if summary['failed'] == 0 else '[red]✗ 有失败[/red]'}"
            )
            console.print(
                f"总计: {summary['total_steps']} 步骤 | "
                f"[green]✓ {summary['successful']}[/green] | "
                f"[red]✗ {summary['failed']}[/red] | "
                f"[yellow]⊘ {summary['skipped']}[/yellow]"
            )
            console.print(f"耗时: {workflow['duration']:.1f}秒")
            console.print(f"结果: {output}")

        # 生成 Markdown 报告
        if report and not dry_run:
            _generate_markdown_report(result, output)

        # 保存到历史
        if not dry_run:
            _save_to_history(config, result)

    except FileNotFoundError as e:
        console.print(f"[red]错误:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]错误:[/red] {e}")
        if verbose:
            import traceback

            console.print(traceback.format_exc())
        raise typer.Exit(1)


def _generate_markdown_report(result: dict, output_file: str):
    """生成包含扫描结果的完整 Markdown 报告"""
    report_path = Path(output_file).with_suffix(".md")
    workflow = result["workflow"]
    summary = result["summary"]
    steps = result["steps"]
    variables = result.get("variables", {})
    target = variables.get("target", "unknown")
    start = workflow.get("start_time", "")[:19].replace("T", " ")
    end = workflow.get("end_time", "")[:19].replace("T", " ")
    duration = workflow.get("duration", 0)
    status_str = "✓ 成功" if summary["failed"] == 0 else "✗ 有失败"
    L: list[str] = []

    # 标题概要
    L += [
        "# 渗透测试扫描报告", "",
        "| 项目 | 内容 |", "|---|---|",
        f"| 目标 | `{target}` |",
        f"| 开始时间 | {start} |",
        f"| 结束时间 | {end} |",
        f"| 总耗时 | {duration:.1f} 秒 |",
        f"| 状态 | {status_str} |",
        f"| 步骤 成功/失败/跳过 | {summary['successful']} / {summary['failed']} / {summary['skipped']} |",
        "",
    ]

    # Nmap 结果
    nmap_step = next((s for s in steps if s.get("id") == "port_scan"), None)
    nmap_result = nmap_step.get("result") if nmap_step else None
    L.append("## 端口扫描结果")
    L.append("")
    if nmap_result and isinstance(nmap_result, dict):
        open_ports = nmap_result.get("open_ports", [])
        services = nmap_result.get("services", [])
        ports_str = ", ".join(str(p) for p in open_ports) if open_ports else "无"
        L.append(f"**开放端口:** {ports_str}")
        L.append("")
        if services:
            L += ["| 端口 | 协议 | 服务 | 版本信息 |", "|---:|---|---|---|"]
            for svc in services:
                port = svc.get('port', '-')
                proto = svc.get('protocol', '-')
                svc_name = svc.get('service', '-')
                ver_str = f"{svc.get('product','')}"
                ver_str2 = f"{svc.get('version','')}"
                ver = f"{ver_str} {ver_str2}".strip() or '-'
                L.append(f"| {port} | {proto} | {svc_name} | {ver} |")
            L.append("")
    else:
        L += ["> 扫描失败或无结果", ""]

    # Web 目录爆破结果
    ffuf_steps = [s for s in steps if s.get("id", "").startswith("ffuf_port_")]
    executed_ffuf = [s for s in ffuf_steps if s.get("status") == "success"]
    skipped_ffuf = [s for s in ffuf_steps if s.get("status") == "skipped"]
    L += ["## Web 目录爆破结果", ""]

    if not executed_ffuf:
        L += ["> 未发现 Web 端口，跳过目录爆破", ""]
    else:
        for s in executed_ffuf:
            step_result = s.get("result")
            step_name = s.get("name", s.get("id", ""))
            L.append(f"### {step_name}")
            L.append("")
            if not step_result or not isinstance(step_result, dict):
                L += ["> 无结果数据", ""]
                continue
            entries = step_result.get("entries", [])
            cmd = step_result.get("commandline", "")
            scan_time = step_result.get("scan_time", "")
            report_md = step_result.get("report_markdown", "")
            if cmd:
                L += [f"```", cmd, "```", ""]
            if scan_time:
                L += [f"扫描时间: `{scan_time}`", ""]
            if not entries:
                # Try to read raw stdout from result dir
                result_dir = Path.home() / ".neosec" / "result" / target
                step_id = s.get("id", "")
                txt_file = result_dir / f"{step_id}.txt"
                if txt_file.exists():
                    L.append("```")
                    L.append(txt_file.read_text(encoding="utf-8", errors="replace").rstrip())
                    L.append("```")
                    L.append("")
                else:
                    L += ["> 无命中结果", ""]
                continue
            status_counts: dict = {}
            for e in entries:
                sc = e.get("status")
                if isinstance(sc, int):
                    status_counts[sc] = status_counts.get(sc, 0) + 1
            dist = "  ".join(f"`{code}` ×{cnt}" for code, cnt in sorted(status_counts.items()))
            L.append(f"**命中:** {len(entries)} 条　**状态码:** {dist}")
            L.append("")
            L += ["| 路径 | 状态 | 大小(B) | 耗时(ms) | 重定向 |",
                  "|---|---:|---:|---:|---|"]
            for entry in entries:
                path = str(entry.get('path', '/')).replace('|', '\\|')
                redirect = str(entry.get('redirectlocation', ''))
                sc2 = entry.get('status', '-')
                badge = f"**{sc2}**" if sc2 in (200, 301, 302, 401) else str(sc2)
                L.append(f"| `{path}` | {badge} | {entry.get('length','-')} "
                         f"| {entry.get('duration_ms','-')} | {redirect} |")
            L.append("")
            if report_md and Path(report_md).exists():
                L += [f"> 详细报告: `{report_md}`", ""]

    if skipped_ffuf:
        names = ", ".join(s.get("name", s.get("id", "")) for s in skipped_ffuf)
        L += [f"> 已跳过（端口未开放）: {names}", ""]

    # 执行步骤摘要
    L += ["## 执行步骤", ""]
    for step in steps:
        if step.get("status") == "skipped":
            continue
        icon = {"success": "✓", "failed": "✗"}.get(step["status"], "?")
        dur = f"{step['duration']:.1f}s" if step.get("duration") else "-"
        L.append(f"- {icon} **{step['name']}** — {dur}")
        if step.get("error") and step["status"] == "failed":
            L.append(f"  - 错误: {step['error']}")
    L.append("")

    report_path.write_text("\n".join(L), encoding="utf-8")
    console.print(f"[green]✓[/green] Markdown 报告已生成: {report_path}")

def _save_to_history(config: Config, result: dict):
    """保存到历史"""
    import json
    from datetime import datetime

    history_dir = config.history_dir
    history_dir.mkdir(parents=True, exist_ok=True)

    # 生成文件名
    workflow_name = result["workflow"]["name"]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"workflow_{workflow_name}_{timestamp}.json"

    history_file = history_dir / filename

    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    app()
