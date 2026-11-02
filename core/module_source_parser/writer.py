import ast
from pathlib import Path
from typing import List, Tuple
from core.data_models.models import Troop
from core.backup_diff.transaction import Transaction

def patch_troop_equipment(source_code: str, modified_troops: List[Troop]) -> str:
    """
    通过 AST 坐标原位替换兵种装备列表。
    从后往前替换，防止上层节点行列失效。
    """
    valid_modifications = [
        t for t in modified_troops if t.equipment_ast_coords is not None
    ]
    
    valid_modifications.sort(
        key=lambda t: (t.equipment_ast_coords.lineno, t.equipment_ast_coords.col_offset), 
        reverse=True
    )
    
    lines = source_code.splitlines(keepends=True)
    
    for troop in valid_modifications:
        coords = troop.equipment_ast_coords
        start_line_idx = coords.lineno - 1
        end_line_idx = coords.end_lineno - 1
        start_col = coords.col_offset
        end_col = coords.end_col_offset
        
        new_equipment_str = "[" + ", ".join(troop.equipment) + "]"
        
        if start_line_idx == end_line_idx:
            original_line = lines[start_line_idx]
            lines[start_line_idx] = original_line[:start_col] + new_equipment_str + original_line[end_col:]
        else:
            first_line_prefix = lines[start_line_idx][:start_col]
            last_line_suffix = lines[end_line_idx][end_col:]
            lines[start_line_idx] = first_line_prefix + new_equipment_str + last_line_suffix
            for i in range(start_line_idx + 1, end_line_idx + 1):
                lines[i] = ""
                
    return "".join(lines)

def save_troops_transaction(file_path: Path, modified_troops: List[Troop], backup_dir: Path, description: str = "更新兵种装备", original_mtime: float = None) -> Transaction:
    """
    生成一个写回事务，可供调用者进行 diff 预览或直接 commit
    """
    with open(file_path, "r", encoding="utf-8") as f:
        original = f.read()
    
    patched = patch_troop_equipment(original, modified_troops)
    
    def ast_verifier(content: str) -> bool:
        ast.parse(content)
        return True

    tx = Transaction(
        target_file=file_path,
        new_content=patched,
        description=description,
        backup_dir=backup_dir,
        original_mtime=original_mtime
    )
    tx.verify(ast_verifier)
    return tx
