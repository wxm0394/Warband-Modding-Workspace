import sys
from pathlib import Path
from typing import Optional
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

from core.context import ProjectContext, ProjectConfig, COMMON_WARBAND_PATHS
from core.localization.manager import LocalizationManager
from core.build_runner.runner import BuildRunner
from apps.troop_equipment_editor.workbench import TroopEquipmentWorkbench
from apps.map_editor.map_editor import MapEditor

class WorkspaceWindow(QMainWindow):
    def __init__(self, default_mod_dir: Optional[str] = None):
        super().__init__()
        self.setWindowTitle("Warband Modding Workspace (战团 Mod 开发工作区)")
        self.resize(1360, 860)

        self.ctx: Optional[ProjectContext] = None
        self.loc = LocalizationManager()

        self.init_ui()

        # 如果传入了默认 mod 目录且存在，才自动加载；否则保持初始为空状态
        if default_mod_dir and Path(default_mod_dir).exists():
            self.load_mod(default_mod_dir)

    def init_ui(self):
        # 1. 顶部 Header 状态栏
        header_widget = QWidget()
        header_widget.setStyleSheet("background-color: #1e1e2e; color: #cdd6f4; border-bottom: 1px solid #313244;")
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(16, 8, 16, 8)

        self.lbl_title = QLabel("🛡️ Warband Modding Workspace")
        self.lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #89b4fa;")
        header_layout.addWidget(self.lbl_title)

        header_layout.addSpacing(20)

        self.lbl_project_info = QLabel()
        self.update_header_info()
        header_layout.addWidget(self.lbl_project_info)

        header_layout.addStretch()

        self.btn_reload_proj = QPushButton("🔄 重新检测项目")
        self.btn_reload_proj.clicked.connect(self.reload_project)
        header_layout.addWidget(self.btn_reload_proj)

        # 2. 主体选项卡
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setStyleSheet("""
            QTabBar::tab {
                padding: 10px 20px;
                font-size: 13px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background: #313244;
                color: #89b4fa;
            }
        """)

        # Tab 0: 项目设置
        self.tab_project = self.create_project_tab()
        self.tabs.addTab(self.tab_project, "📁 项目设置")

        # Tab 1: 地图工作台 (嵌入现有 Map Editor)
        self.map_editor_widget = MapEditor()
        self.tabs.addTab(self.map_editor_widget, "🗺️ 地图工作台")

        # Tab 2: 兵种与装备工作台
        self.troop_workbench = TroopEquipmentWorkbench(self.ctx, self.loc)
        self.tabs.addTab(self.troop_workbench, "⚔️ 兵种与装备")

        # Tab 3: 本地化中心
        self.tab_localization = self.create_localization_tab()
        self.tabs.addTab(self.tab_localization, "🌐 文本本地化")

        # Tab 4: 构建与测试
        self.tab_build = self.create_build_tab()
        self.tabs.addTab(self.tab_build, "🚀 构建与测试")

        # 布局
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(header_widget)
        layout.addWidget(self.tabs)
        self.setCentralWidget(container)

    def update_header_info(self):
        if not self.ctx:
            self.lbl_project_info.setText("当前 Mod: <span style='color:#f38ba8; font-weight:bold;'>未选择</span> (请在「项目设置」中选择 Mod 目录)")
            return
        rep = self.ctx.report
        mode_str = "<span style='color:#a6e3a1;'>Module System 源码模式</span>" if rep.is_source_ready else "<span style='color:#f9e2af;'>TXT 编译兼容模式</span>"
        git_str = f" | Git: <span style='color:#cba6f7;'>{rep.git_branch}</span>" if rep.is_git else ""
        self.lbl_project_info.setText(f"当前 Mod: <b>{self.ctx.config.project_name}</b> ({mode_str}{git_str})")

    def reload_project(self):
        m_dir = self.txt_mod_dir.text().strip()
        if not m_dir:
            QMessageBox.warning(self, "提示", "请先选择 Mod 目录！")
            return
        self.load_mod(m_dir)

    def load_mod(self, mod_dir_or_file: str, show_dialog: bool = True):
        target_path = Path(mod_dir_or_file).resolve()
        if target_path.is_file():
            target_path = target_path.parent

        s_dir = self.txt_source_dir.text().strip() or None
        self.ctx = ProjectContext.auto_detect(target_path, source_dir=s_dir)

        # 1. 更新顶部和项目设置表单
        self.update_header_info()
        self.txt_mod_dir.setText(str(self.ctx.module_path))
        if self.ctx.config.module_system_dir:
            self.txt_source_dir.setText(self.ctx.config.module_system_dir)
        self.txt_launch_cmd.setText(self.ctx.config.launch_command)
        self.txt_build_cmd.setText(self.ctx.config.build_command)
        self.txt_detection_report.setPlainText(self.ctx.report.summary())

        # 2. 载入本地化映射
        self._load_localization_from_mod(self.ctx.module_path)
        self.populate_localization_table()

        # 3. 载入兵种与装备数据
        self.troop_workbench.loc = self.loc
        self.troop_workbench.load_from_context(self.ctx)

        # 4. 主动识别并在地图工作台部署 map.txt 与 parties.txt
        map_txt = self.ctx.module_path / "map.txt"
        parties_txt = self.ctx.module_path / "parties.txt"
        loaded_map = False
        loaded_parties = False

        if map_txt.exists():
            self.map_editor_widget.load_maptxt(str(map_txt))
            loaded_map = True

        if parties_txt.exists():
            self.map_editor_widget.load_parties(str(parties_txt))
            loaded_parties = True

        if show_dialog:
            status_msg = [
                f"已成功载入 Mod: {self.ctx.config.project_name}",
                f"• 运行模式: {'Module System 源码模式' if self.ctx.report.is_source_ready else 'TXT 编译兼容模式'}",
                f"• 兵种装备: 已解析 {len(self.troop_workbench.troops)} 个兵种, {len(self.troop_workbench.items)} 个物品",
                f"• 地图网格 (map.txt): {'已在地图工作台自动部署' if loaded_map else '未找到 map.txt'}",
                f"• 据点坐标 (parties.txt): {'已在地图工作台自动部署' if loaded_parties else '未找到 parties.txt'}",
                f"• 本地化词条: 已加载 {len(self.loc.table)} 条中英文翻译"
            ]
            QMessageBox.information(self, "Mod 项目就绪", "\n".join(status_msg))

    def _load_localization_from_mod(self, mod_path: Path):
        self.loc = LocalizationManager(mod_path / ".workspace/localization.json")
        cns_dirs = [mod_path / "languages/cns", mod_path / "languages/zh_CN", mod_path / "languages/zh-hans"]
        for cns in cns_dirs:
            if cns.exists():
                for f in cns.glob("*.csv"):
                    self.loc.load_warband_csv(f, lang="zh_CN")
        en_dir = mod_path / "languages/en"
        if en_dir.exists():
            for f in en_dir.glob("*.csv"):
                self.loc.load_warband_csv(f, lang="en")

    # ==========================
    # Tab 0: 项目页
    # ==========================
    def create_project_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)

        form_box = QGroupBox("路径与配置")
        form_layout = QFormLayout(form_box)

        self.txt_mod_dir = QLineEdit()
        self.txt_mod_dir.setPlaceholderText("请选择 Mod 文件夹路径...")
        btn_browse_mod = QPushButton("浏览...")
        btn_browse_mod.clicked.connect(self.browse_mod_dir)
        h_mod = QHBoxLayout()
        h_mod.addWidget(self.txt_mod_dir)
        h_mod.addWidget(btn_browse_mod)
        form_layout.addRow("Mod 目标目录:", h_mod)

        self.txt_source_dir = QLineEdit()
        self.txt_source_dir.setPlaceholderText("可选：Module System 源码路径...")
        btn_browse_src = QPushButton("浏览...")
        btn_browse_src.clicked.connect(self.browse_src_dir)
        h_src = QHBoxLayout()
        h_src.addWidget(self.txt_source_dir)
        h_src.addWidget(btn_browse_src)
        form_layout.addRow("Module System 源码目录:", h_src)

        self.txt_launch_cmd = QLineEdit()
        form_layout.addRow("游戏启动命令:", self.txt_launch_cmd)

        self.txt_build_cmd = QLineEdit("python3 build_module.py")
        form_layout.addRow("编译命令:", self.txt_build_cmd)

        layout.addWidget(form_box)

        # 报告区
        rep_box = QGroupBox("环境自检与模式报告")
        rep_layout = QVBoxLayout(rep_box)
        self.txt_detection_report = QTextEdit()
        self.txt_detection_report.setReadOnly(True)
        self.txt_detection_report.setFont(QFont("Monospace", 10))
        self.txt_detection_report.setPlainText(
            "当前工作区尚未载入任何 Mod。\n\n"
            "操作指引:\n"
            "1. 点击上方「浏览...」按钮。\n"
            "2. 文件浏览对话框默认定位在 Warband 的 Modules/ 目录。\n"
            "3. 单击目标 Mod 文件夹并点击 Choose 按钮，或双击进入 Mod 文件夹后点击 Choose 按钮。\n"
            "4. 选中后，工作区将自动完成:\n"
            "   ✓ 自动识别 map.txt 与 parties.txt 并在地图工作台部署\n"
            "   ✓ 自动解析兵种、领主、NPC 与装备库\n"
            "   ✓ 自动关联 languages/ 下的中英文翻译表"
        )
        rep_layout.addWidget(self.txt_detection_report)
        layout.addWidget(rep_box)

        btn_save_cfg = QPushButton("💾 保存工作区配置 (.workspace_config.json)")
        btn_save_cfg.clicked.connect(self.save_project_config)
        layout.addWidget(btn_save_cfg)

        return widget

    def browse_mod_dir(self):
        current = self.txt_mod_dir.text().strip()
        start_dir = ""
        if current and Path(current).exists():
            # 如果当前已有路径，打开其父级 (Modules 目录)，方便单击选择目标文件夹
            start_dir = str(Path(current).parent)
        else:
            # 自动探测 Warband Modules 目录作为默认浏览起点
            for p in COMMON_WARBAND_PATHS:
                cand = p / "Modules"
                if cand.exists():
                    start_dir = str(cand)
                    break
                if p.exists() and (p / "game" / "Modules").exists():
                    start_dir = str(p / "game" / "Modules")
                    break
            if not start_dir:
                alt = Path.home() / "GOG Games/Mount Blade Warband/game/Modules"
                if alt.exists():
                    start_dir = str(alt)
                else:
                    start_dir = str(Path.home())

        d = QFileDialog.getExistingDirectory(
            self,
            "选择 Mod 目录 (单击选中后点击 Choose，或双击进入后点击 Choose)",
            start_dir
        )
        if d:
            self.load_mod(d)

    def browse_src_dir(self):
        start_dir = self.txt_source_dir.text().strip() or str(Path.home())
        d = QFileDialog.getExistingDirectory(self, "选择 Module System 源码目录", start_dir)
        if d:
            self.txt_source_dir.setText(d)
            if self.ctx:
                self.ctx.config.module_system_dir = d
                self.reload_project()

    def save_project_config(self):
        if not self.ctx:
            QMessageBox.warning(self, "提示", "当前未载入任何 Mod 项目。")
            return
        self.ctx.config.module_dir = self.txt_mod_dir.text()
        self.ctx.config.module_system_dir = self.txt_source_dir.text() or None
        self.ctx.config.launch_command = self.txt_launch_cmd.text()
        self.ctx.config.build_command = self.txt_build_cmd.text()
        self.ctx.save()
        QMessageBox.information(self, "保存成功", "工作区配置已持久化。")

    # ==========================
    # Tab 3: 本地化中心
    # ==========================
    def create_localization_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)

        top_bar = QHBoxLayout()
        self.loc_search = QLineEdit()
        self.loc_search.setPlaceholderText("过滤 ID 或词条文本...")
        self.loc_search.textChanged.connect(self.filter_localization)
        top_bar.addWidget(self.loc_search)

        btn_export = QPushButton("📤 导出为 Warband 官方 CSV")
        btn_export.clicked.connect(self.export_loc_csv)
        top_bar.addWidget(btn_export)

        btn_save_loc = QPushButton("💾 保存翻译表")
        btn_save_loc.clicked.connect(self.save_localization)
        top_bar.addWidget(btn_save_loc)

        layout.addLayout(top_bar)

        self.loc_table = QTableWidget(0, 3)
        self.loc_table.setHorizontalHeaderLabels(["ID (Key)", "默认英文 (en)", "简体中文 (zh_CN)"])
        self.loc_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.loc_table)

        self.populate_localization_table()
        return widget

    def populate_localization_table(self):
        self.loc_table.setRowCount(0)
        entries = list(self.loc.table.items())
        self.loc_table.setRowCount(len(entries))
        for r, (k, d) in enumerate(entries):
            en_val = d.get("en") or d.get("default") or ""
            zh_val = d.get("zh_CN") or ""
            k_item = QTableWidgetItem(k)
            k_item.setFlags(k_item.flags() ^ Qt.ItemIsEditable)
            self.loc_table.setItem(r, 0, k_item)
            self.loc_table.setItem(r, 1, QTableWidgetItem(en_val))
            self.loc_table.setItem(r, 2, QTableWidgetItem(zh_val))

    def filter_localization(self, text: str):
        text = text.lower()
        for r in range(self.loc_table.rowCount()):
            k = self.loc_table.item(r, 0).text().lower()
            en = self.loc_table.item(r, 1).text().lower()
            zh = self.loc_table.item(r, 2).text().lower()
            self.loc_table.setRowHidden(r, not (text in k or text in en or text in zh))

    def save_localization(self):
        if not self.ctx:
            QMessageBox.warning(self, "提示", "请先载入 Mod 项目。")
            return
        for r in range(self.loc_table.rowCount()):
            k = self.loc_table.item(r, 0).text()
            en = self.loc_table.item(r, 1).text()
            zh = self.loc_table.item(r, 2).text()
            self.loc.register(k, default_name=en, zh_name=zh)
        self.loc.save_json(self.ctx.module_path / ".workspace/localization.json")
        QMessageBox.information(self, "本地化保存", "多语言映射表已持久化！")

    def export_loc_csv(self):
        if not self.ctx:
            QMessageBox.warning(self, "提示", "请先载入 Mod 项目。")
            return
        target_dir = self.ctx.module_path / "languages/cns"
        self.loc.export_warband_csv("trp_", target_dir / "troops.csv", lang="zh_CN")
        self.loc.export_warband_csv("itm_", target_dir / "item_kinds.csv", lang="zh_CN")
        self.loc.export_warband_csv("p_", target_dir / "parties.csv", lang="zh_CN")
        QMessageBox.information(self, "导出成功", f"已在 {target_dir} 生成 troops.csv, item_kinds.csv, parties.csv！")

    # ==========================
    # Tab 4: 构建与测试
    # ==========================
    def create_build_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)

        btn_bar = QHBoxLayout()
        self.btn_run_build = QPushButton("⚙️ 执行 Module System 编译")
        self.btn_run_build.setStyleSheet("font-weight: bold; padding: 8px 16px; background-color: #1e66f5; color: white;")
        self.btn_run_build.clicked.connect(self.trigger_build)
        btn_bar.addWidget(self.btn_run_build)

        self.btn_launch = QPushButton("▶ 启动 Warband 快速测试")
        self.btn_launch.setStyleSheet("font-weight: bold; padding: 8px 16px; background-color: #40a02b; color: white;")
        self.btn_launch.clicked.connect(self.trigger_launch)
        btn_bar.addWidget(self.btn_launch)

        layout.addLayout(btn_bar)

        tip_lbl = QLabel("💡 提示：静态兵种和领主初始装备修改后，需新开档生效。")
        tip_lbl.setStyleSheet("color: #df8e1d; font-weight: bold;")
        layout.addWidget(tip_lbl)

        box_out = QGroupBox("编译输出日志与行号追踪")
        lay_out = QVBoxLayout(box_out)
        self.build_log = QTextEdit()
        self.build_log.setReadOnly(True)
        self.build_log.setFont(QFont("Monospace", 10))
        lay_out.addWidget(self.build_log)
        layout.addWidget(box_out)

        return widget

    def trigger_build(self):
        if not self.ctx:
            QMessageBox.warning(self, "提示", "请先在项目设置中选择并载入 Mod！")
            return
        self.build_log.clear()
        self.build_log.append(">>> 开始编译 Module System...\n")
        QApplication.processEvents()

        success, output, errors = BuildRunner.run_build(
            self.ctx,
            output_callback=lambda line: (self.build_log.append(line.rstrip()), QApplication.processEvents())
        )
        if success:
            self.build_log.append("\n✅ 编译圆满完成！TXT 数据已同步更新至 Mod 目录。")
            QMessageBox.information(self, "编译成功", "Module System 编译成功！")
        else:
            self.build_log.append(f"\n❌ 编译失败，发现 {len(errors)} 处错误定位。")
            err_details = "\n".join([f"- {e['file']} (第 {e['line']} 行)" for e in errors])
            QMessageBox.critical(self, "编译失败", f"编译进程异常退出:\n{err_details}")

    def trigger_launch(self):
        if not self.ctx:
            QMessageBox.warning(self, "提示", "请先在项目设置中选择并载入 Mod！")
            return
        ok, msg = BuildRunner.launch_game(self.ctx)
        if ok:
            QMessageBox.information(self, "拉起游戏", msg)
        else:
            QMessageBox.warning(self, "启动失败", msg)


def main():
    QCoreApplication.setAttribute(Qt.AA_UseSoftwareOpenGL)
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = WorkspaceWindow()
    win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()

