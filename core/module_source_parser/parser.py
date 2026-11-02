import ast
from typing import List, Dict, Optional
from core.data_models.models import ItemRef, Troop, AstCoordinates

def parse_items(source_code: str) -> List[ItemRef]:
    """
    解析 module_items.py，提取物品列表。
    """
    tree = ast.parse(source_code)
    parsed_items = []
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == 'items':
                    if isinstance(node.value, ast.List):
                        for el in node.value.elts:
                            if isinstance(el, ast.Tuple) and len(el.elts) >= 2:
                                item_id_node = el.elts[0]
                                item_name_node = el.elts[1]
                                
                                if isinstance(item_id_node, ast.Constant) and isinstance(item_name_node, ast.Constant):
                                    item_id = item_id_node.value
                                    if not item_id.startswith("itm_"):
                                        item_id = f"itm_{item_id}"
                                        
                                    parsed_items.append(ItemRef(
                                        id=item_id,
                                        display_name=item_name_node.value
                                    ))
    return parsed_items

def parse_troops(source_code: str) -> List[Troop]:
    """
    解析 module_troops.py，提取兵种及精确 AST 坐标。
    """
    tree = ast.parse(source_code)
    parsed_troops = []
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == 'troops':
                    if isinstance(node.value, ast.List):
                        for el in node.value.elts:
                            if isinstance(el, (ast.Tuple, ast.List)) and len(el.elts) >= 7:
                                troop_id_node = el.elts[0]
                                name_node = el.elts[1]
                                plural_name_node = el.elts[2]
                                equipment_node = el.elts[5]
                                
                                troop_id = troop_id_node.value if isinstance(troop_id_node, ast.Constant) else ""
                                name = name_node.value if isinstance(name_node, ast.Constant) else ""
                                plural_name = plural_name_node.value if isinstance(plural_name_node, ast.Constant) else ""
                                
                                if troop_id and not troop_id.startswith("trp_"):
                                    troop_id = f"trp_{troop_id}"
                                    
                                equipment = []
                                coords = None
                                
                                if isinstance(equipment_node, ast.List):
                                    coords = AstCoordinates(
                                        lineno=equipment_node.lineno,
                                        col_offset=equipment_node.col_offset,
                                        end_lineno=getattr(equipment_node, 'end_lineno', equipment_node.lineno),
                                        end_col_offset=getattr(equipment_node, 'end_col_offset', equipment_node.col_offset)
                                    )
                                    
                                    for item_node in equipment_node.elts:
                                        if isinstance(item_node, ast.Name):
                                            equipment.append(item_node.id)
                                        elif isinstance(item_node, ast.Constant):
                                            equipment.append(str(item_node.value))
                                
                                parsed_troops.append(Troop(
                                    id=troop_id,
                                    name_singular=name,
                                    name_plural=plural_name,
                                    equipment=equipment,
                                    equipment_ast_coords=coords
                                ))
    return parsed_troops
