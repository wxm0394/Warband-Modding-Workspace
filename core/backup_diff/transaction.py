import os
import difflib
import datetime
import json
from pathlib import Path
from typing import Callable, Optional, List, Dict, Any

class ConcurrencyConflictError(Exception):
    """当文件在加载后被外部或其他子工具修改时抛出，防止旧缓存覆盖新变更"""
    pass

class ValidationError(Exception):
    """写入前语法或语义验证失败时抛出"""
    pass

class Transaction:
    def __init__(self, target_file: Path, new_content: str, description: str, backup_dir: Path, original_mtime: Optional[float] = None):
        self.target_file = target_file.resolve()
        self.new_content = new_content
        self.description = description
        self.backup_dir = backup_dir.resolve()
        self.original_mtime = original_mtime
        self.original_content = ""
        self.committed = False
        self.backup_created: Optional[Path] = None

        if self.target_file.exists():
            with open(self.target_file, "r", encoding="utf-8", errors="replace") as f:
                self.original_content = f.read()

    def get_diff(self) -> str:
        orig_lines = self.original_content.splitlines(keepends=True)
        new_lines = self.new_content.splitlines(keepends=True)
        diff = difflib.unified_diff(
            orig_lines, new_lines,
            fromfile=f"a/{self.target_file.name}",
            tofile=f"b/{self.target_file.name}",
            lineterm=""
        )
        return "".join(diff)

    def verify(self, verifier_fn: Optional[Callable[[str], bool]] = None) -> bool:
        if verifier_fn:
            try:
                ok = verifier_fn(self.new_content)
                if not ok:
                    raise ValidationError("自定义校验函数返回失败")
            except Exception as e:
                raise ValidationError(f"验证失败，拒绝写入: {e}")
        return True

    def commit(self, verifier_fn: Optional[Callable[[str], bool]] = None) -> Path:
        """执行事务：校验 -> 冲突检测 -> 备份 -> 原子落盘 -> 日志"""
        # 1. 语法/完整性验证
        self.verify(verifier_fn)

        # 2. 并发冲突检测
        if self.target_file.exists() and self.original_mtime is not None:
            current_mtime = self.target_file.stat().st_mtime
            if abs(current_mtime - self.original_mtime) > 0.001:
                raise ConcurrencyConflictError(
                    f"文件 {self.target_file.name} 自上次加载后已被外部或其它工作台修改！\n"
                    f"原时间戳: {self.original_mtime}, 当前时间戳: {current_mtime}。\n"
                    f"为防覆盖丢失，已阻止本次保存，请重新加载后再试。"
                )

        # 3. 建立备份
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = self.backup_dir / f"{self.target_file.name}.{timestamp}.bak"
        if self.target_file.exists():
            with open(backup_file, "w", encoding="utf-8") as bf:
                bf.write(self.original_content)
            self.backup_created = backup_file

        # 4. 写入临时文件并执行 POSIX 原子替换 (os.replace)
        temp_file = self.target_file.with_name(f".{self.target_file.name}.{timestamp}.tmp")
        try:
            with open(temp_file, "w", encoding="utf-8") as tf:
                tf.write(self.new_content)
            os.replace(temp_file, self.target_file)
            self.committed = True
        except Exception as e:
            if temp_file.exists():
                temp_file.unlink()
            raise IOError(f"原子写入失败: {e}")

        # 5. 记录 Changelog
        self._log_change()
        return self.target_file

    def _log_change(self):
        log_file = self.backup_dir / "changelog.jsonl"
        log_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "file": str(self.target_file),
            "description": self.description,
            "backup": str(self.backup_created) if self.backup_created else None
        }
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

    @classmethod
    def rollback_file(cls, backup_path: Path, target_path: Path):
        """从备份文件回滚目标文件"""
        if not backup_path.exists():
            raise FileNotFoundError(f"备份文件不存在: {backup_path}")
        with open(backup_path, "r", encoding="utf-8") as bf:
            content = bf.read()
        with open(target_path, "w", encoding="utf-8") as tf:
            tf.write(content)
