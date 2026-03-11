"""工作流执行引擎"""
import asyncio
import json
import re
import shutil
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from rich.console import Console

from ..utils.variables import get_nested_value, replace_variables

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
        self._output_dir: Optional[str] = None
        self._ansi_escape_re = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
        self._non_printable_re = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")

    async def execute(
        self,
        template: dict[str, Any],
        variables: dict[str, str],
        output_file: Optional[str] = None,
    ) -> dict[str, Any]:
        """执行工作流"""
        self._init_context(template, variables)

        # Set output directory early so tools can write files there
        if output_file:
            self._output_dir = str(Path(output_file).parent)

        start_time = datetime.now()
        self.context["metadata"]["start_time"] = start_time.isoformat()
        self.context["metadata"]["workflow_name"] = template["name"]

        steps = template["steps"]
        order_groups = self._group_by_order(steps)

        for order in sorted(order_groups.keys()):
            await self._execute_order_group(order_groups[order])

        end_time = datetime.now()
        self.context["metadata"]["end_time"] = end_time.isoformat()
        self.context["metadata"]["duration"] = (end_time - start_time).total_seconds()

        result = self._generate_result(template)

        if output_file and not self.dry_run:
            self._save_result(result, output_file)

        return result

    def _init_context(self, template: dict[str, Any], variables: dict[str, str]) -> None:
        """初始化执行上下文"""
        template_vars = template.get("variables", {})
        config_defaults = self.config.get("defaults", {})
        self.context["variables"] = {**config_defaults, **template_vars, **variables}

    def _build_template_context(self, item: Any = None) -> dict[str, Any]:
        """构建模板变量替换上下文。"""
        variables = self.context.get("variables", {})
        results = self.context.get("results", {})
        metadata = self.context.get("metadata", {})

        context: dict[str, Any] = {**variables, **results}
        context["variables"] = variables
        context["results"] = results
        context["metadata"] = metadata

        if item is not None:
            context["item"] = item

        return context

    def _group_by_order(self, steps: list[dict]) -> dict[int, list[dict]]:
        """按 order 分组步骤。"""
        groups: dict[int, list[dict]] = {}

        for step in steps:
            order = step["order"]
            if order not in groups:
                groups[order] = []
            groups[order].append(step)

        return groups

    async def _execute_order_group(self, steps: list[dict]) -> None:
        """执行同一 order 的步骤组（支持并行）。"""
        remaining = list(steps)

        while remaining:
            remaining_ids = {step.get("id") for step in remaining if "id" in step}
            runnable = []

            for step in remaining:
                depends_on = step.get("depends_on", [])
                unresolved_same_order = any(dep in remaining_ids for dep in depends_on)
                if not unresolved_same_order:
                    runnable.append(step)

            if not runnable:
                unresolved = [step.get("id", "unknown") for step in remaining]
                raise RuntimeError(
                    f"同一 order 组内存在无法解析的依赖关系: {', '.join(unresolved)}"
                )

            await asyncio.gather(*(self._execute_step(step) for step in runnable))

            runnable_refs = {id(step) for step in runnable}
            remaining = [step for step in remaining if id(step) not in runnable_refs]

    async def _execute_step(self, step: dict[str, Any]) -> None:
        """执行单个步骤。"""
        raw_step = step
        resolved_step = replace_variables(raw_step, self._build_template_context())

        step_id = resolved_step["id"]
        step_name = resolved_step.get("name", step_id)

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

        if not self._check_dependencies(resolved_step):
            self.steps_status[step_id]["status"] = "skipped"
            self.steps_status[step_id]["error"] = None
            if self.verbose:
                console.print(f"[yellow]⊘ SKIP[/yellow]  {step_name} [dim](依赖失败)[/dim]")
            return

        if not self._check_condition(resolved_step):
            self.steps_status[step_id]["status"] = "skipped"
            self.steps_status[step_id]["error"] = None
            if self.verbose:
                console.print(f"[yellow]⊘ SKIP[/yellow]  {step_name} [dim](端口未开放)[/dim]")
            return

        start_time = datetime.now()
        self.steps_status[step_id]["start_time"] = start_time.isoformat()
        self.steps_status[step_id]["status"] = "running"

        if self.verbose:
            console.print(f"[blue]▶ RUN[/blue]   {step_name}")

        try:
            if "for_each" in raw_step:
                result = await self._execute_for_each(raw_step)
            else:
                result = await self._run_with_retry(resolved_step, step_name)

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            self.steps_status[step_id]["status"] = "success"
            self.steps_status[step_id]["end_time"] = end_time.isoformat()
            self.steps_status[step_id]["duration"] = duration
            self.steps_status[step_id]["result"] = result

            if "save_result_as" in resolved_step:
                self.context["results"][resolved_step["save_result_as"]] = result

            if self.verbose:
                console.print(f"[green]✓ DONE[/green]  {step_name} [dim]({duration:.1f}s)[/dim]")

        except Exception as e:
            end_time = datetime.now()
            self.steps_status[step_id]["status"] = "failed"
            self.steps_status[step_id]["end_time"] = end_time.isoformat()
            self.steps_status[step_id]["duration"] = (end_time - start_time).total_seconds()
            self.steps_status[step_id]["error"] = str(e)

            if self.verbose or not self.quiet:
                console.print(f"[red]✗ FAIL[/red]  {step_name} — {e}")

            if not resolved_step.get("continue_on_error", False):
                raise

    async def _run_with_retry(self, step: dict[str, Any], step_name: str) -> dict[str, Any]:
        """带重试执行单个工具步骤。"""
        retry_count = step.get("retry", 0)

        for attempt in range(retry_count + 1):
            try:
                if attempt > 0:
                    if self.verbose or not self.quiet:
                        console.print(f"[yellow]↻ RETRY[/yellow] {step_name} [{attempt}/{retry_count}]")
                    await asyncio.sleep(5)

                return await self._run_tool(step)
            except Exception:
                if attempt == retry_count:
                    raise

        raise RuntimeError(f"步骤执行失败: {step_name}")

    def _check_dependencies(self, step: dict[str, Any]) -> bool:
        """检查步骤依赖是否满足。"""
        depends_on = step.get("depends_on", [])

        for dep_id in depends_on:
            dep_status = self.steps_status.get(dep_id, {}).get("status")
            if dep_status != "success":
                return False

        return True

    def _check_condition(self, step: dict[str, Any]) -> bool:
        """检查步骤条件是否满足。"""
        if "when" not in step:
            return True

        when = step["when"]
        condition_type = when["type"]
        source = when["source"]

        source_value = get_nested_value(self._build_template_context(), source)

        if source_value is None:
            return False

        if condition_type == "contains":
            value = when["value"]
            return value in source_value if isinstance(source_value, (list, str)) else False

        if condition_type == "contains_any":
            values = when["values"]
            if not isinstance(values, list):
                values = [values]
            if isinstance(source_value, list):
                return any(v in source_value for v in values)
            return False

        if condition_type == "not_contains_any":
            values = when["values"]
            if not isinstance(values, list):
                values = [values]
            if isinstance(source_value, list):
                return not any(v in source_value for v in values)
            return True

        if condition_type == "equals":
            value = when["value"]
            return source_value == value

        if condition_type == "greater_than":
            value = when["value"]
            return source_value > value

        if condition_type == "less_than":
            value = when["value"]
            return source_value < value

        return False

    async def _execute_for_each(self, step: dict[str, Any]) -> list[dict[str, Any]]:
        """执行 for_each 循环。"""
        for_each_value = step.get("for_each")

        if isinstance(for_each_value, list):
            items = for_each_value
        elif isinstance(for_each_value, str):
            source = for_each_value.strip()
            if source.startswith("{{") and source.endswith("}}"):
                source = source[2:-2].strip()
            items = get_nested_value(self._build_template_context(), source)
        else:
            items = for_each_value

        if not isinstance(items, list):
            raise TypeError(f"for_each 的值不是数组: {for_each_value}")

        results: list[dict[str, Any]] = []

        for index, item in enumerate(items):
            item_context = self._build_template_context(item=item)
            item_step = replace_variables(step, item_context)
            item_step = dict(item_step)
            item_step.pop("for_each", None)

            item_name = f"{step.get('name', step.get('id', 'for_each'))}[{index}]"
            try:
                item_result = await self._run_with_retry(item_step, item_name)
            except Exception as e:
                if not item_step.get("continue_on_error", False):
                    raise
                item_result = {"status": "failed", "error": str(e)}

            results.append(item_result)

        return results

    def _get_result_dir(self) -> Optional[Path]:
        """返回 ~/.neosec/result/<ip>/ 目录，按需创建。"""
        target = self.context.get("variables", {}).get("target")
        if not target:
            return None
        result_dir = Path.home() / ".neosec" / "result" / str(target)
        result_dir.mkdir(parents=True, exist_ok=True)
        return result_dir

    def _save_tool_stdout(self, step: dict, tool_name: str, cmd: list[str], output: str) -> None:
        """将工具的原始 stdout 保存为可读文本文件。"""
        result_dir = self._get_result_dir()
        if not result_dir or self.dry_run:
            return
        # Build filename from step id, e.g. port_scan.txt, ffuf_port_80.txt
        step_id = step.get("id", tool_name)
        filename = f"{step_id}.txt"
        out_path = result_dir / filename
        # Write: command header + stdout
        header = "$ " + " ".join(cmd) + "\n" + "-" * 72 + "\n"
        cleaned = self._clean_console_output(output)
        out_path.write_text(header + cleaned + "\n", encoding="utf-8")

    def _print_step_block(self, step_name: str, cmd: list[str], tool_name: str, raw_output: str, result: dict[str, Any]) -> None:
        """以原子块方式打印步骤命令和输出，避免并行交错。"""
        if not self.verbose and not self.dry_run:
            return

        lines: list[str] = []
        lines.append(f"  ╔══ {step_name}")
        lines.append(f"  ║  $ {' '.join(cmd)}")

        if self.verbose and not self.dry_run:
            summary = self._summarize_tool_output(tool_name, raw_output, result)
            if summary:
                for ln in summary.splitlines():
                    lines.append(f"  ║  {ln}")

        lines.append(f"  ╚══")
        console.print("\n".join(lines), markup=False)

    def _print_command(self, cmd: list[str]) -> None:
        """兼容旧调用，不再直接打印（由 _print_step_block 统一输出）。"""
        pass

    def _print_tool_output(self, tool_name: str, raw_output: str, result: dict[str, Any]) -> None:
        """兼容旧调用，不再直接打印（由 _print_step_block 统一输出）。"""
        pass

    def _summarize_tool_output(self, tool_name: str, raw_output: str, result: dict[str, Any]) -> str:
        """按工具生成可读的输出摘要。"""
        if tool_name == "nmap":
            open_ports = result.get("open_ports", [])
            services = result.get("services", [])
            service_names = sorted({str(item.get("service", "unknown")) for item in services})

            ports_text = ",".join(str(p) for p in open_ports) if open_ports else "-"
            if service_names:
                shown = ",".join(service_names[:8])
                if len(service_names) > 8:
                    shown += f",...(+{len(service_names) - 8})"
            else:
                shown = "-"

            lines_out = [f"Open ports : {ports_text}"]
            if services:
                lines_out.append("Services   :")
                for svc in services:
                    ver = (f"{svc.get('product','')} {svc.get('version','')}").strip()
                    ver_str = f"  [{ver}]" if ver else ""
                    lines_out.append(
                        f"  {svc.get('port')}/{svc.get('protocol','tcp')}"
                        f"  {svc.get('service','unknown')}{ver_str}")
            return "\n".join(lines_out)

        if tool_name == "ffuf":
            ffuf_entries = result.get("entries", [])
            if isinstance(ffuf_entries, list) and ffuf_entries:
                return self._summarize_ffuf_entries(result)
            ffuf_summary = self._summarize_ffuf_output(raw_output)
            if ffuf_summary:
                return ffuf_summary

        cleaned = self._clean_console_output(raw_output)
        if not cleaned.strip():
            return "(no stdout)"

        lines = cleaned.splitlines()
        max_lines = 25
        if len(lines) > max_lines:
            return "\n".join(lines[:max_lines]) + f"\n... ({len(lines) - max_lines} more lines)"

        return cleaned

    def _summarize_ffuf_output(self, raw_output: str) -> str:
        """解析 ffuf 输出，提取发现条目摘要。"""
        cleaned = self._clean_console_output(raw_output)
        if not cleaned.strip():
            return "No ffuf output"

        compact = re.sub(r",\s*\n\s*", ", ", cleaned)
        pattern = re.compile(
            r"(?:^|\n)\s*(?P<path>[^\n\[]*?)\s*"
            r"\[Status:\s*(?P<status>\d+),\s*"
            r"Size:\s*(?P<size>\d+),\s*"
            r"Words:\s*(?P<words>\d+),\s*"
            r"Lines:\s*(?P<lines>\d+),\s*"
            r"Duration:\s*(?P<duration>[^\]]+)\]",
            re.MULTILINE,
        )

        items: list[str] = []
        for match in pattern.finditer(compact):
            raw_path = match.group("path").strip()
            path = raw_path if raw_path else "/"
            items.append(
                f"- {path} [status={match.group('status')}, size={match.group('size')}, "
                f"words={match.group('words')}, lines={match.group('lines')}, "
                f"duration={match.group('duration').strip()}]"
            )

        if not items:
            lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
            if not lines:
                return "No ffuf output"
            return "\n".join(lines[:15])

        shown = items[:20]
        if len(items) > 20:
            shown.append(f"... (+{len(items) - 20} more)")

        return "Found entries:\n" + "\n".join(shown)

    def _summarize_ffuf_entries(self, result: dict[str, Any]) -> str:
        """基于 ffuf JSON 结果生成可读摘要。"""
        entries = result.get("entries", [])
        if not isinstance(entries, list) or not entries:
            return "No ffuf findings"

        status_counts: dict[int, int] = {}
        for entry in entries:
            status = entry.get("status")
            if isinstance(status, int):
                status_counts[status] = status_counts.get(status, 0) + 1

        status_text = ", ".join(
            f"{code}:{count}" for code, count in sorted(status_counts.items())
        ) or "-"

        lines = [
            f"Found entries: {len(entries)}",
            f"Status counts: {status_text}",
        ]

        report_md = result.get("report_markdown")
        if report_md:
            lines.append(f"Readable report: {report_md}")

        max_items = 20
        col = f"{"PATH":<38} {"ST":>4}  {"SIZE":>7}  {"MS(ms)":>8}  REDIRECT"
        lines.append(f"  {col}")
        lines.append("  " + "-" * 70)
        for item in entries[:max_items]:
            p = str(item.get("path", "/"))[:38]
            st = str(item.get("status", "-"))
            sz = str(item.get("length", "-"))
            ms = str(item.get("duration_ms", "-"))
            rd = str(item.get("redirectlocation", ""))
            lines.append(f"  {p:<38} {st:>4}  {sz:>7}  {ms:>8}  {rd}")
        if len(entries) > max_items:
            lines.append(f"  ... (+{len(entries) - max_items} more)")
        return "\n".join(lines)

    def _parse_ffuf_result(self, raw_output: str, args: dict[str, Any]) -> dict[str, Any]:
        """解析 ffuf 结果，并生成可读 Markdown 报告。"""
        result: dict[str, Any] = {"status": "success", "raw_output": raw_output}

        output_file = args.get("-o")
        output_format = str(args.get("-of", "")).lower()
        if not output_file or output_format != "json":
            return result

        json_path = Path(str(output_file))
        if not json_path.exists():
            return result

        try:
            data = json.loads(json_path.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            return result

        items = data.get("results", [])
        if not isinstance(items, list):
            items = []

        entries: list[dict[str, Any]] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            input_data = item.get("input", {})
            if not isinstance(input_data, dict):
                input_data = {}
            raw_path = str(input_data.get("FUZZ", ""))
            path = raw_path if raw_path else "/"

            duration_ns = item.get("duration", 0)
            try:
                duration_ms = round(float(duration_ns) / 1_000_000, 2)
            except (TypeError, ValueError):
                duration_ms = 0.0

            entries.append(
                {
                    "path": path,
                    "status": item.get("status"),
                    "length": item.get("length"),
                    "words": item.get("words"),
                    "lines": item.get("lines"),
                    "duration_ms": duration_ms,
                    "url": item.get("url", ""),
                    "host": item.get("host", ""),
                    "content_type": item.get("content-type", ""),
                    "redirectlocation": item.get("redirectlocation", ""),
                }
            )

        result["commandline"] = data.get("commandline", "")
        result["scan_time"] = data.get("time", "")
        result["entries"] = entries

        md_path = self._write_ffuf_markdown(json_path, result)
        if md_path is not None:
            result["report_markdown"] = str(md_path.resolve())

        return result

    def _write_ffuf_markdown(self, json_path: Path, result: dict[str, Any]) -> Optional[Path]:
        """将 ffuf 结果写成 Markdown，便于用户阅读。"""
        entries = result.get("entries", [])
        if not isinstance(entries, list):
            return None

        status_counts: dict[int, int] = {}
        for entry in entries:
            status = entry.get("status")
            if isinstance(status, int):
                status_counts[status] = status_counts.get(status, 0) + 1

        md_lines = [
            "# FFUF 扫描结果",
            "",
            f"- 原始结果文件: `{json_path.name}`",
            f"- 扫描时间: `{result.get('scan_time', '')}`",
            f"- 命中数量: `{len(entries)}`",
        ]

        commandline = result.get("commandline", "")
        if commandline:
            md_lines.append(f"- 命令: `{commandline}`")

        md_lines.extend(["", "## 状态码分布", "", "| 状态码 | 数量 |", "|---|---:|"])
        if status_counts:
            for code, count in sorted(status_counts.items()):
                md_lines.append(f"| {code} | {count} |")
        else:
            md_lines.append("| - | 0 |")

        md_lines.extend(
            [
                "",
                "## 发现条目",
                "",
                "| 路径 | 状态 | 大小 | Words | Lines | 耗时(ms) | 重定向 |",
                "|---|---:|---:|---:|---:|---:|---|",
            ]
        )

        for entry in entries:
            path = str(entry.get("path", "/")).replace("|", "\\|")
            redirect = str(entry.get("redirectlocation", "")).replace("|", "\\|")
            md_lines.append(
                f"| {path} | {entry.get('status', '-')} | {entry.get('length', '-')} | "
                f"{entry.get('words', '-')} | {entry.get('lines', '-')} | "
                f"{entry.get('duration_ms', '-')} | {redirect} |"
            )

        md_path = json_path.with_suffix(".md")
        md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
        return md_path
    def _clean_console_output(self, raw_output: str) -> str:
        """清洗工具输出中的控制字符，便于终端阅读。"""
        text = raw_output.replace("\r\n", "\n").replace("\r", "\n")
        text = self._ansi_escape_re.sub("", text)
        text = text.replace("[2K", "")
        text = text.replace("[0m", "")
        text = self._non_printable_re.sub("", text)

        lines = [line.rstrip() for line in text.split("\n")]
        compact_lines: list[str] = []
        previous_blank = False
        for line in lines:
            is_blank = (line.strip() == "")
            if is_blank and previous_blank:
                continue
            compact_lines.append(line)
            previous_blank = is_blank

        # Strip nmap noisy blocks: SF: fingerprints and fingerprint-strings HTTP bodies
        filtered: list[str] = []
        in_sf_block = False
        in_fp_block = False  # fingerprint-strings HTTP body block
        for ln in compact_lines:
            stripped_ln = ln.strip()
            # Skip SF: service fingerprint lines
            if stripped_ln.startswith("SF-Port") or stripped_ln.startswith("SF:"):
                in_sf_block = True
                continue
            if in_sf_block:
                if stripped_ln.startswith("|") or stripped_ln.startswith("SF"):
                    continue
                in_sf_block = False
            # Skip fingerprint-strings HTTP body (| GetRequest:, | HTTPOptions:, etc.)
            if stripped_ln == "| fingerprint-strings:":
                in_fp_block = True
                continue
            if in_fp_block:
                if stripped_ln.startswith("|"):
                    continue
                in_fp_block = False
            # Skip "N service unrecognized" line
            if "service unrecognized despite" in stripped_ln:
                continue
            filtered.append(ln)
        compact_lines = filtered

        return "\n".join(compact_lines).strip()

    async def _run_tool(self, step: dict[str, Any]) -> dict[str, Any]:
        """运行工具。"""
        tool_name = step["tool"]
        args = step.get("args", {})
        timeout = step.get("timeout", self.config.get("defaults.timeout", 300))

        tool_path = self.config.get_tool_path(tool_name)

        if not self.dry_run and not shutil.which(tool_path):
            raise FileNotFoundError(f"工具未找到: {tool_path}")

        prepared_args = dict(args)
        # For ffuf, remove JSON output flags - we'll save raw stdout instead
        if tool_name == "ffuf":
            prepared_args.pop("-o", None)
            prepared_args.pop("-of", None)
        temp_nmap_xml: Optional[Path] = None
        if tool_name == "nmap" and "-oX" not in prepared_args and "-oA" not in prepared_args:
            with tempfile.NamedTemporaryFile(prefix="neosec_nmap_", suffix=".xml", delete=False) as tmp:
                temp_nmap_xml = Path(tmp.name)
            prepared_args["-oX"] = str(temp_nmap_xml)

        cmd = [tool_path]
        for key, value in prepared_args.items():
            if key.startswith("-"):
                if isinstance(value, bool):
                    if value:
                        cmd.append(key)
                else:
                    cmd.extend([key, str(value)])
            else:
                cmd.append(str(value))

        self._print_command(cmd)

        if self.dry_run:
            return {"status": "dry_run", "command": " ".join(cmd)}

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

            output = stdout.decode(errors="replace")

            if tool_name == "nmap":
                result = self._parse_nmap_result(
                    raw_output=output,
                    args=prepared_args,
                    temp_xml_path=temp_nmap_xml,
                )
            elif tool_name == "ffuf":
                result = self._parse_ffuf_result(output, prepared_args)
            else:
                try:
                    result = json.loads(output)
                except json.JSONDecodeError:
                    result = {"status": "success", "raw_output": output}

            self._save_tool_stdout(step, tool_name, cmd, output)
            self._print_step_block(step.get("name", tool_name), cmd, tool_name, output, result)
            return result

        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            raise TimeoutError(f"工具执行超时 ({timeout}秒)")
        finally:
            if temp_nmap_xml and temp_nmap_xml.exists():
                try:
                    temp_nmap_xml.unlink()
                except OSError:
                    pass

    def _parse_nmap_result(
        self,
        raw_output: str,
        args: dict[str, Any],
        temp_xml_path: Optional[Path],
    ) -> dict[str, Any]:
        """解析 nmap 输出，优先使用 XML 结果并回退到文本解析。"""
        xml_data: Optional[str] = None

        ox_value = args.get("-oX")
        if isinstance(ox_value, str):
            if ox_value == "-":
                xml_data = raw_output
            elif Path(ox_value).exists():
                xml_data = Path(ox_value).read_text(encoding="utf-8", errors="replace")
        elif temp_xml_path and temp_xml_path.exists():
            xml_data = temp_xml_path.read_text(encoding="utf-8", errors="replace")

        if xml_data is None and "-oA" in args:
            oa_prefix = str(args["-oA"])
            oa_xml_path = Path(f"{oa_prefix}.xml")
            if oa_xml_path.exists():
                xml_data = oa_xml_path.read_text(encoding="utf-8", errors="replace")

        parsed = self._parse_nmap_xml(xml_data) if xml_data else None
        if parsed is None:
            parsed = self._parse_nmap_text(raw_output)

        return {
            "status": "success",
            "raw_output": raw_output,
            **parsed,
        }

    def _parse_nmap_xml(self, xml_data: str) -> Optional[dict[str, Any]]:
        """解析 nmap XML 并提取结构化端口与服务信息。"""
        if not xml_data.strip():
            return None

        try:
            root = ET.fromstring(xml_data)
        except ET.ParseError:
            return None

        hosts: list[dict[str, Any]] = []
        services: list[dict[str, Any]] = []
        open_ports: list[int] = []

        for host in root.findall("host"):
            ip_address = "Unknown"
            for addr in host.findall("address"):
                if addr.attrib.get("addrtype") == "ipv4":
                    ip_address = addr.attrib.get("addr", "Unknown")
                    break

            host_ports: list[dict[str, Any]] = []
            for port in host.findall("./ports/port"):
                port_raw = port.attrib.get("portid", "")
                port_num = self._to_int(port_raw)
                protocol = port.attrib.get("protocol", "")

                state_node = port.find("state")
                state = state_node.attrib.get("state", "") if state_node is not None else ""

                service_node = port.find("service")
                service_name = (
                    service_node.attrib.get("name", "unknown")
                    if service_node is not None
                    else "unknown"
                )
                product = service_node.attrib.get("product", "") if service_node is not None else ""
                version = service_node.attrib.get("version", "") if service_node is not None else ""

                port_value: int | str = port_num if port_num is not None else port_raw
                record = {
                    "ip": ip_address,
                    "port": port_value,
                    "protocol": protocol,
                    "state": state,
                    "service": service_name,
                    "product": product,
                    "version": version,
                }
                host_ports.append(record)

                if state == "open":
                    services.append(record)
                    if port_num is not None:
                        open_ports.append(port_num)

            hosts.append({"ip": ip_address, "ports": host_ports})

        return {
            "format": "nmap_xml",
            "hosts": hosts,
            "services": services,
            "open_ports": sorted(set(open_ports)),
        }

    def _parse_nmap_text(self, raw_output: str) -> dict[str, Any]:
        """回退解析 nmap 文本输出，提取开放端口与服务信息。"""
        open_ports: list[int] = []
        services: list[dict[str, Any]] = []

        host_match = re.search(r"Nmap scan report for\s+([^\r\n]+)", raw_output)
        host_name = host_match.group(1).strip() if host_match else "Unknown"

        port_pattern = re.compile(r"^(\d+)\/(tcp|udp)\s+open(?:\s+(\S+))?(?:\s+(.*))?$")
        for line in raw_output.splitlines():
            match = port_pattern.match(line.strip())
            if not match:
                continue

            port = int(match.group(1))
            protocol = match.group(2)
            service = match.group(3) or "unknown"
            version = (match.group(4) or "").strip()

            open_ports.append(port)
            services.append(
                {
                    "ip": host_name,
                    "port": port,
                    "protocol": protocol,
                    "state": "open",
                    "service": service,
                    "product": "",
                    "version": version,
                }
            )

        return {
            "format": "nmap_text",
            "hosts": [{"ip": host_name, "ports": services}],
            "services": services,
            "open_ports": sorted(set(open_ports)),
        }

    @staticmethod
    def _to_int(value: Any) -> Optional[int]:
        """安全转换为整数。"""
        try:
            return int(str(value))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _clean_result_for_output(result: Any) -> Any:
        """递归移除 raw_output / format / hosts 等对人类无用的噪声字段。"""
        if not isinstance(result, dict):
            return result
        drop_keys = {"raw_output", "format", "hosts"}
        cleaned = {}
        for k, v in result.items():
            if k in drop_keys:
                continue
            if isinstance(v, dict):
                cleaned[k] = WorkflowEngine._clean_result_for_output(v)
            elif isinstance(v, list):
                cleaned[k] = [
                    WorkflowEngine._clean_result_for_output(i) if isinstance(i, dict) else i
                    for i in v
                ]
            else:
                cleaned[k] = v
        return cleaned

    def _generate_result(self, template: dict[str, Any]) -> dict[str, Any]:
        """生成执行结果。"""
        steps_result = []
        summary = {"total_steps": 0, "successful": 0, "failed": 0, "skipped": 0}

        for _, status in self.steps_status.items():
            summary["total_steps"] += 1
            if status["status"] == "success":
                summary["successful"] += 1
            elif status["status"] == "failed":
                summary["failed"] += 1
            elif status["status"] == "skipped":
                summary["skipped"] += 1
                continue  # omit skipped steps from output
            # Clean up noisy fields before storing
            clean_status = dict(status)
            if clean_status.get("result"):
                clean_status["result"] = self._clean_result_for_output(clean_status["result"])
            # Drop fields that are always null/uninformative
            for drop in ("error",):
                if clean_status.get(drop) is None:
                    clean_status.pop(drop, None)
            steps_result.append(clean_status)

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
        """保存执行结果到指定路径，同时也保存一份到 ~/.neosec/result/<ip>/。"""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        if not self.quiet:
            console.print(f"[green]✓[/green] 结果已保存: {output_path}")

        # Also save to ~/.neosec/result/<ip>/
        result_dir = self._get_result_dir()
        if result_dir:
            canon = result_dir / "workflow_result.json"
            with open(canon, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            if not self.quiet:
                console.print(f"[green]✓[/green] 结果也保存至: {canon}")
