import unittest
import math
from map_editor import (
    categorize_party, CATEGORY_META, create_category_icon, PartyItem, MapEditor
)
from PyQt5.QtWidgets import QApplication
import sys

app = QApplication.instance() or QApplication(sys.argv)

class TestMapPartyIcons(unittest.TestCase):
    def test_categorization(self):
        # 1. 桥梁
        self.assertEqual(categorize_party('p_bridge_1', '{!}1'), 'bridge')
        self.assertEqual(categorize_party('p_bridge_ford', 'River_Crossing'), 'bridge')
        
        # 2. 城镇
        self.assertEqual(categorize_party('p_town_1', 'Sargoth'), 'town')
        self.assertEqual(categorize_party('p_hx_city_1', "Chang'an"), 'town')
        
        # 3. 城堡
        self.assertEqual(categorize_party('p_castle_1', 'Culmarr_Castle'), 'castle')
        self.assertEqual(categorize_party('p_hx_castle_1', 'Hangu_Pass'), 'castle')
        
        # 4. 村庄
        self.assertEqual(categorize_party('p_village_1', 'Yruma'), 'village')
        self.assertEqual(categorize_party('p_hx_village_1', 'Village_1'), 'village')
        
        # 5. 训练营
        self.assertEqual(categorize_party('p_training_ground_1', 'Mercenary_camp'), 'training_camp')
        self.assertEqual(categorize_party('p_training_ground', 'Training_Ground'), 'training_camp')
        
        # 6. 原版遗留/彩蛋/特殊独立场景
        self.assertEqual(categorize_party('p_zendar', 'Zendar'), 'special_scene')
        self.assertEqual(categorize_party('p_salt_mine', 'Salt_Mine'), 'special_scene')
        self.assertEqual(categorize_party('p_four_ways_inn', 'Four_Ways_Inn'), 'special_scene')
        self.assertEqual(categorize_party('p_dhorak_keep', 'Dhorak_Keep'), 'special_scene')
        self.assertEqual(categorize_party('p_main_party', 'Main_Party'), 'special_scene')
        
        # 7. 野怪与强盗刷新点
        self.assertEqual(categorize_party('p_steppe_bandit_spawn_point_1', '{!}steppe_bandit_sp_1'), 'spawn_point')
        self.assertEqual(categorize_party('p_sea_raider_spawn_point_1', '{!}sea_raider_sp_1'), 'spawn_point')
        
        # 8. 引擎系统内部项 ({!} 隐匿)
        self.assertEqual(categorize_party('p_temp_party', '{!}temp_party'), 'hidden_system')
        self.assertEqual(categorize_party('p_camp_bandits', '{!}camp_bandits'), 'hidden_system')
        self.assertEqual(categorize_party('p_temp_casualties', '{!}casualties'), 'hidden_system')
        self.assertEqual(categorize_party('p_temp_wounded', '{!}enemies_wounded'), 'hidden_system')
        self.assertEqual(categorize_party('p_spawn_points_end', '{!}last_spawn_point'), 'hidden_system')
        self.assertEqual(categorize_party('p_main_party_backup', '{!}_'), 'hidden_system')

    def test_category_meta_and_icons(self):
        for cat in ['town', 'castle', 'village', 'bridge', 'training_camp', 'special_scene', 'spawn_point', 'hidden_system']:
            self.assertIn(cat, CATEGORY_META)
            icon = create_category_icon(cat)
            self.assertFalse(icon.isNull())

    def test_bridge_rotation_and_saving(self):
        editor = MapEditor()
        # 模拟 parties.txt 数据结构 (2行一个据点)
        lines = [
            "partiesfile version 1\n",
            "2 2\n",
            " 1 1 1 p_bridge_1 {!}1 541739 0 0 3 0 0 0 0 0 10.000000 20.000000 10.000000 20.000000 10.000000 20.000000 0.0 0 \n",
            "1.570796\n",
            " 1 2 2 p_temp_party {!}temp_party 256 0 0 1 0 0 0 0 0 0.000000 0.000000 0.000000 0.000000 0.000000 0.000000 0.0 0 \n",
            "0.000000\n",
        ]
        editor.original_parties_lines = lines
        editor.parties = []
        
        for i in range(2, len(lines), 2):
            parts = lines[i].strip().split()
            angle = float(lines[i + 1].strip())
            cat = categorize_party(parts[3], parts[4])
            editor.parties.append({
                'index': i,
                'id': parts[3],
                'name': parts[4],
                'display_name': '桥梁 #1' if cat == 'bridge' else parts[4],
                'category': cat,
                'angle': angle,
                'faction': parts[8],
                'x': float(parts[14]),
                'y': float(parts[15]),
                'parts': parts
            })
            
        editor.update_party_list()
        editor.draw_parties()
        
        # 默认情况下系统隐匿项不在列表中
        self.assertEqual(editor.list_widget.count(), 1)
        self.assertEqual(len(editor.party_items), 1)
        
        # 勾选显示隐匿项
        editor.cb_show_hidden.setChecked(True)
        self.assertEqual(editor.list_widget.count(), 2)
        self.assertEqual(len(editor.party_items), 2)
        
        # 选中桥梁并测试旋转
        editor.party_items['p_bridge_1'].setSelected(True)
        bridge_party = editor.parties[0]
        self.assertAlmostEqual(bridge_party['angle'], 1.570796, places=4)
        
        # 旋转 +15 度
        editor.rotate_selected_bridge(15)
        self.assertAlmostEqual(bridge_party['angle'], 1.570796 + math.radians(15), places=4)

if __name__ == '__main__':
    unittest.main()
