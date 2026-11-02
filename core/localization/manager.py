import csv
import json
from pathlib import Path
from typing import Dict, Optional, Tuple, Any

class LocalizationManager:
    """统一多语言本地化服务，支持内存查询、JSON 持久化以及 Warband 官方 CSV 导入导出"""
    def __init__(self, workspace_file: Optional[Path] = None):
        self.workspace_file = workspace_file
        # 结构: { id: { "en": "...", "zh_CN": "..." } }
        self.table: Dict[str, Dict[str, str]] = {}
        if workspace_file and workspace_file.exists():
            self.load_json(workspace_file)

    def register(self, object_id: str, default_name: str, zh_name: Optional[str] = None, lang: str = "en"):
        if object_id not in self.table:
            self.table[object_id] = {}
        self.table[object_id]["default"] = default_name
        self.table[object_id][lang] = default_name
        if zh_name:
            self.table[object_id]["zh_CN"] = zh_name

    def get(self, object_id: str, default: Optional[str] = None, lang: str = "zh_CN") -> str:
        entry = self.table.get(object_id)
        if not entry:
            return default or object_id
        return entry.get(lang) or entry.get("default") or default or object_id

    def get_display_name(self, object_id: str, raw_name: str, lang: str = "zh_CN", mode: str = "both") -> str:
        """
        根据模式生成 UI 展示文本:
        - "both": "French Line Infantry (法军线列步兵)"
        - "zh": "法军线列步兵"
        - "en": "French Line Infantry"
        """
        trans = self.get(object_id, default=raw_name, lang=lang)
        if mode == "zh":
            return trans
        elif mode == "en":
            return raw_name
        else: # both
            if trans and trans != raw_name:
                return f"{raw_name} ({trans})"
            return raw_name

    def load_warband_csv(self, csv_path: Path, lang: str = "zh_CN"):
        """读取 Warband languages/<lang>/*.csv 文件 (格式: id|translation)"""
        if not csv_path.exists():
            return
        with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("|", 1)
                if len(parts) == 2:
                    k, v = parts[0].strip(), parts[1].strip()
                    if k not in self.table:
                        self.table[k] = {}
                    self.table[k][lang] = v

    def export_warband_csv(self, category_prefix: str, output_csv: Path, lang: str = "zh_CN"):
        """将指定前缀的对象导出为 Warband 识别的 CSV 文件"""
        output_csv.parent.mkdir(parents=True, exist_ok=True)
        lines = []
        for obj_id, mapping in sorted(self.table.items()):
            if obj_id.startswith(category_prefix) and lang in mapping:
                lines.append(f"{obj_id}|{mapping[lang]}\n")
        with open(output_csv, "w", encoding="utf-8") as f:
            f.writelines(lines)

    def load_json(self, path: Path):
        with open(path, "r", encoding="utf-8") as f:
            self.table = json.load(f)

    def save_json(self, path: Optional[Path] = None):
        target = path or self.workspace_file
        if not target:
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            json.dump(self.table, f, indent=2, ensure_ascii=False)
