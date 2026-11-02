import os
import json
import subprocess
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List

COMMON_WARBAND_PATHS = [
    Path.home() / "GOG Games/Mount Blade Warband/game",
    Path.home() / ".steam/steam/steamapps/common/MountBlade Warband",
    Path.home() / ".local/share/Steam/steamapps/common/MountBlade Warband",
    Path.home() / ".wine/drive_c/Program Files (x86)/Mount&Blade Warband",
]

@dataclass
class ProjectConfig:
    project_name: str = "Warband Project"
    warband_root: Optional[str] = None
    module_dir: str = ""
    module_system_dir: Optional[str] = None
    source_mode: bool = False
    module_ini: str = "module.ini"
    build_command: str = "python3 build_module.py"
    launch_command: str = ""
    cartographer_command: str = ""
    openbrf_command: str = ""
    backup_dir: str = ".workspace/backups"

@dataclass
class DetectionReport:
    has_module_troops_py: bool = False
    has_module_items_py: bool = False
    has_module_parties_py: bool = False
    has_troops_txt: bool = False
    has_parties_txt: bool = False
    has_item_kinds1_txt: bool = False
    has_map_txt: bool = False
    has_module_ini: bool = False
    is_git: bool = False
    git_branch: str = ""
    git_dirty: bool = False

    @property
    def is_source_ready(self) -> bool:
        return self.has_module_troops_py and self.has_module_items_py

    @property
    def is_txt_ready(self) -> bool:
        return self.has_troops_txt and self.has_parties_txt and self.has_item_kinds1_txt

    def summary(self) -> str:
        mode = "Module System (源码模式)" if self.is_source_ready else ("TXT 编译兼容模式" if self.is_txt_ready else "数据不全")
        lines = [
            f"检测状态: {mode}",
            f"  - module_troops.py : {'✓' if self.has_module_troops_py else '✗'}",
            f"  - module_items.py  : {'✓' if self.has_module_items_py else '✗'}",
            f"  - module_parties.py: {'✓' if self.has_module_parties_py else '✗'}",
            f"  - troops.txt       : {'✓' if self.has_troops_txt else '✗'}",
            f"  - parties.txt      : {'✓' if self.has_parties_txt else '✗'}",
            f"  - item_kinds1.txt  : {'✓' if self.has_item_kinds1_txt else '✗'}",
            f"  - map.txt          : {'✓' if self.has_map_txt else '✗'}",
            f"  - module.ini       : {'✓' if self.has_module_ini else '✗'}",
            f"  - Git 仓库         : {'✓ (' + self.git_branch + (' dirty' if self.git_dirty else ' clean') + ')' if self.is_git else '✗'}"
        ]
        return "\n".join(lines)


class ProjectContext:
    def __init__(self, config: ProjectConfig):
        self.config = config
        self.module_path = Path(config.module_dir).resolve() if config.module_dir else Path.cwd()
        self.source_path = Path(config.module_system_dir).resolve() if config.module_system_dir else self.module_path
        self.backup_path = self.module_path / config.backup_dir
        self.report = self.detect_environment()

    @classmethod
    def auto_detect(cls, module_dir: str | Path, warband_root: Optional[str | Path] = None, source_dir: Optional[str | Path] = None) -> "ProjectContext":
        m_dir = Path(module_dir).resolve()
        
        # 查找 Warband 根目录
        wb_root = None
        if warband_root and Path(warband_root).exists():
            wb_root = str(Path(warband_root).resolve())
        else:
            # 尝试向上探测 Modules/ 的上一级
            if m_dir.parent.name.lower() == "modules":
                wb_root = str(m_dir.parent.parent)
            else:
                for candidate in COMMON_WARBAND_PATHS:
                    if candidate.exists():
                        wb_root = str(candidate)
                        break

        s_dir = str(Path(source_dir).resolve()) if source_dir else None
        
        # 默认启动指令
        launch_cmd = ""
        if wb_root:
            sh_script = Path(wb_root) / "mb_warband.sh"
            game_sh = Path(wb_root) / "game" / "mb_warband.sh"
            if sh_script.exists():
                launch_cmd = f"bash \"{sh_script}\""
            elif game_sh.exists():
                launch_cmd = f"bash \"{game_sh}\""
            else:
                launch_cmd = f"wine \"{Path(wb_root)/'mb_warband.exe'}\" -module \"{m_dir.name}\""

        config = ProjectConfig(
            project_name=m_dir.name,
            warband_root=wb_root,
            module_dir=str(m_dir),
            module_system_dir=s_dir,
            launch_command=launch_cmd,
            backup_dir=".workspace/backups"
        )
        ctx = cls(config)
        ctx.config.source_mode = ctx.report.is_source_ready
        return ctx

    def detect_environment(self) -> DetectionReport:
        r = DetectionReport()
        m = self.module_path
        s = self.source_path

        r.has_module_troops_py = (s / "module_troops.py").exists() or (m / "module_troops.py").exists()
        r.has_module_items_py = (s / "module_items.py").exists() or (m / "module_items.py").exists()
        r.has_module_parties_py = (s / "module_parties.py").exists() or (m / "module_parties.py").exists()

        r.has_troops_txt = (m / "troops.txt").exists()
        r.has_parties_txt = (m / "parties.txt").exists()
        r.has_item_kinds1_txt = (m / "item_kinds1.txt").exists()
        r.has_map_txt = (m / "map.txt").exists()
        r.has_module_ini = (m / self.config.module_ini).exists()

        # Git 探测
        git_dir = m / ".git"
        if not git_dir.exists() and s != m:
            git_dir = s / ".git"
        if not git_dir.exists():
            git_dir = Path.cwd() / ".git"

        if git_dir.exists():
            r.is_git = True
            try:
                branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=git_dir.parent, text=True, stderr=subprocess.DEVNULL).strip()
                r.git_branch = branch
                status = subprocess.check_output(["git", "status", "--porcelain"], cwd=git_dir.parent, text=True, stderr=subprocess.DEVNULL).strip()
                r.git_dirty = len(status) > 0
            except Exception:
                r.git_branch = "unknown"

        return r

    def get_source_file(self, filename: str) -> Optional[Path]:
        """优先从源码目录寻找，其次从 module 目录寻找"""
        if self.source_path and (self.source_path / filename).exists():
            return self.source_path / filename
        if (self.module_path / filename).exists():
            return self.module_path / filename
        return None

    def get_compiled_file(self, filename: str) -> Optional[Path]:
        p = self.module_path / filename
        return p if p.exists() else None

    def save(self, filepath: Optional[Path] = None):
        target = filepath or (self.module_path / ".workspace_config.json")
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            json.dump(asdict(self.config), f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, filepath: Path) -> "ProjectContext":
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(ProjectConfig(**data))
