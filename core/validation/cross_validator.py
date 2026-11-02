from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Any

@dataclass
class ValidationIssue:
    severity: str # "ERROR", "WARNING", "INFO"
    category: str # "ITEM_REF", "FACTION_REF", "COORDINATE", "ATTACHMENT", "TRANSLATION"
    target_id: str
    message: str
    suggestion: Optional[str] = None

@dataclass
class ValidationReport:
    issues: List[ValidationIssue] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "ERROR")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "WARNING")

    def format_summary(self) -> str:
        lines = [f"校验完成: {self.error_count} 错误, {self.warning_count} 警告, {len(self.issues) - self.error_count - self.warning_count} 提示"]
        for issue in self.issues:
            icon = "❌" if issue.severity == "ERROR" else ("⚠️" if issue.severity == "WARNING" else "ℹ️")
            lines.append(f"  {icon} [{issue.category}] {issue.target_id}: {issue.message}")
            if issue.suggestion:
                lines.append(f"      💡 建议: {issue.suggestion}")
        return "\n".join(lines)


class CrossReferenceValidator:
    """跨模块关系校验引擎"""
    def __init__(self, 
                 known_items: Optional[Set[str]] = None,
                 known_troops: Optional[Set[str]] = None,
                 known_factions: Optional[Set[str]] = None,
                 known_parties: Optional[Set[str]] = None):
        self.items: Set[str] = known_items or set()
        self.troops: Set[str] = known_troops or set()
        self.factions: Set[str] = known_factions or set()
        self.parties: Set[str] = known_parties or set()

    def validate_troop(self, troop_id: str, equipment: List[str], flags: Optional[str] = None) -> List[ValidationIssue]:
        issues = []
        has_gun = False
        has_bullet = False
        has_bow = False
        has_arrow = False
        has_horse = False

        for item in equipment:
            # 1. 引用存在性检查
            if self.items and item not in self.items:
                issues.append(ValidationIssue(
                    severity="ERROR",
                    category="ITEM_REF",
                    target_id=troop_id,
                    message=f"装备了不存在的物品 '{item}'",
                    suggestion=f"检查拼写或先在 module_items.py / item_kinds1.txt 中定义 '{item}'"
                ))

            # 2. 简易装备搭配语义检查
            ilow = item.lower()
            if "musket" in ilow or "rifle" in ilow or "pistol" in ilow or "arquebus" in ilow:
                has_gun = True
            if "cartridge" in ilow or "bullet" in ilow or "ball" in ilow:
                has_bullet = True
            if "bow" in ilow and "cross" not in ilow:
                has_bow = True
            if "arrow" in ilow:
                has_arrow = True
            if "horse" in ilow or "courser" in ilow or "charger" in ilow or "steed" in ilow:
                has_horse = True

        if has_gun and not has_bullet:
            issues.append(ValidationIssue(
                severity="WARNING",
                category="EQUIPMENT_LOGIC",
                target_id=troop_id,
                message="装备了枪械但未配备弹药/纸包弹 (cartridges)",
                suggestion="为该兵种装备槽添加对应弹药"
            ))

        if has_bow and not has_arrow:
            issues.append(ValidationIssue(
                severity="WARNING",
                category="EQUIPMENT_LOGIC",
                target_id=troop_id,
                message="装备了弓箭但未配备箭矢 (arrows)",
                suggestion="为该兵种装备槽添加对应箭袋"
            ))

        return issues

    def validate_party_coordinates(self, party_id: str, x: float, y: float, existing_coords: Dict[str, tuple]) -> List[ValidationIssue]:
        issues = []
        # 1. 虚空坐标检查
        if abs(x - 175.0) < 0.01 and abs(y - 175.0) < 0.01:
            issues.append(ValidationIssue(
                severity="WARNING",
                category="COORDINATE",
                target_id=party_id,
                message="据点坐标处于 (175, 175) 疑似测试虚空点",
                suggestion="在大地图编辑器中拖拽该据点至实际地理位置"
            ))

        # 2. 重叠坐标检查
        for other_id, (ox, oy) in existing_coords.items():
            if other_id != party_id:
                dist_sq = (x - ox) ** 2 + (y - oy) ** 2
                if dist_sq < 0.0001: # 几乎完全重合
                    issues.append(ValidationIssue(
                        severity="ERROR",
                        category="COORDINATE",
                        target_id=party_id,
                        message=f"据点坐标与 '{other_id}' 完全重叠 (x={x:.2f}, y={y:.2f})",
                        suggestion="分开摆放据点，避免游戏内大地图点击判定冲突"
                    ))
                    break
        return issues

    def validate_party_faction(self, party_id: str, faction_id: str) -> List[ValidationIssue]:
        issues = []
        if self.factions and faction_id not in self.factions:
            issues.append(ValidationIssue(
                severity="ERROR",
                category="FACTION_REF",
                target_id=party_id,
                message=f"据点指定了不存在的阵营 '{faction_id}'"
            ))
        return issues
