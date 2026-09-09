import sys
import os
import math
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

# 16 种原生 Warband 大地图地形材质（兼容 Native / 1815 / 1257AD / 457 等全部 MOD）
TERRAIN_COLORS = {
    0: QColor(25, 45, 110),     # 0: 海洋 (Ocean)
    1: QColor(105, 105, 105),   # 1: 山脉 (Mountain)
    2: QColor(185, 175, 85),    # 2: 草原 (Steppe)
    3: QColor(85, 145, 45),     # 3: 平原 (Plain)
    4: QColor(240, 245, 255),   # 4: 雪原 (Snow)
    5: QColor(225, 205, 105),   # 5: 沙漠 (Desert)
    6: QColor(155, 105, 55),    # 6: 浅滩/桥梁 (Bridge/Ford)
    7: QColor(55, 125, 220),    # 7: 河流 (River)
    8: QColor(125, 115, 85),    # 8: 草原山脉 (Steppe Mountain)
    9: QColor(105, 135, 45),    # 9: 草原森林 (Steppe Forest)
    10: QColor(35, 85, 25),     # 10: 平原森林 (Plain Forest)
    11: QColor(205, 210, 215),  # 11: 雪山 (Snow Mountain)
    12: QColor(155, 185, 185),  # 12: 雪原森林 (Snow Forest)
    13: QColor(155, 135, 85),   # 13: 沙漠山脉 (Desert Mountain)
    14: QColor(185, 165, 65),   # 14: 沙漠森林 (Desert Forest)
    15: QColor(190, 0, 190),    # 15: 远洋/深水 (Deep Ocean / 1257&457航海紫色大洋)
}

TERRAIN_NAMES = {
    0: "海洋", 1: "山脉", 2: "草原", 3: "温带平原", 4: "雪原", 5: "沙漠",
    6: "浅滩/桥梁", 7: "河流", 8: "草原山脉", 9: "草原森林",
    10: "平原森林", 11: "雪山", 12: "雪原森林", 13: "沙漠山脉", 14: "沙漠森林",
    15: "远洋深水(1257紫色大洋)"
}


class PartyItem(QGraphicsItem):
    def __init__(self, party, editor):
        super().__init__()
        self.party = party
        self.editor = editor
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
        
        self.radius = 5
        self.hit_radius = 18  # 保证跟手、不钝感
        
        pid = party['id']
        self.color = Qt.red
        self.scale_mult = 1.0
        if pid.startswith('p_town'):
            self.color = Qt.blue
            self.scale_mult = 1.6
        elif pid.startswith('p_castle'):
            self.color = Qt.darkMagenta
            self.scale_mult = 1.3
        elif pid.startswith('p_village'):
            self.color = Qt.darkGreen
            self.scale_mult = 1.1
            
        self.setToolTip(f"{party['name']} (ID: {party['id']})\nFaction: {party['faction']}")
        
        self.label = QGraphicsTextItem(party['name'], self)
        self.label.setPos(self.hit_radius, -10)
        self.label.setFont(QFont("Arial", 10, QFont.Bold))
        self.label.setDefaultTextColor(Qt.black)

    def boundingRect(self):
        return QRectF(-self.hit_radius, -self.hit_radius, self.hit_radius*2, self.hit_radius*2)

    def paint(self, painter, option, widget):
        if self.isSelected():
            painter.setPen(QPen(Qt.yellow, 2))
        else:
            painter.setPen(QPen(Qt.black, 1))
        painter.setBrush(self.color)
        r = self.radius * self.scale_mult
        painter.drawEllipse(QRectF(-r, -r, r*2, r*2))

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            if self.editor.active_tool != "party":
                return self.pos()
            self.editor.is_modified = True
            new_pos = value
            game_x, game_y = self.editor.pixel_to_game(new_pos.x(), new_pos.y())
            self.party['x'] = game_x
            self.party['y'] = game_y
            self.editor.update_status(f"移动据点 {self.party['name']} 至 ({game_x:.2f}, {game_y:.2f})")
        return super().itemChange(change, value)


class MapView(QGraphicsView):
    def __init__(self, scene, editor):
        super().__init__(scene)
        self.editor = editor
        self.setRenderHint(QPainter.Antialiasing)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.NoDrag)
        self._is_panning = False
        self._pan_start = QPoint()
        
    def wheelEvent(self, event):
        zoom_in = 1.15
        zoom_out = 1 / zoom_in
        if event.angleDelta().y() > 0:
            self.editor.apply_zoom(zoom_in)
        else:
            self.editor.apply_zoom(zoom_out)
            
    def mousePressEvent(self, event):
        # 右键全局拖动画布，或手形工具左键拖动
        if event.button() == Qt.RightButton or (event.button() == Qt.LeftButton and self.editor.active_tool == "hand"):
            self._is_panning = True
            self._pan_start = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return
            
        if event.button() == Qt.LeftButton:
            scene_pos = self.mapToScene(event.pos())
            self.editor.handle_tool_press(scene_pos)
            if self.editor.active_tool == "party":
                super().mousePressEvent(event)
            else:
                event.accept()

    def mouseMoveEvent(self, event):
        if self._is_panning:
            delta = event.pos() - self._pan_start
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            self._pan_start = event.pos()
            event.accept()
            return
            
        if event.buttons() & Qt.LeftButton:
            scene_pos = self.mapToScene(event.pos())
            self.editor.handle_tool_drag(scene_pos)
            if self.editor.active_tool == "party":
                super().mouseMoveEvent(event)
            else:
                event.accept()
        else:
            super().mouseMoveEvent(event)
            
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.RightButton or (self._is_panning and event.button() == Qt.LeftButton):
            self._is_panning = False
            self.setCursor(Qt.ArrowCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)


class PalettePopup(QWidget):
    """紧凑的 8*2 调色板气泡窗口"""
    def __init__(self, editor):
        super().__init__(None, Qt.Popup | Qt.FramelessWindowHint)
        self.editor = editor
        self.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
                border: 1px solid #cbd5e1;
                border-radius: 8px;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        
        # 顶部当前选中展示
        top_row = QHBoxLayout()
        self.preview_badge = QLabel()
        self.preview_badge.setFixedSize(20, 20)
        self.preview_badge.setStyleSheet("border-radius: 4px; border: 1px solid #475569;")
        
        self.info_label = QLabel()
        self.info_label.setStyleSheet("font-size: 12px; font-weight: bold; color: #1e293b; border: none;")
        
        top_row.addWidget(self.preview_badge)
        top_row.addWidget(self.info_label)
        top_row.addStretch()
        layout.addLayout(top_row)
        
        # 8 x 2 调色盘网格
        grid = QGridLayout()
        grid.setSpacing(4)
        self.buttons = []
        for idx in range(16):
            r = idx // 8
            c = idx % 8
            btn = QToolButton()
            btn.setFixedSize(28, 28)
            color = TERRAIN_COLORS[idx]
            btn.setToolTip(f"{idx}: {TERRAIN_NAMES[idx]}")
            btn.setStyleSheet(f"""
                QToolButton {{
                    background-color: {color.name()};
                    border: 1px solid rgba(0,0,0,0.25);
                    border-radius: 4px;
                }}
                QToolButton:hover {{
                    border: 2px solid #2563eb;
                }}
            """)
            btn.clicked.connect(lambda checked, tid=idx: self.pick_terrain(tid))
            grid.addWidget(btn, r, c)
            self.buttons.append(btn)
            
        layout.addLayout(grid)
        self.update_preview(self.editor.selected_terrain)
        
    def pick_terrain(self, tid):
        self.editor.set_terrain(tid)
        self.update_preview(tid)
        self.close()
        
    def update_preview(self, tid):
        color = TERRAIN_COLORS[tid]
        self.preview_badge.setStyleSheet(f"background-color: {color.name()}; border-radius: 4px; border: 1px solid #475569;")
        self.info_label.setText(f"{tid}: {TERRAIN_NAMES[tid]}")


class MapEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.parties = []
        self.original_parties_lines = []
        self.parties_filepath = ""
        
        self.vertices = []
        self.faces = []
        self.adj = []
        self.spatial_grid = {}
        self.grid_size = 5.0
        self.map_filepath = ""
        
        self.img_width = 1000
        self.img_height = 1000
        self.min_x, self.max_x = -180.0, 180.0
        self.min_y, self.max_y = -180.0, 180.0
        self.scale_factor = 4.0
        
        self.zoom_level = 1.0
        self.active_tool = "party"  # hand, party, pencil, fill, picker
        self.selected_terrain = 3   # 默认平原
        self.is_modified = False
        
        self.undo_stack = []
        self.redo_stack = []
        
        self.id_map_image = None
        self.visual_image = None
        
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle('Warband Universal Map & Scene Editor')
        self.setGeometry(50, 50, 1600, 920)
        
        # 全局现代扁平化样式（Excalidraw 灵感）
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f8fafc;
            }
            QToolBar {
                background: transparent;
                border: none;
                margin: 6px 12px;
                spacing: 12px;
            }
            QFrame.pill-frame {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 2px 4px;
            }
            QToolButton {
                background: transparent;
                border: none;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 13px;
                color: #334155;
            }
            QToolButton:hover {
                background-color: #f1f5f9;
            }
            QToolButton:checked {
                background-color: #e0f2fe;
                color: #0284c7;
            }
            QToolButton::menu-indicator {
                image: none;
            }
            QDockWidget {
                font-weight: bold;
                color: #475569;
            }
            QDockWidget::title {
                background: #f1f5f9;
                padding: 6px;
                border-bottom: 1px solid #e2e8f0;
            }
            QListWidget, QLineEdit {
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                background: #ffffff;
                padding: 4px;
            }
        """)
        
        self.scene = QGraphicsScene()
        self.view = MapView(self.scene, self)
        self.setCentralWidget(self.view)
        
        # 调色板浮窗
        self.palette_popup = PalettePopup(self)
        
        # =================== 顶部悬浮工具条 ===================
        self.top_toolbar = QToolBar("TopBar", self)
        self.top_toolbar.setMovable(False)
        self.addToolBar(Qt.TopToolBarArea, self.top_toolbar)
        
        # 1. 左侧药丸面板 (文件菜单 + 撤销/重做)
        left_pill = QFrame()
        left_pill.setProperty("class", "pill-frame")
        left_layout = QHBoxLayout(left_pill)
        left_layout.setContentsMargins(4, 2, 4, 2)
        left_layout.setSpacing(2)
        
        self.btn_menu = QToolButton()
        self.btn_menu.setText("≡")
        self.btn_menu.setFont(QFont("Arial", 16, QFont.Bold))
        self.btn_menu.setToolTip("菜单 (文件与导出)")
        self.build_file_menu()
        left_layout.addWidget(self.btn_menu)
        
        self.btn_undo = QToolButton()
        self.btn_undo.setText("↶")
        self.btn_undo.setFont(QFont("Arial", 14))
        self.btn_undo.setToolTip("撤销 (Ctrl+Z)")
        self.btn_undo.clicked.connect(self.undo)
        left_layout.addWidget(self.btn_undo)
        
        self.btn_redo = QToolButton()
        self.btn_redo.setText("↷")
        self.btn_redo.setFont(QFont("Arial", 14))
        self.btn_redo.setToolTip("重做 (Ctrl+Y)")
        self.btn_redo.clicked.connect(self.redo)
        left_layout.addWidget(self.btn_redo)
        
        self.top_toolbar.addWidget(left_pill)
        
        # 弹性间隔
        spacer1 = QWidget()
        spacer1.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.top_toolbar.addWidget(spacer1)
        
        # 2. 中间药丸面板 (操作工具箱 + 调色板整合按钮 + 笔刷粗细)
        center_pill = QFrame()
        center_pill.setProperty("class", "pill-frame")
        center_layout = QHBoxLayout(center_pill)
        center_layout.setContentsMargins(4, 2, 4, 2)
        center_layout.setSpacing(2)
        
        self.tool_group = QActionGroup(self)
        
        self.act_hand = self.create_tool_action("✋", "漫游拖动", "hand")
        self.act_party = self.create_tool_action("↖", "选择与移动据点", "party", checked=True)
        self.act_pencil = self.create_tool_action("✏️", "地形铅笔涂抹", "pencil")
        self.act_fill = self.create_tool_action("🪣", "区域填充(油漆桶)", "fill")
        self.act_picker = self.create_tool_action("💉", "地形吸管", "picker")
        
        for act in [self.act_hand, self.act_party, self.act_pencil, self.act_fill, self.act_picker]:
            btn = QToolButton()
            btn.setDefaultAction(act)
            center_layout.addWidget(btn)
            
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.VLine)
        sep1.setStyleSheet("color: #cbd5e1; margin: 4px 6px;")
        center_layout.addWidget(sep1)
        
        # 集成调色板弹出按钮 (8*2)
        self.btn_palette = QToolButton()
        self.btn_palette.setToolTip("选择地貌材质 (8x2 调色盘)")
        self.btn_palette.clicked.connect(self.toggle_palette_popup)
        self.update_palette_btn_style()
        center_layout.addWidget(self.btn_palette)
        
        # 笔刷粗细
        lbl_size = QLabel(" 粗细:")
        lbl_size.setStyleSheet("color: #64748b; font-size: 12px;")
        center_layout.addWidget(lbl_size)
        
        self.spin_brush = QSpinBox()
        self.spin_brush.setRange(0, 15)
        self.spin_brush.setValue(2)
        self.spin_brush.setToolTip("笔刷半径 (0为单网格像素)")
        self.spin_brush.setStyleSheet("border: 1px solid #cbd5e1; border-radius: 4px; padding: 2px;")
        center_layout.addWidget(self.spin_brush)
        
        self.top_toolbar.addWidget(center_pill)
        
        # 弹性间隔
        spacer2 = QWidget()
        spacer2.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.top_toolbar.addWidget(spacer2)
        
        # 3. 右侧药丸面板 (缩放面板与视角重置)
        right_pill = QFrame()
        right_pill.setProperty("class", "pill-frame")
        right_layout = QHBoxLayout(right_pill)
        right_layout.setContentsMargins(4, 2, 4, 2)
        right_layout.setSpacing(2)
        
        btn_zoom_out = QToolButton()
        btn_zoom_out.setText("🔍-")
        btn_zoom_out.setToolTip("缩小")
        btn_zoom_out.clicked.connect(lambda: self.apply_zoom(1 / 1.2))
        right_layout.addWidget(btn_zoom_out)
        
        self.lbl_zoom = QLabel("100%")
        self.lbl_zoom.setAlignment(Qt.AlignCenter)
        self.lbl_zoom.setFixedWidth(46)
        self.lbl_zoom.setStyleSheet("font-size: 12px; font-weight: bold; color: #475569;")
        right_layout.addWidget(self.lbl_zoom)
        
        btn_zoom_in = QToolButton()
        btn_zoom_in.setText("🔍+")
        btn_zoom_in.setToolTip("放大")
        btn_zoom_in.clicked.connect(lambda: self.apply_zoom(1.2))
        right_layout.addWidget(btn_zoom_in)
        
        btn_reset_zoom = QToolButton()
        btn_reset_zoom.setText("🔄")
        btn_reset_zoom.setToolTip("重置视角与比例")
        btn_reset_zoom.clicked.connect(self.reset_view)
        right_layout.addWidget(btn_reset_zoom)
        
        self.top_toolbar.addWidget(right_pill)
        
        # =================== 左侧据点停靠板 ===================
        self.dock_parties = QDockWidget("据点列表 (Parties)", self)
        self.dock_parties.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        parties_widget = QWidget()
        pl = QVBoxLayout(parties_widget)
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("🔍 过滤据点...")
        self.filter_input.textChanged.connect(self.filter_list)
        pl.addWidget(self.filter_input)
        
        self.list_widget = QListWidget()
        self.list_widget.itemClicked.connect(self.on_list_click)
        pl.addWidget(self.list_widget)
        self.dock_parties.setWidget(parties_widget)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.dock_parties)
        
        self.status_bar = self.statusBar()
        self.status_bar.showMessage('就绪。点击左上角 ≡ 菜单加载 map.txt 与 parties.txt。左键绘图/移动，右键全局漫游。')
        
        self.party_items = {}
        self.map_pixmap_item = None
        self.map_pixmap = None
        
        # 快捷键支持
        QShortcut(QKeySequence("Ctrl+S"), self, self.save_all)
        QShortcut(QKeySequence("Ctrl+Shift+E"), self, self.export_image)
        QShortcut(QKeySequence("Ctrl+Z"), self, self.undo)
        QShortcut(QKeySequence("Ctrl+Y"), self, self.redo)

    def create_tool_action(self, icon_str, tooltip, tool_id, checked=False):
        act = QAction(icon_str, self, checkable=True)
        act.setToolTip(tooltip)
        act.setChecked(checked)
        self.tool_group.addAction(act)
        act.triggered.connect(lambda: self.set_tool(tool_id))
        return act

    def set_tool(self, tool_id):
        self.active_tool = tool_id
        for item in self.party_items.values():
            item.setFlag(QGraphicsItem.ItemIsMovable, self.active_tool == "party")

    def build_file_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: #ffffff;
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 24px;
                border-radius: 4px;
                font-size: 13px;
                color: #1e293b;
            }
            QMenu::item:selected {
                background: #f1f5f9;
            }
        """)
        
        act_open_map = menu.addAction("📁 打开 map.txt (大地图网格)")
        act_open_map.triggered.connect(self.load_maptxt)
        
        act_open_parties = menu.addAction("📁 打开 parties.txt (据点坐标)")
        act_open_parties.triggered.connect(self.load_parties)
        
        menu.addSeparator()
        
        act_save = menu.addAction("📄 保存文件 (Save All)\tCtrl+S")
        act_save.triggered.connect(self.save_all)
        
        act_export = menu.addAction("🖼 导出图片 (Export Image)\tCtrl+Shift+E")
        act_export.triggered.connect(self.export_image)
        
        menu.addSeparator()
        
        act_exit = menu.addAction("🚪 退出")
        act_exit.triggered.connect(self.close)
        
        self.btn_menu.setMenu(menu)
        self.btn_menu.setPopupMode(QToolButton.InstantPopup)

    def toggle_palette_popup(self):
        pos = self.btn_palette.mapToGlobal(QPoint(0, self.btn_palette.height() + 6))
        self.palette_popup.update_preview(self.selected_terrain)
        self.palette_popup.move(pos)
        self.palette_popup.show()

    def set_terrain(self, tid):
        self.selected_terrain = tid
        self.update_palette_btn_style()
        self.update_status(f"当前地貌笔刷: {tid} - {TERRAIN_NAMES[tid]}")

    def update_palette_btn_style(self):
        color = TERRAIN_COLORS[self.selected_terrain]
        self.btn_palette.setText(f" 🎨 {self.selected_terrain}:{TERRAIN_NAMES[self.selected_terrain]} ")
        self.btn_palette.setStyleSheet(f"""
            QToolButton {{
                background-color: {color.name()};
                color: {'#000000' if color.lightness() > 140 else '#ffffff'};
                font-weight: bold;
                border: 1px solid rgba(0,0,0,0.3);
                border-radius: 6px;
                padding: 4px 8px;
            }}
        """)

    def apply_zoom(self, factor):
        self.view.scale(factor, factor)
        self.zoom_level *= factor
        self.lbl_zoom.setText(f"{int(round(self.zoom_level * 100))}%")

    def reset_view(self):
        self.view.resetTransform()
        self.zoom_level = 1.0
        self.lbl_zoom.setText("100%")

    def closeEvent(self, event):
        if self.is_modified:
            reply = QMessageBox.question(
                self, '保存提示',
                "大地图或据点修改尚未保存，是否在退出前保存？",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                QMessageBox.Save
            )
            if reply == QMessageBox.Save:
                self.save_all()
                event.accept()
            elif reply == QMessageBox.Discard:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

    def undo(self):
        if not self.undo_stack:
            self.update_status("没有可撤销的操作")
            return
        record = self.undo_stack.pop()
        to_redo = []
        painter = QPainter(self.map_pixmap)
        painter.setPen(Qt.NoPen)
        for f_idx, old_t, new_t in record:
            to_redo.append((f_idx, old_t, new_t))
            self.faces[f_idx]['terrain'] = old_t
            painter.setBrush(TERRAIN_COLORS[old_t])
            v1, v2, v3 = self.vertices[self.faces[f_idx]['v1']], self.vertices[self.faces[f_idx]['v2']], self.vertices[self.faces[f_idx]['v3']]
            p1, p2, p3 = self.game_to_pixel_pt(v1[0], v1[1]), self.game_to_pixel_pt(v2[0], v2[1]), self.game_to_pixel_pt(v3[0], v3[1])
            painter.drawPolygon(QPolygonF([p1, p2, p3]))
        painter.end()
        self.map_pixmap_item.setPixmap(self.map_pixmap)
        self.redo_stack.append(to_redo)
        self.is_modified = True
        self.update_status("已撤销上一步绘制")

    def redo(self):
        if not self.redo_stack:
            self.update_status("没有可重做的操作")
            return
        record = self.redo_stack.pop()
        to_undo = []
        painter = QPainter(self.map_pixmap)
        painter.setPen(Qt.NoPen)
        for f_idx, old_t, new_t in record:
            to_undo.append((f_idx, old_t, new_t))
            self.faces[f_idx]['terrain'] = new_t
            painter.setBrush(TERRAIN_COLORS[new_t])
            v1, v2, v3 = self.vertices[self.faces[f_idx]['v1']], self.vertices[self.faces[f_idx]['v2']], self.vertices[self.faces[f_idx]['v3']]
            p1, p2, p3 = self.game_to_pixel_pt(v1[0], v1[1]), self.game_to_pixel_pt(v2[0], v2[1]), self.game_to_pixel_pt(v3[0], v3[1])
            painter.drawPolygon(QPolygonF([p1, p2, p3]))
        painter.end()
        self.map_pixmap_item.setPixmap(self.map_pixmap)
        self.undo_stack.append(to_undo)
        self.is_modified = True
        self.update_status("已重做操作")

    def export_image(self):
        if not self.map_pixmap:
            QMessageBox.warning(self, "提示", "尚未渲染大地图，无法导出。")
            return
        filepath, _ = QFileDialog.getSaveFileName(self, "导出地图全景图", "world_map.png", "PNG 图片 (*.png);;JPEG 图片 (*.jpg)")
        if filepath:
            self.map_pixmap.save(filepath)
            self.update_status(f"地图已导出至: {filepath}")
            QMessageBox.information(self, "导出成功", f"地图已成功导出到:\n{filepath}")

    def get_face_at(self, scene_pos):
        if not self.id_map_image: return -1
        x, y = int(scene_pos.x()), int(scene_pos.y())
        if x < 0 or y < 0 or x >= self.img_width or y >= self.img_height: return -1
        c = self.id_map_image.pixelColor(x, y)
        idx = (c.red() << 16) | (c.green() << 8) | c.blue()
        return idx if idx < len(self.faces) else -1
        
    def handle_tool_press(self, scene_pos):
        if self.active_tool == "picker":
            f_idx = self.get_face_at(scene_pos)
            if f_idx >= 0:
                t_id = self.faces[f_idx]['terrain']
                if t_id in TERRAIN_NAMES:
                    self.set_terrain(t_id)
                    self.act_pencil.setChecked(True)
                    self.set_tool("pencil")
        elif self.active_tool == "fill":
            f_idx = self.get_face_at(scene_pos)
            if f_idx >= 0:
                self.apply_flood_fill(f_idx)
        elif self.active_tool == "pencil":
            self.apply_pencil(scene_pos)
            
    def handle_tool_drag(self, scene_pos):
        if self.active_tool == "pencil":
            self.apply_pencil(scene_pos)

    def apply_pencil(self, scene_pos):
        radius = self.spin_brush.value()
        if radius == 0:
            f_idx = self.get_face_at(scene_pos)
            if f_idx >= 0 and self.faces[f_idx]['terrain'] != self.selected_terrain:
                self.paint_faces([f_idx], self.selected_terrain)
            return
            
        gx, gy = self.pixel_to_game(scene_pos.x(), scene_pos.y())
        r_grid = int(radius // self.grid_size) + 1
        cgx, cgy = int(gx // self.grid_size), int(gy // self.grid_size)
        
        to_paint = []
        for nx in range(cgx - r_grid, cgx + r_grid + 1):
            for ny in range(cgy - r_grid, cgy + r_grid + 1):
                if (nx, ny) in self.spatial_grid:
                    for f_idx in self.spatial_grid[(nx, ny)]:
                        f = self.faces[f_idx]
                        if f['terrain'] != self.selected_terrain:
                            dist_sq = (f['cx'] - gx)**2 + (f['cy'] - gy)**2
                            if dist_sq <= radius**2:
                                to_paint.append(f_idx)
                                
        if to_paint:
            self.paint_faces(to_paint, self.selected_terrain)

    def apply_flood_fill(self, start_idx):
        target_t = self.faces[start_idx]['terrain']
        if target_t == self.selected_terrain: return
        
        q = [start_idx]
        visited = set([start_idx])
        to_paint = []
        
        while q:
            curr = q.pop(0)
            to_paint.append(curr)
            for nbr in self.adj[curr]:
                if nbr not in visited and self.faces[nbr]['terrain'] == target_t:
                    visited.add(nbr)
                    q.append(nbr)
                    
        if to_paint:
            self.paint_faces(to_paint, self.selected_terrain)

    def paint_faces(self, indices, terrain):
        self.is_modified = True
        record = []
        painter = QPainter(self.map_pixmap)
        painter.setPen(Qt.NoPen)
        painter.setBrush(TERRAIN_COLORS[terrain])
        
        for idx in indices:
            old_t = self.faces[idx]['terrain']
            record.append((idx, old_t, terrain))
            self.faces[idx]['terrain'] = terrain
            v1 = self.vertices[self.faces[idx]['v1']]
            v2 = self.vertices[self.faces[idx]['v2']]
            v3 = self.vertices[self.faces[idx]['v3']]
            p1 = self.game_to_pixel_pt(v1[0], v1[1])
            p2 = self.game_to_pixel_pt(v2[0], v2[1])
            p3 = self.game_to_pixel_pt(v3[0], v3[1])
            painter.drawPolygon(QPolygonF([p1, p2, p3]))
            
        painter.end()
        self.map_pixmap_item.setPixmap(self.map_pixmap)
        self.undo_stack.append(record)
        self.redo_stack.clear()

    def load_maptxt(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "打开 map.txt", ".", "Text Files (*.txt)")
        if not filepath: return
        self.status_bar.showMessage("正在解析原生 map.txt 几何数据...")
        QApplication.processEvents()
        
        with open(filepath, 'r') as f:
            lines = f.readlines()
            
        self.vertices = []
        self.faces = []
        
        idx = 0
        num_verts = int(lines[idx].strip())
        idx += 1
        
        for i in range(num_verts):
            parts = lines[idx].strip().split()
            self.vertices.append((float(parts[0]), float(parts[1]), float(parts[2])))
            idx += 1
            
        num_faces = int(lines[idx].strip())
        idx += 1
        
        self.spatial_grid = {}
        for i in range(num_faces):
            line = lines[idx]
            parts = line.strip().split()
            v1, v2, v3 = int(parts[3]), int(parts[4]), int(parts[5])
            
            vx1, vy1 = self.vertices[v1][0], self.vertices[v1][1]
            vx2, vy2 = self.vertices[v2][0], self.vertices[v2][1]
            vx3, vy3 = self.vertices[v3][0], self.vertices[v3][1]
            cx, cy = (vx1+vx2+vx3)/3, (vy1+vy2+vy3)/3
            
            f_dict = {
                'terrain': int(parts[0]), 'v1': v1, 'v2': v2, 'v3': v3,
                'orig_parts': parts, 'cx': cx, 'cy': cy
            }
            self.faces.append(f_dict)
            
            gx, gy = int(cx // self.grid_size), int(cy // self.grid_size)
            if (gx, gy) not in self.spatial_grid: self.spatial_grid[(gx, gy)] = []
            self.spatial_grid[(gx, gy)].append(i)
            idx += 1
            
        self.status_bar.showMessage("构建地块相邻拓扑关系 (支持智能区域填充)...")
        QApplication.processEvents()
        
        self.adj = [[] for _ in range(num_faces)]
        edge_to_faces = {}
        for i, f in enumerate(self.faces):
            edges = [tuple(sorted((f['v1'], f['v2']))), tuple(sorted((f['v2'], f['v3']))), tuple(sorted((f['v3'], f['v1'])))]
            for e in edges:
                if e not in edge_to_faces: edge_to_faces[e] = []
                edge_to_faces[e].append(i)
        for faces_on_edge in edge_to_faces.values():
            if len(faces_on_edge) == 2:
                f1, f2 = faces_on_edge
                self.adj[f1].append(f2)
                self.adj[f2].append(f1)
                
        self.map_filepath = filepath
        self.build_map_images()
        self.status_bar.showMessage(f"成功载入 map.txt: {num_verts} 顶点, {num_faces} 面片。已全面适配 16 种生态地形。")

    def build_map_images(self):
        self.status_bar.showMessage("渲染大地图网格中...")
        QApplication.processEvents()
        
        self.min_x = min(v[0] for v in self.vertices)
        self.max_x = max(v[0] for v in self.vertices)
        self.min_y = min(v[1] for v in self.vertices)
        self.max_y = max(v[1] for v in self.vertices)
        
        self.scale_factor = 4.0
        self.img_width = int((self.max_x - self.min_x) * self.scale_factor)
        self.img_height = int((self.max_y - self.min_y) * self.scale_factor)
        
        self.id_map_image = QImage(self.img_width, self.img_height, QImage.Format_RGB32)
        self.id_map_image.fill(0xFFFFFF)
        
        id_painter = QPainter(self.id_map_image)
        id_painter.setPen(Qt.NoPen)
        
        visual_image = QImage(self.img_width, self.img_height, QImage.Format_RGB32)
        visual_image.fill(Qt.black)
        
        vis_painter = QPainter(visual_image)
        vis_painter.setPen(Qt.NoPen)
        
        for i, face in enumerate(self.faces):
            v1 = self.vertices[face['v1']]
            v2 = self.vertices[face['v2']]
            v3 = self.vertices[face['v3']]
            p1 = self.game_to_pixel_pt(v1[0], v1[1])
            p2 = self.game_to_pixel_pt(v2[0], v2[1])
            p3 = self.game_to_pixel_pt(v3[0], v3[1])
            polygon = QPolygonF([p1, p2, p3])
            
            id_color = QColor((i & 0xFF0000) >> 16, (i & 0x00FF00) >> 8, i & 0x0000FF)
            id_painter.setBrush(id_color)
            id_painter.drawPolygon(polygon)
            
            # 使用包含 16 种颜色的 TERRAIN_COLORS (默认紫红兜底)
            vis_painter.setBrush(TERRAIN_COLORS.get(face['terrain'], QColor(255, 0, 255)))
            vis_painter.drawPolygon(polygon)
            
        id_painter.end()
        vis_painter.end()
        
        self.map_pixmap = QPixmap.fromImage(visual_image)
        if self.map_pixmap_item:
            self.scene.removeItem(self.map_pixmap_item)
        self.map_pixmap_item = self.scene.addPixmap(self.map_pixmap)
        self.map_pixmap_item.setZValue(-1)
        self.scene.setSceneRect(0, 0, self.img_width, self.img_height)
        self.draw_parties()
        
    def load_parties(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "打开 parties.txt", ".", "Text Files (*.txt)")
        if not filepath: return
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            self.original_parties_lines = f.readlines()
            
        self.parties = []
        self.list_widget.clear()
        
        for i in range(2, len(self.original_parties_lines), 2):
            if i >= len(self.original_parties_lines) - 1: break
            line1 = self.original_parties_lines[i]
            parts = line1.strip().split()
            if len(parts) < 20: continue
            p = {
                'index': i, 'id': parts[3], 'name': parts[4].replace('_', ' '),
                'faction': parts[8], 'x': float(parts[14]), 'y': float(parts[15]), 'parts': parts
            }
            self.parties.append(p)
            item = QListWidgetItem(f"{p['name']} ({p['id']})")
            item.setData(Qt.UserRole, p['id'])
            self.list_widget.addItem(item)
            
        self.parties_filepath = filepath
        self.draw_parties()
        self.status_bar.showMessage(f"成功加载 {len(self.parties)} 个据点。")
        
    def filter_list(self, text):
        text = text.lower()
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setHidden(text not in item.text().lower())
            
    def game_to_pixel_pt(self, x, y):
        px = (x - self.min_x) * self.scale_factor
        py = self.img_height - (y - self.min_y) * self.scale_factor
        return QPointF(px, py)
        
    def pixel_to_game(self, px, py):
        x = (px / self.scale_factor) + self.min_x
        y = self.min_y + (self.img_height - py) / self.scale_factor
        return x, y
        
    def draw_parties(self):
        for item in self.party_items.values():
            self.scene.removeItem(item)
        self.party_items.clear()
        for party in self.parties:
            item = PartyItem(party, self)
            item.setPos(self.game_to_pixel_pt(party['x'], party['y']))
            item.setFlag(QGraphicsItem.ItemIsMovable, self.active_tool == "party")
            self.scene.addItem(item)
            self.party_items[party['id']] = item
            
    def on_list_click(self, list_item):
        pid = list_item.data(Qt.UserRole)
        item = self.party_items.get(pid)
        if item:
            self.view.centerOn(item)
            self.scene.clearSelection()
            item.setSelected(True)
            
    def update_status(self, msg):
        self.status_bar.showMessage(msg)
        
    def save_all(self):
        try:
            if self.map_filepath and self.faces:
                with open(self.map_filepath, 'r') as f: map_lines = f.readlines()
                idx = 0
                num_verts = int(map_lines[idx].strip())
                idx += num_verts + 1
                num_faces = int(map_lines[idx].strip())
                idx += 1
                for i in range(num_faces):
                    parts = self.faces[i]['orig_parts']
                    parts[0] = str(self.faces[i]['terrain'])
                    map_lines[idx] = " ".join(parts) + "\n"
                    idx += 1
                with open(self.map_filepath, 'w') as f:
                    f.writelines(map_lines)
                    
            if self.parties_filepath and self.original_parties_lines:
                for p in self.parties:
                    parts = p['parts']
                    x_str, y_str = f"{p['x']:.6f}", f"{p['y']:.6f}"
                    parts[14:20] = [x_str, y_str, x_str, y_str, x_str, y_str]
                    self.original_parties_lines[p['index']] = " " + " ".join(parts) + " \n"
                with open(self.parties_filepath, 'w', encoding='utf-8') as f:
                    f.writelines(self.original_parties_lines)
                    
            self.is_modified = False
            QMessageBox.information(self, "保存成功", "map.txt 与 parties.txt 已成功精确写回！")
            self.status_bar.showMessage("已保存所有修改。")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败:\n{str(e)}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MapEditor()
    ex.show()
    sys.exit(app.exec_())
