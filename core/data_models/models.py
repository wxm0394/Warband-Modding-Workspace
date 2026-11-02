import dataclasses
from typing import List, Optional, Tuple, Any, Dict

@dataclasses.dataclass
class ItemRef:
    """物品统一模型"""
    id: str  # e.g., "itm_french_musket"
    display_name: str
    numeric_id: Optional[int] = None
    item_type: Optional[str] = None
    mesh_name: Optional[str] = None
    price: int = 0
    weight: float = 0.0

@dataclasses.dataclass
class AstCoordinates:
    """AST 节点精确源码坐标，用于原子字符串替换"""
    lineno: int
    col_offset: int
    end_lineno: int
    end_col_offset: int

@dataclasses.dataclass
class Troop:
    """兵种/领主/NPC 统一模型"""
    id: str  # e.g., "trp_french_line_infantry"
    name_singular: str
    name_plural: str
    equipment: List[str] # ['itm_french_musket', 'itm_cartridges']
    equipment_ast_coords: Optional[AstCoordinates] = None
    flags: Optional[str] = None
    faction_id: Optional[str] = None
    upgrade_troop_1: Optional[str] = None
    upgrade_troop_2: Optional[str] = None
    source_kind: str = "module_source" # "module_source" or "compiled_txt"

@dataclasses.dataclass
class Party:
    """地图据点与部队统一模型"""
    id: str # e.g., "p_town_1"
    name: str # e.g., "Lille"
    faction_id: str # e.g., "fac_kingdom_1"
    party_type: str # "town", "castle", "village", "spawn_point", etc.
    x: float
    y: float
    z: float = 0.0
    menu_id: Optional[str] = None
    party_template: Optional[str] = None
    attached_to: Optional[str] = None # 村庄归属的主城
    icon_id: Optional[str] = None
    garrison: List[Tuple[str, int]] = dataclasses.field(default_factory=list) # [(trp_id, count)]

@dataclasses.dataclass
class Faction:
    """阵营/势力模型"""
    id: str # e.g., "fac_kingdom_1"
    name: str # e.g., "Kingdom of France"
    color_rgb: Tuple[int, int, int] = (255, 255, 255)
    flag_texture: Optional[str] = None
