import sys
from pathlib import Path
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from typing import Optional, List, Dict

from core.context import ProjectContext
from core.data_models.models import Troop, ItemRef
from core.module_source_parser.parser import parse_items, parse_troops
from core.module_source_parser.writer import save_troops_transaction
from core.compiled_txt_parser.txt_parser import CompiledTxtParser
from core.validation.cross_validator import CrossReferenceValidator
from core.localization.manager import LocalizationManager

class TroopEquipmentWorkbench(QWidget):
    """兵种与装备独立工作台组件"""
    def __init__(self, ctx: Optional[ProjectContext] = None, loc: Optional[LocalizationManager] = None, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.loc = loc or LocalizationManager()
        self.troops: List[Troop] = []
        self.items: List[ItemRef] = []
        self.selected_troop: Optional[Troop] = None
        self.modified_troops: Dict[str, Troop] = {} # {trp_id: Troop}
        self.file_mtime: Optional[float] = None

        self.init_ui()
        if self.ctx:
            self.load_from_context(self.ctx)

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)

        # 1. 顶部工具条
        toolbar = QHBoxLayout()
        self.status_lbl = QLabel("模式: 未加载")
        self.status_lbl.setStyleSheet("font-weight: bold; color: #4A90E2;")
        toolbar.addWidget(self.status_lbl)

        toolbar.addStretch()

        self.btn_validate = QPushButton("🔍 跨引用与逻辑校验")
        self.btn_validate.clicked.connect(self.run_validation)
        toolbar.addWidget(self.btn_validate)

        self.btn_diff = QPushButton("📝 预览变更 Diff")
        self.btn_diff.clicked.connect(self.preview_diff)
        toolbar.addWidget(self.btn_diff)

        self.btn_save = QPushButton("💾 安全保存 (事务备份)")
        self.btn_save.setStyleSheet("background-color: #2E7D32; color: white; font-weight: bold; padding: 4px 12px;")
        self.btn_save.clicked.connect(self.save_changes)
        toolbar.addWidget(self.btn_save)

        main_layout.addLayout(toolbar)

        # 2. 中间三栏主体分割
        splitter = QSplitter(Qt.Horizontal)

        # 2.1 左栏：兵种列表
        left_box = QGroupBox("兵种 / 领主 / NPC 列表")
        left_layout = QVBoxLayout(left_box)
        self.troop_search = QLineEdit()
        self.troop_search.setPlaceholderText("搜索兵种 ID 或名称...")
        self.troop_search.textChanged.connect(self.filter_troops)
        left_layout.addWidget(self.troop_search)

        self.troop_list = QListWidget()
        self.troop_list.currentItemChanged.connect(self.on_troop_selected)
        left_layout.addWidget(self.troop_list)
        splitter.addWidget(left_box)

        # 2.2 中栏：选中兵种属性
        mid_box = QGroupBox("兵种基本属性")
        mid_layout = QFormLayout(mid_box)
        self.txt_troop_id = QLineEdit()
        self.txt_troop_id.setReadOnly(True)
        self.txt_troop_name = QLineEdit()
        self.txt_troop_plural = QLineEdit()
        self.txt_troop_flags = QLineEdit()
        self.txt_troop_flags.setReadOnly(True)

        mid_layout.addRow("兵种 ID:", self.txt_troop_id)
        mid_layout.addRow("单数名称:", self.txt_troop_name)
        mid_layout.addRow("复数名称:", self.txt_troop_plural)
        mid_layout.addRow("特性标记:", self.txt_troop_flags)
        
        # 批量替换小工具
        replace_box = QGroupBox("批量替换装备")
        rep_layout = QVBoxLayout(replace_box)
        self.txt_old_item = QLineEdit()
        self.txt_old_item.setPlaceholderText("原物品 ID (如 itm_cartridges)")
        self.txt_new_item = QLineEdit()
        self.txt_new_item.setPlaceholderText("新物品 ID (如 itm_cartridges_heavy)")
        btn_batch_rep = QPushButton("⚡ 在当前兵种中替换")
        btn_batch_rep.clicked.connect(self.batch_replace_item)
        rep_layout.addWidget(self.txt_old_item)
        rep_layout.addWidget(self.txt_new_item)
        rep_layout.addWidget(btn_batch_rep)
        mid_layout.addRow(replace_box)

        splitter.addWidget(mid_box)

        # 2.3 右栏：装备槽清单
        right_box = QGroupBox("已装备槽 (Equipment Slots)")
        right_layout = QVBoxLayout(right_box)
        self.equipment_list = QListWidget()
        right_layout.addWidget(self.equipment_list)

        eq_btn_layout = QHBoxLayout()
        self.btn_del_eq = QPushButton("❌ 卸下选中")
        self.btn_del_eq.clicked.connect(self.remove_selected_item)
        self.btn_clear_eq = QPushButton("🧹 清空装备")
        self.btn_clear_eq.clicked.connect(self.clear_equipment)
        eq_btn_layout.addWidget(self.btn_del_eq)
        eq_btn_layout.addWidget(self.btn_clear_eq)
        right_layout.addLayout(eq_btn_layout)

        splitter.addWidget(right_box)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 3)
        splitter.setStretchFactor(2, 4)

        main_layout.addWidget(splitter, stretch=6)

        # 3. 底部栏：物品库检索与添加
        bot_box = QGroupBox("物品数据库 (双击或点击添加按钮穿上装备)")
        bot_layout = QVBoxLayout(bot_box)
        bot_top = QHBoxLayout()
        self.item_search = QLineEdit()
        self.item_search.setPlaceholderText("搜索物品 ID、英文或中文名...")
        self.item_search.textChanged.connect(self.filter_items)
        bot_top.addWidget(self.item_search)

        self.btn_add_item = QPushButton("➕ 装备到当前兵种")
        self.btn_add_item.clicked.connect(self.add_selected_item_to_troop)
        bot_top.addWidget(self.btn_add_item)
        bot_layout.addLayout(bot_top)

        self.item_table = QTableWidget(0, 3)
        self.item_table.setHorizontalHeaderLabels(["物品 ID", "默认英文名", "本地化 (中文)"])
        self.item_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.item_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.item_table.doubleClicked.connect(self.add_selected_item_to_troop)
        bot_layout.addWidget(self.item_table)

        main_layout.addWidget(bot_box, stretch=4)

    def load_from_context(self, ctx: Optional[ProjectContext]):
        self.ctx = ctx
        self.troops.clear()
        self.items.clear()
        self.modified_troops.clear()

        if not ctx:
            self.status_lbl.setText("模式: 未载入 Mod (请在「项目设置」中选择)")
            self.populate_troops()
            self.populate_items()
            return

        # 优先源码模式
        if ctx.config.source_mode:
            self.status_lbl.setText(f"模式: Module System 源码模式 ({ctx.config.project_name})")
            t_file = ctx.get_source_file("module_troops.py")
            i_file = ctx.get_source_file("module_items.py")

            if i_file and i_file.exists():
                self.items = parse_items(i_file.read_text(encoding="utf-8", errors="replace"))
            if t_file and t_file.exists():
                self.file_mtime = t_file.stat().st_mtime
                self.troops = parse_troops(t_file.read_text(encoding="utf-8", errors="replace"))
        else:
            self.status_lbl.setText(f"模式: 编译后 TXT 兼容模式 ({ctx.config.project_name})")
            i_file = ctx.get_compiled_file("item_kinds1.txt")
            t_file = ctx.get_compiled_file("troops.txt")

            if i_file:
                self.items = CompiledTxtParser.parse_item_kinds1(i_file)
            item_lookup = {idx: itm.id for idx, itm in enumerate(self.items)}
            if t_file:
                self.file_mtime = t_file.stat().st_mtime
                self.troops = CompiledTxtParser.parse_troops_txt(t_file, item_lookup)

        self.populate_troops()
        self.populate_items()

    def populate_troops(self):
        self.troop_list.clear()
        for t in self.troops:
            display = self.loc.get_display_name(t.id, t.name_singular, mode="both")
            item = QListWidgetItem(display)
            item.setData(Qt.UserRole, t.id)
            self.troop_list.addItem(item)

    def populate_items(self):
        self.item_table.setRowCount(0)
        self.item_table.setRowCount(len(self.items))
        for r, itm in enumerate(self.items):
            zh = self.loc.get(itm.id, default="", lang="zh_CN")
            self.item_table.setItem(r, 0, QTableWidgetItem(itm.id))
            self.item_table.setItem(r, 1, QTableWidgetItem(itm.display_name))
            self.item_table.setItem(r, 2, QTableWidgetItem(zh))

    def filter_troops(self, text: str):
        text = text.lower()
        for i in range(self.troop_list.count()):
            item = self.troop_list.item(i)
            tid = item.data(Qt.UserRole)
            item.setHidden(text not in item.text().lower() and text not in tid.lower())

    def filter_items(self, text: str):
        text = text.lower()
        for r in range(self.item_table.rowCount()):
            iid = self.item_table.item(r, 0).text().lower()
            en = self.item_table.item(r, 1).text().lower()
            zh = self.item_table.item(r, 2).text().lower()
            match = (text in iid or text in en or text in zh)
            self.item_table.setRowHidden(r, not match)

    def on_troop_selected(self, current: QListWidgetItem, previous: QListWidgetItem):
        if not current:
            return
        tid = current.data(Qt.UserRole)
        troop = next((t for t in self.troops if t.id == tid), None)
        if not troop:
            return
        self.selected_troop = troop
        self.txt_troop_id.setText(troop.id)
        self.txt_troop_name.setText(troop.name_singular)
        self.txt_troop_plural.setText(troop.name_plural)
        self.txt_troop_flags.setText(str(troop.flags or "Default"))

        self.refresh_equipment_list()

    def refresh_equipment_list(self):
        self.equipment_list.clear()
        if not self.selected_troop:
            return
        for itm_id in self.selected_troop.equipment:
            zh = self.loc.get(itm_id, default="", lang="zh_CN")
            text = f"{itm_id} ({zh})" if zh else itm_id
            self.equipment_list.addItem(text)

    def add_selected_item_to_troop(self):
        if not self.selected_troop:
            QMessageBox.warning(self, "提示", "请先在左侧选择一个兵种！")
            return
        cur_row = self.item_table.currentRow()
        if cur_row < 0:
            return
        itm_id = self.item_table.item(cur_row, 0).text()
        self.selected_troop.equipment.append(itm_id)
        self.modified_troops[self.selected_troop.id] = self.selected_troop
        self.refresh_equipment_list()

    def remove_selected_item(self):
        if not self.selected_troop:
            return
        cur_row = self.equipment_list.currentRow()
        if cur_row < 0:
            return
        del self.selected_troop.equipment[cur_row]
        self.modified_troops[self.selected_troop.id] = self.selected_troop
        self.refresh_equipment_list()

    def clear_equipment(self):
        if not self.selected_troop:
            return
        self.selected_troop.equipment.clear()
        self.modified_troops[self.selected_troop.id] = self.selected_troop
        self.refresh_equipment_list()

    def batch_replace_item(self):
        if not self.selected_troop:
            return
        old_item = self.txt_old_item.text().strip()
        new_item = self.txt_new_item.text().strip()
        if not old_item or not new_item:
            QMessageBox.warning(self, "提示", "请输入原物品和新物品 ID！")
            return
        changed = False
        new_eq = []
        for itm in self.selected_troop.equipment:
            if itm == old_item:
                new_eq.append(new_item)
                changed = True
            else:
                new_eq.append(itm)
        if changed:
            self.selected_troop.equipment = new_eq
            self.modified_troops[self.selected_troop.id] = self.selected_troop
            self.refresh_equipment_list()
            QMessageBox.information(self, "完成", f"已将 {old_item} 替换为 {new_item}！")
        else:
            QMessageBox.information(self, "未找到", f"该兵种未装备 {old_item}。")

    def run_validation(self):
        if not self.ctx:
            return
        known_items = {i.id for i in self.items}
        validator = CrossReferenceValidator(known_items=known_items)
        issues = []
        for t in self.troops:
            issues.extend(validator.validate_troop(t.id, t.equipment))

        if not issues:
            QMessageBox.information(self, "校验通过", "所有兵种装备均合法，无引用或逻辑异常！")
        else:
            errs = [f"[{i.severity}] {i.target_id}: {i.message}" for i in issues]
            msg = "\n".join(errs[:30])
            if len(errs) > 30:
                msg += f"\n...及其他 {len(errs) - 30} 项异常"
            QMessageBox.warning(self, f"发现 {len(issues)} 项异常", msg)

    def preview_diff(self):
        if not self.modified_troops:
            QMessageBox.information(self, "提示", "当前没有做任何未保存的修改。")
            return
        if not self.ctx.config.source_mode:
            QMessageBox.information(self, "提示", "TXT 模式直接改动内存数据，Diff 暂只支持源码模式。")
            return

        t_file = self.ctx.get_source_file("module_troops.py")
        tx = save_troops_transaction(
            file_path=t_file,
            modified_troops=list(self.modified_troops.values()),
            backup_dir=self.ctx.backup_path,
            original_mtime=self.file_mtime
        )
        diff_text = tx.get_diff()
        
        dlg = QDialog(self)
        dlg.setWindowTitle("修改 Diff 预览")
        dlg.resize(700, 450)
        dlg_layout = QVBoxLayout(dlg)
        txt = QTextEdit()
        txt.setReadOnly(True)
        txt.setFont(QFont("Monospace", 10))
        txt.setPlainText(diff_text or "无文本差异")
        dlg_layout.addWidget(txt)
        btn_close = QPushButton("关闭")
        btn_close.clicked.connect(dlg.accept)
        dlg_layout.addWidget(btn_close)
        dlg.exec_()

    def save_changes(self):
        if not self.modified_troops:
            QMessageBox.information(self, "提示", "无修改需要保存。")
            return

        if not self.ctx.config.source_mode:
            QMessageBox.warning(self, "注意", "当前为 TXT 模式，暂只支持在源码模式下原子回写 module_troops.py。")
            return

        t_file = self.ctx.get_source_file("module_troops.py")
        try:
            tx = save_troops_transaction(
                file_path=t_file,
                modified_troops=list(self.modified_troops.values()),
                backup_dir=self.ctx.backup_path,
                description=f"修改了 {len(self.modified_troops)} 个兵种的装备",
                original_mtime=self.file_mtime
            )
            tx.commit()
            self.file_mtime = t_file.stat().st_mtime
            self.modified_troops.clear()
            QMessageBox.information(self, "成功", "兵种装备已安全原子保存，并已在 .workspace/backups 中生成备份！")
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"保存出错: {e}")
