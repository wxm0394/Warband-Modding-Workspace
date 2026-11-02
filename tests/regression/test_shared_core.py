import unittest
import tempfile
import time
from pathlib import Path
from core import (
    ProjectContext,
    ProjectConfig,
    ItemRef,
    Troop,
    Transaction,
    ConcurrencyConflictError,
    LocalizationManager,
    CrossReferenceValidator,
    BuildRunner
)
from core.module_source_parser.writer import patch_troop_equipment
from core.module_source_parser.parser import parse_items, parse_troops

DUMMY_TROOPS_CODE = """
from header_troops import *

troops = [
  ["player","Player","Player",tf_hero,no_faction,[],0,0,0,0],
  ["french_fusilier","French Fusilier","French Fusiliers",tf_guarantee_all,fac_kingdom_1,
   [itm_french_musket, itm_cartridges],
   0,0,0,0]
]
"""

class TestSharedCore(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.backup_dir = self.root / ".workspace/backups"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_transaction_diff_and_atomic_commit(self):
        target_file = self.root / "module_troops.py"
        target_file.write_text(DUMMY_TROOPS_CODE, encoding="utf-8")
        original_mtime = target_file.stat().st_mtime

        # 修改内容
        new_content = DUMMY_TROOPS_CODE.replace("itm_cartridges", "itm_cartridges_heavy")

        tx = Transaction(
            target_file=target_file,
            new_content=new_content,
            description="测试更换重装纸包弹",
            backup_dir=self.backup_dir,
            original_mtime=original_mtime
        )

        diff = tx.get_diff()
        self.assertIn("-   [itm_french_musket, itm_cartridges],", diff)
        self.assertIn("+   [itm_french_musket, itm_cartridges_heavy],", diff)

        # 提交事务
        committed_path = tx.commit()
        self.assertEqual(committed_path, target_file)
        self.assertTrue(tx.committed)
        self.assertIn("itm_cartridges_heavy", target_file.read_text(encoding="utf-8"))
        
        # 验证备份已创建
        backups = list(self.backup_dir.glob("*.bak"))
        self.assertEqual(len(backups), 1)

    def test_transaction_concurrency_protection(self):
        """测试防止跨工具覆盖：若外部修改导致 mtime 变动，应拒绝保存"""
        target_file = self.root / "parties.txt"
        target_file.write_text("initial content", encoding="utf-8")
        original_mtime = target_file.stat().st_mtime

        # 模拟外部工具修改了该文件
        time.sleep(0.01)
        target_file.write_text("content modified by map editor", encoding="utf-8")

        # 此时装备工具试图用旧缓存覆盖
        tx = Transaction(
            target_file=target_file,
            new_content="content from troop editor using stale cache",
            description="旧缓存写入",
            backup_dir=self.backup_dir,
            original_mtime=original_mtime
        )

        with self.assertRaises(ConcurrencyConflictError):
            tx.commit()

    def test_localization_manager(self):
        loc = LocalizationManager()
        loc.register("trp_french_line_infantry", "French Line Infantry", "法军线列步兵")
        loc.register("p_town_1", "Lille", "里尔")

        # 测试多种显示模式
        display_both = loc.get_display_name("trp_french_line_infantry", "French Line Infantry", mode="both")
        self.assertEqual(display_both, "French Line Infantry (法军线列步兵)")

        display_zh = loc.get_display_name("trp_french_line_infantry", "French Line Infantry", mode="zh")
        self.assertEqual(display_zh, "法军线列步兵")

        display_en = loc.get_display_name("trp_french_line_infantry", "French Line Infantry", mode="en")
        self.assertEqual(display_en, "French Line Infantry")

        # 测试导出与导入 Warband CSV (id|trans)
        csv_file = self.root / "languages/cns/troops.csv"
        loc.export_warband_csv("trp_", csv_file, lang="zh_CN")
        self.assertTrue(csv_file.exists())
        content = csv_file.read_text(encoding="utf-8")
        self.assertIn("trp_french_line_infantry|法军线列步兵", content)

    def test_cross_reference_validator(self):
        validator = CrossReferenceValidator(
            known_items={"itm_french_musket", "itm_cartridges"},
            known_factions={"fac_kingdom_1"},
            known_parties={"p_town_1"}
        )

        # 1. 枪兵缺弹药警告
        issues = validator.validate_troop("trp_french_fusilier", ["itm_french_musket"])
        self.assertTrue(any(i.category == "EQUIPMENT_LOGIC" for i in issues))

        # 2. 装备不存在错误
        issues = validator.validate_troop("trp_invalid", ["itm_plasma_rifle"])
        self.assertTrue(any(i.category == "ITEM_REF" and i.severity == "ERROR" for i in issues))

        # 3. 坐标 (175, 175) 虚空与重合检查
        coord_issues = validator.validate_party_coordinates("p_test", 175.0, 175.0, {})
        self.assertTrue(any(i.category == "COORDINATE" and "175" in i.message for i in coord_issues))

        overlap_issues = validator.validate_party_coordinates("p_test2", 10.0, 20.0, {"p_town_1": (10.0, 20.0)})
        self.assertTrue(any(i.category == "COORDINATE" and i.severity == "ERROR" for i in overlap_issues))

    def test_project_context_detection(self):
        mod_dir = self.root / "MockMod"
        mod_dir.mkdir()
        (mod_dir / "troops.txt").write_text("troopsfile version 1", encoding="utf-8")
        (mod_dir / "parties.txt").write_text("partiesfile version 1", encoding="utf-8")
        (mod_dir / "item_kinds1.txt").write_text("itemsfile version 1", encoding="utf-8")
        (mod_dir / "module.ini").write_text("module_name = MockMod", encoding="utf-8")

        ctx = ProjectContext.auto_detect(mod_dir)
        self.assertTrue(ctx.report.is_txt_ready)
        self.assertFalse(ctx.report.is_source_ready)
        self.assertEqual(ctx.config.project_name, "MockMod")

if __name__ == "__main__":
    unittest.main()
