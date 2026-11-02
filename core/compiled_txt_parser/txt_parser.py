import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from core.data_models.models import ItemRef, Troop, Party

class CompiledTxtParser:
    """Warband 编译后 TXT 文件解析器"""

    @staticmethod
    def parse_item_kinds1(file_path: Path) -> List[ItemRef]:
        """解析 item_kinds1.txt"""
        items = []
        if not file_path.exists():
            return items

        with open(file_path, "r", encoding="latin1", errors="replace") as f:
            lines = [l.strip() for l in f if l.strip()]

        if not lines or not lines[0].startswith("itemsfile version"):
            return items

        # 第一行为 itemsfile version X, 第二行为数量
        idx = 2
        while idx < len(lines):
            line = lines[idx]
            if line.startswith("itm_"):
                parts = line.split()
                item_id = parts[0]
                display_name = parts[1].replace("_", " ") if len(parts) > 1 else item_id
                # 提取价值与重量
                price = 0
                weight = 0.0
                if len(parts) > 5:
                    try:
                        price = int(parts[5])
                    except ValueError:
                        pass
                items.append(ItemRef(
                    id=item_id,
                    display_name=display_name,
                    price=price,
                    weight=weight
                ))
            idx += 1
        return items

    @staticmethod
    def parse_troops_txt(file_path: Path, items_lookup: Optional[Dict[int, str]] = None) -> List[Troop]:
        """解析 troops.txt"""
        troops = []
        if not file_path.exists():
            return troops

        with open(file_path, "r", encoding="latin1", errors="replace") as f:
            lines = [l.strip() for l in f if l.strip()]

        if not lines or not lines[0].startswith("troopsfile version"):
            return troops

        idx = 2
        while idx < len(lines):
            line = lines[idx]
            if line.startswith("trp_"):
                parts = line.split()
                troop_id = parts[0]
                name_sing = parts[1].replace("_", " ") if len(parts) > 1 else troop_id
                name_plur = parts[2].replace("_", " ") if len(parts) > 2 else name_sing
                
                # 接下来几行包含装备信息
                # Warband troops.txt 中，兵种条目下一行通常是装备数组
                equipment = []
                if idx + 1 < len(lines):
                    eq_line = lines[idx + 1]
                    eq_parts = eq_line.split()
                    # 格式为: [item_id_numeric item_modifier ... -1 0]
                    for i in range(0, len(eq_parts) - 1, 2):
                        item_num_str = eq_parts[i]
                        try:
                            item_num = int(item_num_str)
                            if item_num == -1:
                                break
                            item_name = items_lookup.get(item_num, f"itm_{item_num}") if items_lookup else f"itm_{item_num}"
                            equipment.append(item_name)
                        except ValueError:
                            pass

                troops.append(Troop(
                    id=troop_id,
                    name_singular=name_sing,
                    name_plural=name_plur,
                    equipment=equipment,
                    source_kind="compiled_txt"
                ))
            idx += 1
        return troops

    @staticmethod
    def parse_parties_txt(file_path: Path) -> List[Party]:
        """解析 parties.txt"""
        parties = []
        if not file_path.exists():
            return parties

        with open(file_path, "r", encoding="latin1", errors="replace") as f:
            lines = [l.strip() for l in f if l.strip()]

        if not lines or not lines[0].startswith("partiesfile version"):
            return parties

        idx = 2
        while idx < len(lines):
            line = lines[idx]
            parts = line.split()
            # 典型格式: 1 1 0 p_town_1 Town_Name 0 0 0 0 0 0 fac_kingdom_1 ... x y z ...
            if len(parts) >= 12 and any(p.startswith("p_") for p in parts):
                p_idx = next(i for i, p in enumerate(parts) if p.startswith("p_"))
                party_id = parts[p_idx]
                name = parts[p_idx + 1].replace("_", " ") if len(parts) > p_idx + 1 else party_id
                
                # 查找坐标和阵营
                faction = "fac_neutral"
                for p in parts:
                    if p.startswith("fac_"):
                        faction = p
                        break

                # 寻找浮点坐标 (Warband 大地图通常在 10~15 列左右)
                coords = []
                for p in parts[p_idx + 2:]:
                    try:
                        v = float(p)
                        if "." in p:
                            coords.append(v)
                            if len(coords) == 3:
                                break
                    except ValueError:
                        continue

                x = coords[0] if len(coords) > 0 else 0.0
                y = coords[1] if len(coords) > 1 else 0.0
                z = coords[2] if len(coords) > 2 else 0.0

                parties.append(Party(
                    id=party_id,
                    name=name,
                    faction_id=faction,
                    party_type="town" if "town" in party_id else ("castle" if "castle" in party_id else "village"),
                    x=x,
                    y=y,
                    z=z
                ))
            idx += 1
        return parties
