"""配置管理模块"""
import os
from pathlib import Path
from typing import Any, Optional
import yaml
from rich.console import Console

console = Console()


class Config:
    """配置管理类"""

    DEFAULT_CONFIG = {
        "tools": {
            "nmap": "nmap",
            "ffuf": "ffuf",
            "subfinder": "subfinder",
            "nuclei": "nuclei",
            "dnsenum": "dnsenum",
            "whois": "whois",
        },
        "defaults": {
            "wordlist": "/usr/share/wordlists/dirb/common.txt",
            "timeout": 300,
            "retry": 1,
        },
        "output": {
            "default_path": "./",
            "default_filename": "workflow_result.json",
            "log_path": "~/.neosec/log/",
        },
        "verbose": False,
        "quiet": False,
    }

    def __init__(self, config_path: Optional[Path] = None):
        """初始化配置

        Args:
            config_path: 自定义配置文件路径，如果为 None 则使用默认路径
        """
        self.neosec_dir = Path.home() / ".neosec"
        self.config_path = config_path or (self.neosec_dir / "config.yaml")
        self.templates_dir = self.neosec_dir / "templates"
        self.log_dir = self.neosec_dir / "log"
        self.history_dir = self.neosec_dir / "history"

        self.config_data: dict[str, Any] = {}

    def init_directories(self) -> None:
        """初始化目录结构"""
        self.neosec_dir.mkdir(parents=True, exist_ok=True)
        self.templates_dir.mkdir(exist_ok=True)
        self.log_dir.mkdir(exist_ok=True)
        self.history_dir.mkdir(exist_ok=True)

    def create_default_config(self) -> None:
        """创建默认配置文件"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.config_path, "w", encoding="utf-8") as f:
            yaml.dump(self.DEFAULT_CONFIG, f, default_flow_style=False, allow_unicode=True)

        console.print(f"[green]✓[/green] 配置文件已创建: {self.config_path}")

    def load(self) -> dict[str, Any]:
        """加载配置文件

        Returns:
            配置字典
        """
        if not self.config_path.exists():
            console.print(f"[yellow]警告:[/yellow] 配置文件不存在: {self.config_path}")
            console.print("[yellow]使用默认配置，建议运行 'neosec init' 创建配置文件[/yellow]")
            self.config_data = self.DEFAULT_CONFIG.copy()
            return self.config_data

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                self.config_data = yaml.safe_load(f) or {}

            # 合并默认配置（处理缺失的键）
            self.config_data = self._merge_config(self.DEFAULT_CONFIG, self.config_data)

            return self.config_data
        except Exception as e:
            console.print(f"[red]错误:[/red] 加载配置文件失败: {e}")
            console.print("[yellow]使用默认配置[/yellow]")
            self.config_data = self.DEFAULT_CONFIG.copy()
            return self.config_data

    def _merge_config(self, default: dict, user: dict) -> dict:
        """合并默认配置和用户配置

        Args:
            default: ���认配置
            user: 用户配置

        Returns:
            合并后的配置
        """
        result = default.copy()
        for key, value in user.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value
        return result

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值（支持点号访问嵌套字段）

        Args:
            key: 配置键，支持 "tools.nmap" 格式
            default: 默认值

        Returns:
            配置值
        """
        keys = key.split(".")
        value = self.config_data

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default

        return value

    def get_tool_path(self, tool_name: str) -> Optional[str]:
        """获取工具路径

        Args:
            tool_name: 工具名称

        Returns:
            工具路径，如果未配置则返回工具名称本身
        """
        return self.get(f"tools.{tool_name}", tool_name)

    def expand_path(self, path: str) -> Path:
        """展开路径（处理 ~ 和相对路径）

        Args:
            path: 路径字符串

        Returns:
            展开后的 Path 对象
        """
        return Path(os.path.expanduser(path)).expanduser().resolve()
