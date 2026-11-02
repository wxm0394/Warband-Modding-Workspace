#!/usr/bin/env python3
import sys
import os
import math
import re

# ==================== Linux DRM / NVIDIA 驱动崩溃防御 ====================
# 强制 PyQt5 使用纯 CPU 软件光栅引擎，禁用 DRI3/GLX 硬件探测与设备打开
os.environ["QT_XCB_FORCE_SOFTWARE_OPENGL"] = "1"
os.environ["LIBGL_ALWAYS_SOFTWARE"] = "1"
os.environ["QT_QUICK_BACKEND"] = "software"
# =======================================================================

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

# 强制开启软件 OpenGL
QCoreApplication.setAttribute(Qt.AA_UseSoftwareOpenGL)


# 16 种原生 Warband 大地图地形材质 (严格遵循 header_terrain_types.py 引擎标准)
TERRAIN_COLORS = {
    0: QColor(25, 45, 110),     # 0: 海洋 (rt_water)
    1: QColor(105, 105, 105),   # 1: 山脉 (rt_mountain)
    2: QColor(125, 115, 85),    # 2: 草原山脉 (rt_steppe_mountain)
    3: QColor(85, 145, 45),     # 3: 平原 (rt_plain)
    4: QColor(240, 245, 255),   # 4: 雪原 (rt_snow)
    5: QColor(225, 205, 105),   # 5: 沙漠 (rt_desert)
    6: QColor(185, 175, 85),    # 6: 草原 (rt_steppe)
    7: QColor(155, 105, 55),    # 7: 浅滩/桥梁 (rt_bridge)
    8: QColor(55, 125, 220),    # 8: 河流 (rt_river)
    9: QColor(205, 210, 215),   # 9: 雪山 (rt_snow_mountain)
    10: QColor(105, 135, 45),   # 10: 草原森林 (rt_steppe_forest)
    11: QColor(35, 85, 25),     # 11: 森林 (rt_forest)
    12: QColor(155, 185, 185),  # 12: 雪原森林 (rt_snow_forest)
    13: QColor(185, 165, 65),   # 13: 沙漠森林 (rt_desert_forest)
    14: QColor(155, 135, 85),   # 14: 沙漠山脉 (原版无，兼容用)
    15: QColor(190, 0, 190),    # 15: 远洋/深水 (原版无，兼容用)
}

TERRAIN_NAMES = {
    0: "海洋", 1: "山脉", 2: "草原山脉", 3: "平原", 4: "雪原", 5: "沙漠",
    6: "草原", 7: "桥梁", 8: "河流", 9: "雪山", 10: "草原森林",
    11: "森林", 12: "雪原森林", 13: "沙漠森林", 14: "沙漠山脉", 15: "远洋深水"
}


# 8 种据点类型元数据（7 种拿战战役地图经典矢量标 + 1 种引擎系统隐匿项）
CATEGORY_META = {
    'town': {
        'name': '城镇 (Town)',
        'color': '#2563eb',
        'badge': '🏰'
    },
    'castle': {
        'name': '堡垒 (Castle)',
        'color': '#dc2626',
        'badge': '🛡️'
    },
    'village': {
        'name': '村庄 (Village)',
        'color': '#d97706',
        'badge': '🌾'
    },
    'bridge': {
        'name': '桥梁 (Bridge)',
        'color': '#475569',
        'badge': '🌉'
    },
    'training_camp': {
        'name': '训练营 (Camp)',
        'color': '#16a34a',
        'badge': '⛺'
    },
    'special_scene': {
        'name': '特殊/遗留场景 (Relic)',
        'color': '#8b5cf6',
        'badge': '🏛️'
    },
    'spawn_point': {
        'name': '野怪刷新点 (Spawn)',
        'color': '#ea580c',
        'badge': '⚔️'
    },
    'hidden_system': {
        'name': '系统引擎项 (Hidden)',
        'color': '#6c7086',
        'badge': '⚙️'
    },
}

_CATEGORY_ICON_CACHE = {}

def create_category_icon(cat):
    if cat in _CATEGORY_ICON_CACHE:
        return _CATEGORY_ICON_CACHE[cat]
    pm = QPixmap(18, 18)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.translate(9, 9)

    if cat == 'town':
        path = QPainterPath()
        for i in range(16):
            r = 7.5 if i % 2 == 0 else 4.5
            a = i * math.pi / 8
            pt = QPointF(r * math.cos(a), r * math.sin(a))
            if i == 0: path.moveTo(pt)
            else: path.lineTo(pt)
        path.closeSubpath()
        p.setPen(QPen(QColor('#0f172a'), 1.0))
        p.setBrush(QBrush(QColor('#2563eb')))
        p.drawPath(path)
        p.setBrush(QBrush(QColor('#ffffff')))
        p.drawEllipse(QRectF(-2.5, -2.5, 5, 5))
    elif cat == 'castle':
        pts = [
            QPointF(0, -8), QPointF(2, -3), QPointF(3, -3), QPointF(3, -2),
            QPointF(8, 0), QPointF(3, 2), QPointF(3, 3), QPointF(2, 3),
            QPointF(0, 8), QPointF(-2, 3), QPointF(-3, 3), QPointF(-3, 2),
            QPointF(-8, 0), QPointF(-3, -2), QPointF(-3, -3), QPointF(-2, -3)
        ]
        path = QPainterPath()
        path.moveTo(pts[0])
        for pt in pts[1:]: path.lineTo(pt)
        path.closeSubpath()
        p.setPen(QPen(QColor('#450a0a'), 1.0))
        p.setBrush(QBrush(QColor('#dc2626')))
        p.drawPath(path)
        p.setBrush(QBrush(QColor('#ffffff')))
        p.drawRect(QRectF(-2, -2, 4, 4))
    elif cat == 'village':
        p.setPen(QPen(QColor('#451a03'), 1.0))
        p.setBrush(QBrush(QColor('#d97706')))
        p.drawRect(QRectF(-4.5, -1, 9, 6))
        roof = QPainterPath()
        roof.moveTo(-6, -1); roof.lineTo(0, -7); roof.lineTo(6, -1); roof.closeSubpath()
        p.setBrush(QBrush(QColor('#b45309')))
        p.drawPath(roof)
    elif cat == 'bridge':
        p.rotate(45)
        p.setPen(QPen(QColor('#0f172a'), 1.0))
        p.setBrush(QBrush(QColor('#475569')))
        p.drawRoundedRect(QRectF(-7, -2.5, 14, 5), 1, 1)
        p.setPen(QPen(QColor('#1e293b'), 1.5))
        p.drawLine(-7, -4, -7, 4)
        p.drawLine(7, -4, 7, 4)
    elif cat == 'training_camp':
        tent = QPainterPath()
        tent.moveTo(0, -6); tent.lineTo(6, 5); tent.lineTo(-6, 5); tent.closeSubpath()
        p.setPen(QPen(QColor('#052e16'), 1.0))
        p.setBrush(QBrush(QColor('#16a34a')))
        p.drawPath(tent)
        p.setPen(QPen(QColor('#ffffff'), 1.0))
        p.drawLine(0, -6, 0, -9)
        p.setPen(Qt.NoPen); p.setBrush(QBrush(QColor('#dc2626')))
        flag = QPainterPath()
        flag.moveTo(0, -9); flag.lineTo(4, -7.5); flag.lineTo(0, -6); flag.closeSubpath()
        p.drawPath(flag)
    elif cat == 'special_scene':
        p.setPen(QPen(QColor('#3b0764'), 1.0))
        p.setBrush(QBrush(QColor('#7e22ce')))
        p.drawRect(QRectF(-5.5, 3, 11, 2.5))
        ped = QPainterPath()
        ped.moveTo(0, -6); ped.lineTo(6, -2); ped.lineTo(-6, -2); ped.closeSubpath()
        p.drawPath(ped)
        p.setBrush(QBrush(QColor('#c084fc')))
        p.drawRect(QRectF(-4.5, -2, 2, 5))
        p.drawRect(QRectF(-1, -2, 2, 5))
        p.drawRect(QRectF(2.5, -2, 2, 5))
    elif cat == 'spawn_point':
        p.setPen(QPen(QColor('#7c2d12'), 1.0))
        p.setBrush(QBrush(QColor('#ea580c')))
        d = QPainterPath()
        d.moveTo(0, -6); d.lineTo(6, 0); d.lineTo(0, 6); d.lineTo(-6, 0); d.closeSubpath()
        p.drawPath(d)
        p.setPen(QPen(QColor('#ffffff'), 1.2))
        p.drawLine(-4, -4, 4, 4); p.drawLine(4, -4, -4, 4)
    elif cat == 'hidden_system':
        p.setPen(QPen(QColor('#64748b'), 1.0, Qt.DashLine))
        p.setBrush(QBrush(QColor(100, 116, 139, 45)))
        p.drawEllipse(QRectF(-4, -4, 8, 8))
    p.end()
    icon = QIcon(pm)
    _CATEGORY_ICON_CACHE[cat] = icon
    return icon


def categorize_party(pid, raw_name):
    """
    智能识别 Warband 据点实体类型:
    1. bridge: 桥梁 (解析旋转角度朝向)
    2. spawn_point: 强盗与野怪刷新点
    3. town: 城镇 / 主要设防城市
    4. castle: 城堡 / 要塞 / 关卡
    5. village: 村庄 / 乡镇
    6. training_camp: 训练营 / 雇佣军营地
    7. special_scene: 原版遗留 / 彩蛋 / 特殊独立场景 (禅达/盐矿/四道口客栈等)
    8. hidden_system: 引擎底层占位/预留/伤亡标记/临时队伍 (带 {!} 默认隐匿)
    """
    pid_lower = pid.lower()
    name_lower = raw_name.lower()

    # 1. 桥梁 (优先判定：即使 txt 原名是 {!}1 也属于地图桥梁)
    if pid_lower.startswith('p_bridge') or '_bridge_' in pid_lower:
        return 'bridge'

    # 2. 野外强盗/野怪刷新点 (排除结束标记 p_spawn_points_end)
    if pid_lower == 'p_spawn_points_end':
        return 'hidden_system'
    if pid_lower.endswith('_spawn_point') or '_spawn_point_' in pid_lower or '_sp_' in pid_lower or pid_lower.startswith('p_spawn_point') or pid_lower.endswith('_sp'):
        return 'spawn_point'

    # 3. 城镇 (Town / City)
    if pid_lower.startswith('p_town') or '_city_' in pid_lower or pid_lower.startswith('p_hx_city'):
        return 'town'

    # 4. 城堡 / 要塞 (Castle / Fort / Pass)
    if pid_lower.startswith('p_castle') or pid_lower.startswith('p_fort') or '_castle_' in pid_lower or '_fort_' in pid_lower or pid_lower.startswith('p_hx_castle'):
        return 'castle'

    # 5. 村庄 (Village)
    if pid_lower.startswith('p_village') or '_village_' in pid_lower or pid_lower.startswith('p_hx_village'):
        return 'village'

    # 6. 训练营 (Training Camp)
    if pid_lower.startswith('p_training_ground') or 'training' in pid_lower or 'mercenary_camp' in name_lower:
        return 'training_camp'

    # 7. 原版遗留 / 彩蛋 / 特殊独立场景 / 玩家队伍起点
    special_ids = {
        'p_zendar', 'p_salt_mine', 'p_four_ways_inn', 'p_dhorak_keep',
        'p_test_scene', 'p_battlefields', 'p_ruins', 'p_main_party'
    }
    if pid_lower in special_ids or any(k in pid_lower for k in ('ancient', 'monument', 'relic', 'tourism', 'exploration', 'ferry')):
        return 'special_scene'

    # 8. 引擎系统内部项 / 预留位 / 临时队伍 (带 {!} 隐匿)
    if '{!}' in raw_name or pid_lower.startswith((
        'p_temp', 'p_camp_bandits', 'p_routed', 'p_collective',
        'p_main_party_backup', 'p_encountered', 'p_player_casualties',
        'p_enemy_casualties', 'p_ally_casualties', 'p_total_enemy'
    )):
        return 'hidden_system'

    # 默认兜底
    if '{!}' in raw_name:
        return 'hidden_system'
    return 'special_scene'


class PartyItem(QGraphicsItem):
    def __init__(self, party, editor):
        super().__init__()
        self.party = party
        self.editor = editor
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
        self._is_rotating = False

        self.hit_radius = 20  # 判定半径，保证跟手不钝感
        cat = party.get('category', 'special_scene')
        cat_info = CATEGORY_META.get(cat, CATEGORY_META['special_scene'])

        tip = f"【{cat_info['name']}】{party['display_name']}\nID: {party['id']}\n势力: {party.get('faction', 'none')}\n坐标: ({party['x']:.2f}, {party['y']:.2f})"
        if 'z' in party:
            tip += f"\n高度(Z): {party['z']:.2f}"
        if cat == 'bridge':
            deg = math.degrees(party.get('angle', 0.0))
            tip += f"\n朝向角度: {deg:.1f}° ({party.get('angle', 0.0):.4f} rad)\n[提示: 选中后按 Alt+滚轮 或左侧面板微调]"
        self.setToolTip(tip)

        self.label = QGraphicsTextItem(party['display_name'], self)
        self.label.setPos(self.hit_radius + 3, -11)
        self.label.setFont(QFont("Arial", 9, QFont.Bold))
        self.label.setDefaultTextColor(QColor('#0f172a'))

    def boundingRect(self):
        return QRectF(-self.hit_radius, -self.hit_radius, self.hit_radius * 2, self.hit_radius * 2)

    def paint(self, painter, option, widget):
        cat = self.party.get('category', 'special_scene')

        # 选中高亮光圈 (拿战战役金黄微光环)
        if self.isSelected():
            painter.setPen(QPen(QColor('#f59e0b'), 2.2, Qt.DashLine))
            painter.setBrush(QBrush(QColor(245, 158, 11, 45)))
            painter.drawEllipse(QRectF(-self.hit_radius + 2, -self.hit_radius + 2, (self.hit_radius - 2)*2, (self.hit_radius - 2)*2))

        # 1. 城镇: 中世纪带城墙城楼 (Medieval Walled City)
        if cat == 'town':
            # 外层城墙
            painter.setPen(QPen(QColor('#1e293b'), 1.8))
            painter.setBrush(QBrush(QColor('#64748b')))
            painter.drawRoundedRect(QRectF(-12, -10, 24, 20), 3, 3)
            
            # 城垛细节
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor('#1e293b')))
            for i in range(-10, 11, 4):
                painter.drawRect(QRectF(i, -11, 2, 2))
                painter.drawRect(QRectF(i, 9, 2, 2))
            
            # 内部主楼
            painter.setPen(QPen(QColor('#0f172a'), 1.0))
            painter.setBrush(QBrush(QColor('#2563eb')))
            painter.drawRect(QRectF(-6, -6, 12, 12))
            
            # 中心塔顶
            painter.setBrush(QBrush(QColor('#1e40af')))
            painter.drawRect(QRectF(-3, -3, 6, 6))

            # Z高度标签
            if 'z' in self.party:
                painter.setPen(QPen(QColor('#000000')))
                painter.setFont(QFont("Arial", 7))
                painter.drawText(QRectF(-15, 12, 30, 10), Qt.AlignCenter, f"Z:{self.party['z']:.0f}")

        # 2. 堡垒/要塞: 中世纪方形主楼据点 (Medieval Keep)
        elif cat == 'castle':
            # 基座
            painter.setPen(QPen(QColor('#292524'), 1.8))
            painter.setBrush(QBrush(QColor('#78716c')))
            painter.drawRect(QRectF(-10, -10, 20, 20))
            
            # 四个角塔
            painter.setBrush(QBrush(QColor('#44403c')))
            painter.drawRect(QRectF(-12, -12, 6, 6))
            painter.drawRect(QRectF(6, -12, 6, 6))
            painter.drawRect(QRectF(-12, 6, 6, 6))
            painter.drawRect(QRectF(6, 6, 6, 6))
            
            # 中心内城
            painter.setPen(QPen(QColor('#450a0a'), 1.0))
            painter.setBrush(QBrush(QColor('#dc2626')))
            painter.drawRect(QRectF(-5, -5, 10, 10))

            # Z高度标签
            if 'z' in self.party:
                painter.setPen(QPen(QColor('#000000')))
                painter.setFont(QFont("Arial", 7))
                painter.drawText(QRectF(-15, 12, 30, 10), Qt.AlignCenter, f"Z:{self.party['z']:.0f}")

        # 3. 村庄: 中世纪茅草顶农舍 (Medieval Thatched Cottage)
        elif cat == 'village':
            # 墙身
            painter.setPen(QPen(QColor('#451a03'), 1.5))
            painter.setBrush(QBrush(QColor('#fcd34d')))
            painter.drawRect(QRectF(-8, -2, 16, 9))
            
            # 木框架 (半木结构)
            painter.setPen(QPen(QColor('#451a03'), 1.0))
            painter.drawLine(-8, 2, 8, 2)
            painter.drawLine(0, -2, 0, 7)
            painter.drawLine(-4, 2, -4, 7)
            painter.drawLine(4, 2, 4, 7)

            # 茅草屋顶
            roof = QPainterPath()
            roof.moveTo(-10, -2)
            roof.lineTo(0, -11)
            roof.lineTo(10, -2)
            roof.closeSubpath()
            painter.setPen(QPen(QColor('#78350f'), 1.5))
            painter.setBrush(QBrush(QColor('#b45309')))
            painter.drawPath(roof)
            
            # 门
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor('#451a03')))
            painter.drawRect(QRectF(-2.5, 3, 5, 4))

        # 4. 桥梁: 石拱渡桥 (按游戏内角度旋转并显示前进朝向)
        elif cat == 'bridge':
            angle = self.party.get('angle', 0.0)
            angle_deg = -math.degrees(angle)
            painter.save()
            painter.rotate(angle_deg)

            # 桥面铺装
            painter.setPen(QPen(QColor('#0f172a'), 1.5))
            painter.setBrush(QBrush(QColor('#475569')))
            painter.drawRoundedRect(QRectF(-14, -5, 28, 10), 2, 2)

            # 两侧引桥与石质挡墙
            painter.setPen(QPen(QColor('#1e293b'), 2.2))
            painter.drawLine(-14, -7, -14, 7)
            painter.drawLine(14, -7, 14, 7)

            # 中心虚线路标
            painter.setPen(QPen(QColor('#f8fafc'), 1.0, Qt.DashLine))
            painter.drawLine(-11, 0, 11, 0)

            # 朝向引导箭头 (青蓝色，直观指示河流横跨与行进朝向)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor('#38bdf8')))
            arrow = QPainterPath()
            arrow.moveTo(15, 0)
            arrow.lineTo(9, -4)
            arrow.lineTo(10, 0)
            arrow.lineTo(9, 4)
            arrow.closeSubpath()
            painter.drawPath(arrow)

            painter.restore()

        # 5. 训练营: 中世纪圆形营帐 (Medieval Round Pavilion)
        elif cat == 'training_camp':
            # 圆形底座
            painter.setPen(QPen(QColor('#052e16'), 1.5))
            painter.setBrush(QBrush(QColor('#f8fafc')))
            painter.drawEllipse(QRectF(-9, -2, 18, 9))
            
            # 圆锥形屋顶
            tent = QPainterPath()
            tent.moveTo(0, -13)
            tent.lineTo(10, 2)
            tent.lineTo(-10, 2)
            tent.closeSubpath()
            painter.setBrush(QBrush(QColor('#16a34a')))
            painter.drawPath(tent)
            
            # 帐篷纹饰
            painter.setPen(QPen(QColor('#052e16'), 1.0))
            painter.drawLine(0, -13, 0, 2)
            painter.drawLine(0, -13, -5, 2)
            painter.drawLine(0, -13, 5, 2)

            # 顶部小红旗
            flag = QPainterPath()
            flag.moveTo(0, -13)
            flag.lineTo(0, -19)
            flag.lineTo(6, -16)
            flag.closeSubpath()
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor('#dc2626')))
            painter.drawPath(flag)

        # 6. 特殊独立场景/原版遗留/彩蛋: 古典神庙山墙多立克柱 (Classical Relic)
        elif cat == 'special_scene':
            painter.setPen(QPen(QColor('#3b0764'), 1.5))
            # 基座台阶
            painter.setBrush(QBrush(QColor('#7e22ce')))
            painter.drawRect(QRectF(-10, 6, 20, 4))
            # 三角山墙
            pediment = QPainterPath()
            pediment.moveTo(0, -11)
            pediment.lineTo(11, -4)
            pediment.lineTo(-11, -4)
            pediment.closeSubpath()
            painter.drawPath(pediment)
            # 3 根石柱
            painter.setBrush(QBrush(QColor('#c084fc')))
            painter.drawRect(QRectF(-8, -4, 3.5, 10))
            painter.drawRect(QRectF(-1.75, -4, 3.5, 10))
            painter.drawRect(QRectF(4.5, -4, 3.5, 10))

        # 7. 野怪与强盗刷新点: 警戒菱形与交叉利刃 (Danger Ambush Reticle)
        elif cat == 'spawn_point':
            painter.setPen(QPen(QColor('#7c2d12'), 1.5))
            painter.setBrush(QBrush(QColor('#ea580c')))
            diamond = QPainterPath()
            diamond.moveTo(0, -10)
            diamond.lineTo(10, 0)
            diamond.lineTo(0, 10)
            diamond.lineTo(-10, 0)
            diamond.closeSubpath()
            painter.drawPath(diamond)
            # 交叉刀锋
            painter.setPen(QPen(QColor('#ffffff'), 1.8))
            painter.drawLine(-7, -7, 7, 7)
            painter.drawLine(7, -7, -7, 7)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor('#fbbf24')))
            painter.drawEllipse(QRectF(-2.5, -2.5, 5, 5))

        # 8. 引擎底层系统隐匿项 (虚线齿轮占位符，仅在勾选显示时绘制)
        elif cat == 'hidden_system':
            painter.setPen(QPen(QColor('#64748b'), 1.2, Qt.DashLine))
            painter.setBrush(QBrush(QColor(100, 116, 139, 45)))
            painter.drawEllipse(QRectF(-7, -7, 14, 14))
            painter.setPen(QPen(QColor('#94a3b8'), 1.0))
            painter.drawLine(-4, 0, 4, 0)
            painter.drawLine(0, -4, 0, 4)

    def wheelEvent(self, event):
        # 桥梁专属滚轮旋转交互：Alt+滚轮 或 据点工具下直接滚轮
        if self.party.get('category') == 'bridge' and (event.modifiers() & Qt.AltModifier or self.editor.active_tool == 'party'):
            delta_deg = 5.0 if event.delta() > 0 else -5.0
            self.editor.rotate_selected_bridge(delta_deg)
            event.accept()
            return
        super().wheelEvent(event)

    def mousePressEvent(self, event):
        if self.editor.active_tool == 'party' and self.party.get('category') == 'bridge':
            dist = math.hypot(event.pos().x(), event.pos().y())
            # 点击在外圈 (10 - 20 半径之间) 则进行旋转
            if 10 < dist <= self.hit_radius:
                self._is_rotating = True
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._is_rotating:
            # 根据鼠标相对中心的角度计算朝向，+X方向为 0，顺时针为正 (通常 y 向下)
            angle_rad = math.atan2(event.pos().y(), event.pos().x())
            # map_editor 中 Y 轴朝上绘制桥梁是负角度，我们需要转为引擎顺时针角度 (Warband地图坐标通常是顺时针正)
            # 这里统一由 editor 控制角度计算
            self.party['angle'] = -angle_rad
            
            # 更新状态提示并重绘
            deg = math.degrees(self.party['angle'])
            self.editor.is_modified = True
            
            # 更新UI (若选中桥梁，会更新控制面板的 Label)
            if hasattr(self.editor, 'lbl_bridge_heading') and self.isSelected():
                self.editor.lbl_bridge_heading.setText(f"🌉 桥梁朝向: {deg:.1f}° ({-angle_rad:.3f} rad)")
            
            self.editor.update_status(f"旋转桥梁 {self.party['display_name']} 朝向至 {deg:.1f}°")
            self.update()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._is_rotating:
            self._is_rotating = False
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            if self.editor.active_tool != "party":
                return self.pos()
            self.editor.is_modified = True
            new_pos = value
            game_x, game_y = self.editor.pixel_to_game(new_pos.x(), new_pos.y())
            self.party['x'] = game_x
            self.party['y'] = game_y
            self.editor.update_status(f"移动据点 {self.party['display_name']} 至 ({game_x:.2f}, {game_y:.2f})")
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
        self.scene.selectionChanged.connect(self.on_map_selection_changed)
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

        sep_grid = QFrame()
        sep_grid.setFrameShape(QFrame.VLine)
        sep_grid.setStyleSheet("color: #cbd5e1; margin: 2px 4px;")
        right_layout.addWidget(sep_grid)

        self.btn_toggle_grid = QToolButton()
        self.btn_toggle_grid.setText("🌐 网格")
        self.btn_toggle_grid.setCheckable(True)
        self.btn_toggle_grid.setChecked(True)
        self.btn_toggle_grid.setToolTip("显示/隐藏地图坐标网格")
        self.btn_toggle_grid.toggled.connect(self.toggle_grid)
        right_layout.addWidget(self.btn_toggle_grid)
        
        self.top_toolbar.addWidget(right_pill)
        
        # =================== 左侧据点停靠板 ===================
        self.dock_parties = QDockWidget("据点列表 (Parties)", self)
        self.dock_parties.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        parties_widget = QWidget()
        parties_widget.setStyleSheet("""
            QWidget {
                background-color: #1e1e2e;
                color: #cdd6f4;
            }
            QLineEdit {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 4px;
                padding: 6px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 1px solid #89b4fa;
            }
            QComboBox {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 4px;
                padding: 5px 8px;
                font-size: 12px;
            }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background-color: #181825;
                color: #cdd6f4;
                selection-background-color: #45475a;
                selection-color: #89b4fa;
            }
            QListWidget {
                background-color: #181825;
                color: #cdd6f4;
                border: 1px solid #313244;
                border-radius: 6px;
                padding: 4px;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 6px 8px;
                border-radius: 4px;
                color: #cdd6f4;
                margin-bottom: 2px;
            }
            QListWidget::item:hover {
                background-color: #313244;
                color: #89b4fa;
            }
            QListWidget::item:selected {
                background-color: #1e66f5;
                color: #ffffff;
                font-weight: bold;
            }
        """)
        pl = QVBoxLayout(parties_widget)
        pl.setContentsMargins(6, 6, 6, 6)
        pl.setSpacing(6)

        # 搜索过滤框
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("🔍 过滤据点名称 / ID...")
        self.filter_input.textChanged.connect(self.apply_party_filters)
        pl.addWidget(self.filter_input)

        # 据点分类过滤器
        self.combo_category = QComboBox()
        self.combo_category.addItem("🎯 全部地点类型", "all")
        self.combo_category.addItem("🏰 城镇 (Town)", "town")
        self.combo_category.addItem("🛡️ 堡垒 (Castle)", "castle")
        self.combo_category.addItem("🌾 村庄 (Village)", "village")
        self.combo_category.addItem("🌉 桥梁 (Bridge - 旋转朝向)", "bridge")
        self.combo_category.addItem("⛺ 训练营 (Camp)", "training_camp")
        self.combo_category.addItem("🏛️ 遗留/特殊场景 (Relic)", "special_scene")
        self.combo_category.addItem("⚔️ 野怪刷新点 (Spawn)", "spawn_point")
        self.combo_category.currentIndexChanged.connect(self.apply_party_filters)
        pl.addWidget(self.combo_category)

        # 选项栏：隐匿项过滤与统计计数
        opt_layout = QHBoxLayout()
        self.cb_show_hidden = QCheckBox("显示 {!} 引擎项")
        self.cb_show_hidden.setChecked(False)
        self.cb_show_hidden.setToolTip("开启后可查看与编辑带 {!} 引擎占位、伤亡记录和系统标记（默认隐匿）")
        self.cb_show_hidden.setStyleSheet("QCheckBox { color: #a6adc8; font-size: 11px; }")
        self.cb_show_hidden.toggled.connect(self.on_toggle_show_hidden)
        opt_layout.addWidget(self.cb_show_hidden)

        self.lbl_party_stats = QLabel("共 0 个据点")
        self.lbl_party_stats.setStyleSheet("color: #6c7086; font-size: 11px;")
        self.lbl_party_stats.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        opt_layout.addWidget(self.lbl_party_stats)
        pl.addLayout(opt_layout)

        # 据点属性面板 (包含阵营、模型图标、桥梁旋转等)
        self.party_properties_panel = QFrame()
        self.party_properties_panel.setStyleSheet("""
            QFrame {
                background-color: #181825;
                border: 1px solid #45475a;
                border-radius: 6px;
                padding: 4px;
            }
            QLabel { color: #cdd6f4; font-size: 12px; }
            QPushButton {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 3px;
                padding: 3px 6px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45475a;
                color: #89b4fa;
            }
            QComboBox, QSpinBox {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 4px;
                padding: 3px 6px;
                font-size: 12px;
            }
        """)
        prop_layout = QVBoxLayout(self.party_properties_panel)
        prop_layout.setContentsMargins(4, 4, 4, 4)
        prop_layout.setSpacing(6)

        # 名称编辑
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("📝 名称:"))
        self.txt_properties_name = QLineEdit()
        self.txt_properties_name.textChanged.connect(self.on_party_name_changed)
        name_layout.addWidget(self.txt_properties_name)
        prop_layout.addLayout(name_layout)

        # 阵营选择
        fac_layout = QHBoxLayout()
        fac_layout.addWidget(QLabel("🏴 阵营:"))
        self.combo_properties_faction = QComboBox()
        # 实际选项会在 update_properties_panel 中动态填充
        self.combo_properties_faction.currentIndexChanged.connect(self.on_faction_changed)
        fac_layout.addWidget(self.combo_properties_faction)
        prop_layout.addLayout(fac_layout)

        # 地图图标 (Map Icon) 选择
        icon_layout = QHBoxLayout()
        icon_layout.addWidget(QLabel("🗿 图标 (Icon ID):"))
        self.combo_properties_icon = QComboBox()
        self.combo_properties_icon.currentIndexChanged.connect(self.on_icon_changed)
        icon_layout.addWidget(self.combo_properties_icon)
        prop_layout.addLayout(icon_layout)

        # 桥梁专属旋转调校
        self.bridge_control_widget = QWidget()
        b_box = QVBoxLayout(self.bridge_control_widget)
        b_box.setContentsMargins(0, 0, 0, 0)
        self.lbl_bridge_heading = QLabel("🌉 桥梁朝向: 0.0°")
        self.lbl_bridge_heading.setStyleSheet("color: #89dceb; font-weight: bold; font-size: 11px;")
        b_box.addWidget(self.lbl_bridge_heading)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(4)
        btn_m15 = QPushButton("-15°")
        btn_m15.clicked.connect(lambda: self.rotate_selected_bridge(-15))
        btn_row.addWidget(btn_m15)
        btn_m5 = QPushButton("-5°")
        btn_m5.clicked.connect(lambda: self.rotate_selected_bridge(-5))
        btn_row.addWidget(btn_m5)
        btn_p5 = QPushButton("+5°")
        btn_p5.clicked.connect(lambda: self.rotate_selected_bridge(5))
        btn_row.addWidget(btn_p5)
        btn_p15 = QPushButton("+15°")
        btn_p15.clicked.connect(lambda: self.rotate_selected_bridge(15))
        btn_row.addWidget(btn_p15)
        b_box.addLayout(btn_row)
        prop_layout.addWidget(self.bridge_control_widget)

        self.party_properties_panel.hide()
        pl.addWidget(self.party_properties_panel)

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
        
        # 集成到主工作区，省略独立的打开菜单项
        act_subdivide = menu.addAction("🕸 全局网格细分 (Subdivide Map)")
        act_subdivide.triggered.connect(self.subdivide_map)
        menu.addSeparator()
        
        act_save = menu.addAction("📄 保存文件 (Save All)\tCtrl+S")
        act_save.triggered.connect(self.save_all)
        
        act_export = menu.addAction("🖼 导出地图全景图 (PNG)\tCtrl+Shift+E")
        act_export.triggered.connect(self.export_image)

        act_export_chart = menu.addAction("📊 导出势力据点坐标分布图 (PNG)")
        act_export_chart.triggered.connect(self.export_coordinate_chart)

        act_export_csv = menu.addAction("📋 导出据点坐标数据 (CSV)")
        act_export_csv.triggered.connect(self.export_coordinate_csv)
        
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
            if 0 <= f_idx < len(self.faces):
                to_redo.append((f_idx, old_t, new_t))
                self.faces[f_idx]['terrain'] = old_t
                painter.setBrush(TERRAIN_COLORS.get(old_t, QColor(255, 0, 255)))
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
            if 0 <= f_idx < len(self.faces):
                to_undo.append((f_idx, old_t, new_t))
                self.faces[f_idx]['terrain'] = new_t
                painter.setBrush(TERRAIN_COLORS.get(new_t, QColor(255, 0, 255)))
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
        filepath, _ = QFileDialog.getSaveFileName(self, "导出地图全景图 (含经纬网格)", "world_map_grid.png", "PNG 图片 (*.png);;JPEG 图片 (*.jpg)")
        if not filepath:
            return

        # ---- 计算边距与画布尺寸 ----
        margin_left = 60      # 左侧留给 Y 轴刻度标签
        margin_right = 30
        margin_top = 44       # 顶部标题
        margin_bottom = 50    # 底部 X 轴刻度标签
        canvas_w = self.img_width + margin_left + margin_right
        canvas_h = self.img_height + margin_top + margin_bottom

        canvas = QImage(canvas_w, canvas_h, QImage.Format_ARGB32)
        canvas.fill(QColor("#0e0e12"))

        painter = QPainter(canvas)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)

        # ---- 绘制地形底图 ----
        painter.drawPixmap(margin_left, margin_top, self.map_pixmap)

        # ---- 坐标网格 overlay ----
        step = 20  # 游戏坐标间距
        min_gx = math.floor(self.min_x / step) * step
        max_gx = math.ceil(self.max_x / step) * step
        min_gy = math.floor(self.min_y / step) * step
        max_gy = math.ceil(self.max_y / step) * step

        # 次网格 (细线, 每 10 单位)
        sub_pen = QPen(QColor(255, 255, 255, 30), 1, Qt.DotLine)
        sub_step = 10
        sub_x = math.floor(self.min_x / sub_step) * sub_step
        while sub_x <= max_gx:
            if sub_x % step != 0:  # 跳过主线位置
                p_top = self.game_to_pixel_pt(sub_x, self.max_y)
                p_bot = self.game_to_pixel_pt(sub_x, self.min_y)
                painter.setPen(sub_pen)
                painter.drawLine(
                    QPointF(p_top.x() + margin_left, p_top.y() + margin_top),
                    QPointF(p_bot.x() + margin_left, p_bot.y() + margin_top)
                )
            sub_x += sub_step
        sub_y = math.floor(self.min_y / sub_step) * sub_step
        while sub_y <= max_gy:
            if sub_y % step != 0:
                p_left = self.game_to_pixel_pt(self.min_x, sub_y)
                p_right = self.game_to_pixel_pt(self.max_x, sub_y)
                painter.setPen(sub_pen)
                painter.drawLine(
                    QPointF(p_left.x() + margin_left, p_left.y() + margin_top),
                    QPointF(p_right.x() + margin_left, p_right.y() + margin_top)
                )
            sub_y += sub_step

        # 主网格 (实线, 每 step 单位)
        grid_pen = QPen(QColor(255, 255, 255, 70), 1, Qt.SolidLine)
        tick_font = QFont("Monospace", 9, QFont.Bold)
        painter.setFont(tick_font)

        # 纵向经线 (X = const) + 底部 X 轴刻度
        curr_x = min_gx
        while curr_x <= max_gx:
            p_top = self.game_to_pixel_pt(curr_x, self.max_y)
            p_bot = self.game_to_pixel_pt(curr_x, self.min_y)
            px = p_top.x() + margin_left

            # 网格线
            painter.setPen(grid_pen)
            painter.drawLine(QPointF(px, margin_top), QPointF(px, margin_top + self.img_height))

            # 底部刻度标签
            painter.setPen(QColor(200, 200, 200, 220))
            label = str(int(curr_x))
            fm = QFontMetrics(tick_font)
            tw = fm.horizontalAdvance(label)
            painter.drawText(
                QRectF(px - tw / 2, margin_top + self.img_height + 6, tw + 4, 20),
                Qt.AlignCenter, label
            )

            # 顶部短刻度线
            painter.setPen(QPen(QColor(255, 255, 255, 100), 1))
            painter.drawLine(QPointF(px, margin_top - 4), QPointF(px, margin_top))

            curr_x += step

        # 横向纬线 (Y = const) + 左侧 Y 轴刻度
        curr_y = min_gy
        while curr_y <= max_gy:
            p_left = self.game_to_pixel_pt(self.min_x, curr_y)
            py = p_left.y() + margin_top

            # 网格线
            painter.setPen(grid_pen)
            painter.drawLine(QPointF(margin_left, py), QPointF(margin_left + self.img_width, py))

            # 左侧刻度标签
            painter.setPen(QColor(200, 200, 200, 220))
            label = str(int(curr_y))
            painter.drawText(
                QRectF(2, py - 10, margin_left - 6, 20),
                Qt.AlignRight | Qt.AlignVCenter, label
            )

            # 左侧短刻度线
            painter.setPen(QPen(QColor(255, 255, 255, 100), 1))
            painter.drawLine(QPointF(margin_left - 4, py), QPointF(margin_left, py))

            curr_y += step

        # ---- 地图边框 ----
        painter.setPen(QPen(QColor(255, 255, 255, 120), 1.5))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(QRectF(margin_left, margin_top, self.img_width, self.img_height))

        # ---- 据点标记 ----
        show_hidden = self.cb_show_hidden.isChecked() if hasattr(self, 'cb_show_hidden') else False
        marker_font = QFont("Arial", 7, QFont.Bold)
        painter.setFont(marker_font)

        for party in self.parties:
            cat = party.get('category', 'special_scene')
            if cat == 'hidden_system' and not show_hidden:
                continue
            cat_info = CATEGORY_META.get(cat, CATEGORY_META['special_scene'])
            color = QColor(cat_info['color'])

            pt = self.game_to_pixel_pt(party['x'], party['y'])
            px = pt.x() + margin_left
            py = pt.y() + margin_top

            # 外圈光晕
            painter.setPen(Qt.NoPen)
            glow = QColor(color)
            glow.setAlpha(60)
            painter.setBrush(glow)
            painter.drawEllipse(QPointF(px, py), 6, 6)

            # 实心标记点
            painter.setPen(QPen(QColor(0, 0, 0, 180), 1))
            painter.setBrush(color)
            painter.drawEllipse(QPointF(px, py), 3.5, 3.5)

            # 名称标签 (仅城镇/堡垒/村庄)
            if cat in ('town', 'castle', 'village'):
                painter.setPen(QColor(255, 255, 255, 200))
                painter.drawText(int(px + 6), int(py + 3), party['display_name'])

        # ---- 轴标题 ----
        title_font = QFont("sans-serif", 11, QFont.Bold)
        painter.setFont(title_font)
        painter.setPen(QColor("#e4e4e7"))

        # 底部 X 轴标题
        painter.drawText(
            QRectF(margin_left, canvas_h - 22, self.img_width, 20),
            Qt.AlignCenter, "X (东 → 西)"
        )

        # 左侧 Y 轴标题 (旋转绘制)
        painter.save()
        painter.translate(14, margin_top + self.img_height / 2)
        painter.rotate(-90)
        painter.drawText(QRectF(-80, -10, 160, 20), Qt.AlignCenter, "Y (南 → 北)")
        painter.restore()

        # 顶部标题
        painter.setFont(QFont("sans-serif", 12, QFont.Bold))
        painter.setPen(QColor("#a1a1aa"))
        painter.drawText(
            QRectF(margin_left, 4, self.img_width, margin_top - 6),
            Qt.AlignCenter,
            f"Warband Map — 坐标网格 [{int(self.min_x)},{int(self.min_y)}] → [{int(self.max_x)},{int(self.max_y)}]  (step={step})"
        )

        painter.end()
        canvas.save(filepath)
        self.update_status(f"地图已导出至: {filepath}")
        QMessageBox.information(self, "导出成功", f"含坐标经纬网格的地图已成功导出到:\n{filepath}")

    def toggle_grid(self, checked):
        if hasattr(self, 'grid_group') and self.grid_group:
            self.grid_group.setVisible(checked)
            self.update_status(f"坐标网格: {'显示' if checked else '隐藏'}")

    def draw_grid(self):
        if not hasattr(self, 'vertices') or not self.vertices:
            return
        if hasattr(self, 'grid_group') and self.grid_group:
            if self.grid_group.scene():
                self.scene.removeItem(self.grid_group)

        self.grid_group = QGraphicsItemGroup()
        self.grid_group.setZValue(1)

        step = 20
        min_gx = math.floor(self.min_x / step) * step
        max_gx = math.ceil(self.max_x / step) * step
        min_gy = math.floor(self.min_y / step) * step
        max_gy = math.ceil(self.max_y / step) * step

        pen = QPen(QColor(255, 255, 255, 55), 1, Qt.DashLine)
        font = QFont("Monospace", 8, QFont.Bold)

        # 纵向经线 (X = const)
        curr_x = min_gx
        while curr_x <= max_gx:
            p_top = self.game_to_pixel_pt(curr_x, self.max_y)
            p_bot = self.game_to_pixel_pt(curr_x, self.min_y)
            line = QGraphicsLineItem(p_top.x(), p_top.y(), p_bot.x(), p_bot.y())
            line.setPen(pen)
            self.grid_group.addToGroup(line)

            txt = QGraphicsSimpleTextItem(f"X:{int(curr_x)}")
            txt.setFont(font)
            txt.setBrush(QBrush(QColor(255, 255, 255, 175)))
            txt.setPos(p_top.x() + 2, p_top.y() + 4)
            self.grid_group.addToGroup(txt)
            curr_x += step

        # 横向纬线 (Y = const)
        curr_y = min_gy
        while curr_y <= max_gy:
            p_left = self.game_to_pixel_pt(self.min_x, curr_y)
            p_right = self.game_to_pixel_pt(self.max_x, curr_y)
            line = QGraphicsLineItem(p_left.x(), p_left.y(), p_right.x(), p_right.y())
            line.setPen(pen)
            self.grid_group.addToGroup(line)

            txt = QGraphicsSimpleTextItem(f"Y:{int(curr_y)}")
            txt.setFont(font)
            txt.setBrush(QBrush(QColor(255, 255, 255, 175)))
            txt.setPos(p_left.x() + 4, p_left.y() - 14)
            self.grid_group.addToGroup(txt)
            curr_y += step

        self.scene.addItem(self.grid_group)
        is_visible = getattr(self, 'btn_toggle_grid', None) and self.btn_toggle_grid.isChecked()
        self.grid_group.setVisible(bool(is_visible))

    def export_coordinate_chart(self):
        if not self.parties:
            QMessageBox.warning(self, "提示", "尚未加载据点数据，无法生成坐标图。")
            return

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "导出势力据点坐标分布图",
            "faction_territories_coordinates.png",
            "PNG 图片 (*.png)"
        )
        if not filepath:
            return

        FACTION_COLORS = {
            "fac_kingdom_1": (QColor("#3b82f6"), "France"),
            "fac_kingdom_2": (QColor("#f97316"), "Britain"),
            "fac_kingdom_3": (QColor("#10b981"), "Netherlands"),
            "fac_kingdom_4": (QColor("#eab308"), "Prussia"),
            "fac_kingdom_5": (QColor("#ec4899"), "German_Alliance"),
            "fac_kingdom_6": (QColor("#22c55e"), "Habsburg"),
        }
        FALLBACK_PALETTE = [
            QColor("#38bdf8"), QColor("#fb923c"), QColor("#34d399"),
            QColor("#facc15"), QColor("#f472b6"), QColor("#4ade80"),
            QColor("#a78bfa"), QColor("#2dd4bf"), QColor("#fb7185")
        ]

        present_factions = sorted(list({p['faction'] for p in self.parties if p.get('faction')}))
        faction_map = {}
        for idx, fac in enumerate(present_factions):
            if fac in FACTION_COLORS:
                color, name = FACTION_COLORS[fac]
            else:
                color = FALLBACK_PALETTE[idx % len(FALLBACK_PALETTE)]
                name = fac.replace("fac_", "").replace("_", " ").title()
            faction_map[fac] = (color, name)

        xs = [p['x'] for p in self.parties]
        ys = [p['y'] for p in self.parties]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        step = 20
        plot_min_x = math.floor((min_x - 10) / step) * step
        plot_max_x = math.ceil((max_x + 10) / step) * step
        plot_min_y = math.floor((min_y - 10) / step) * step
        plot_max_y = math.ceil((max_y + 10) / step) * step

        img_w, img_h = 1300, 680
        image = QImage(img_w, img_h, QImage.Format_ARGB32)
        image.fill(QColor("#111215"))

        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)

        # 主卡片外框
        card_rect = QRectF(24, 20, img_w - 48, img_h - 40)
        painter.setPen(QPen(QColor("#27272a"), 1.5))
        painter.setBrush(QColor("#18181b"))
        painter.drawRoundedRect(card_rect, 14, 14)

        # 标题与副标题
        painter.setFont(QFont("sans-serif", 15, QFont.Bold))
        painter.setPen(QColor("#f4f4f5"))
        painter.drawText(int(card_rect.left() + 24), int(card_rect.top() + 38), "1815 Mod — redesigned faction territories (each cluster now contiguous)")

        painter.setFont(QFont("sans-serif", 10))
        painter.setPen(QColor("#a1a1aa"))
        painter.drawText(int(card_rect.left() + 24), int(card_rect.top() + 64), "south - north by west - east")

        plot_l = card_rect.left() + 60
        plot_t = card_rect.top() + 90
        plot_r = card_rect.right() - 40
        plot_b = card_rect.bottom() - 80
        plot_w = plot_r - plot_l
        plot_h = plot_b - plot_t

        def to_plot(gx, gy):
            px = plot_l + (gx - plot_min_x) / (plot_max_x - plot_min_x) * plot_w
            py = plot_b - (gy - plot_min_y) / (plot_max_y - plot_min_y) * plot_h
            return px, py

        # 网格与坐标轴
        grid_pen = QPen(QColor("#27272a"), 1, Qt.SolidLine)
        painter.setFont(QFont("sans-serif", 9))

        cx = plot_min_x
        while cx <= plot_max_x:
            px, _ = to_plot(cx, 0)
            painter.setPen(grid_pen)
            painter.drawLine(QPointF(px, plot_t), QPointF(px, plot_b))
            painter.setPen(QColor("#71717a"))
            painter.drawText(QRectF(px - 30, plot_b + 6, 60, 20), Qt.AlignCenter, f"{int(cx)}")
            cx += step

        cy = plot_min_y
        while cy <= plot_max_y:
            _, py = to_plot(0, cy)
            painter.setPen(grid_pen)
            painter.drawLine(QPointF(plot_l, py), QPointF(plot_r, py))
            painter.setPen(QColor("#71717a"))
            painter.drawText(QRectF(plot_l - 45, py - 10, 36, 20), Qt.AlignRight | Qt.AlignVCenter, f"{int(cy)}")
            cy += step

        # 绘制据点散点
        for p in self.parties:
            fac = p.get('faction', '')
            color, _ = faction_map.get(fac, (QColor("#94a3b8"), fac))
            px, py = to_plot(p['x'], p['y'])

            painter.setPen(QPen(QColor(255, 255, 255, 50), 1.5))
            painter.setBrush(color)
            painter.drawEllipse(QPointF(px, py), 5.5, 5.5)

        # 底部图例
        leg_x = plot_l
        leg_y = card_rect.bottom() - 32
        painter.setFont(QFont("sans-serif", 10, QFont.Bold))

        for fac, (color, name) in faction_map.items():
            painter.setPen(Qt.NoPen)
            painter.setBrush(color)
            painter.drawEllipse(QPointF(leg_x + 5, leg_y - 4), 4.5, 4.5)

            painter.setPen(QColor("#d4d4d8"))
            painter.drawText(int(leg_x + 16), int(leg_y), name)

            metrics = QFontMetrics(painter.font())
            text_w = metrics.horizontalAdvance(name)
            leg_x += text_w + 32
            if leg_x > plot_r - 80:
                leg_x = plot_l
                leg_y += 20

        painter.end()
        image.save(filepath)
        QMessageBox.information(self, "导出成功", f"势力据点坐标分布图已保存至:\n{filepath}")

    def export_coordinate_csv(self):
        if not self.parties:
            QMessageBox.warning(self, "提示", "尚未加载据点数据，无法导出。")
            return

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "导出据点坐标数据",
            "parties_coordinates.csv",
            "CSV 表格 (*.csv)"
        )
        if not filepath:
            return

        import csv
        with open(filepath, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "name", "display_name", "category", "faction", "x", "y", "angle_deg", "angle_rad"])
            for p in self.parties:
                deg = math.degrees(p.get('angle', 0.0))
                writer.writerow([
                    p['id'], p['name'], p.get('display_name', p['name']),
                    p.get('category', 'special_scene'), p.get('faction', ''),
                    p['x'], p['y'], f"{deg:.2f}", f"{p.get('angle', 0.0):.6f}"
                ])

        QMessageBox.information(self, "导出成功", f"据点坐标数据已成功导出至:\n{filepath}")

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

    def load_maptxt(self, filepath=None):
        if not filepath:
            filepath, _ = QFileDialog.getOpenFileName(self, "打开 map.txt", ".", "Text Files (*.txt)")
        if not filepath: return
        self.status_bar.showMessage("正在解析原生 map.txt 几何数据...")
        QApplication.processEvents()
        
        with open(filepath, 'r') as f:
            lines = f.readlines()
            
        self.vertices = []
        self.faces = []
        self.undo_stack.clear()
        self.redo_stack.clear()
        
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
        self.draw_grid()
        self.draw_parties()
        
    def load_parties(self, filepath=None):
        if not filepath:
            filepath, _ = QFileDialog.getOpenFileName(self, "打开 parties.txt", ".", "Text Files (*.txt)")
        if not filepath: return
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            self.original_parties_lines = f.readlines()
        # 尝试读取同级目录下的 factions.txt
        self.faction_names = {}
        import os
        fac_path = os.path.join(os.path.dirname(filepath), 'factions.txt')
        if os.path.exists(fac_path):
            try:
                with open(fac_path, 'r', encoding='utf-8', errors='ignore') as f:
                    fac_lines = f.readlines()
                    fac_idx = 0
                    for i in range(2, len(fac_lines), 2):
                        if i < len(fac_lines):
                            f_parts = fac_lines[i].strip().split()
                            if len(f_parts) >= 3:
                                name = f_parts[2].replace('_', ' ').replace('{!}', '')
                                self.faction_names[str(fac_idx)] = name
                            fac_idx += 1
            except Exception as e:
                print("解析 factions.txt 失败:", e)

        # [INJECTED] Read scripts.txt
        self.scripts_filepath = os.path.join(os.path.dirname(filepath), "scripts.txt")
        self.script_ops = []
        self.party_faction_indices = {}
        if os.path.exists(self.scripts_filepath):
            with open(self.scripts_filepath, 'r') as f:
                self.scripts_lines = f.readlines()
            if len(self.scripts_lines) > 3:
                self.script_ops = self.scripts_lines[3].strip().split()
                for k in range(len(self.script_ops)):
                    if self.script_ops[k] == '1' and k+4 < len(self.script_ops):
                        if self.script_ops[k+1] == '3' and self.script_ops[k+2].startswith('93674872249306'):
                            c_val = int(self.script_ops[k+3])
                            if c_val >= 648518346341351424:
                                p_idx = c_val - 648518346341351424
                                self.party_faction_indices[p_idx] = k+4

                
        # 尝试读取同级目录下的 map_icons.txt
        self.icon_names = {}
        icon_path = os.path.join(os.path.dirname(filepath), 'map_icons.txt')
        if os.path.exists(icon_path):
            try:
                with open(icon_path, 'r', encoding='utf-8', errors='ignore') as f:
                    icon_lines = f.readlines()
                    icon_idx = 0
                    for line in icon_lines[2:]:
                        line = line.strip()
                        if not line: continue
                        i_parts = line.split()
                        if len(i_parts) >= 3:
                            self.icon_names[icon_idx] = i_parts[0]
                            icon_idx += 1
            except Exception as e:
                print("解析 map_icons.txt 失败:", e)

        self.parties = []

        for i in range(2, len(self.original_parties_lines), 2):
            if i >= len(self.original_parties_lines) - 1: break
            line1 = self.original_parties_lines[i]
            parts = line1.strip().split()
            if len(parts) < 20: continue

            # 读取第二行朝向角度 (弧度)
            angle = 0.0
            if i + 1 < len(self.original_parties_lines):
                try:
                    angle = float(self.original_parties_lines[i + 1].strip())
                except ValueError:
                    angle = 0.0

            raw_id = parts[3]
            raw_name = parts[4]
            cat = categorize_party(raw_id, raw_name)

            # 生成人性化显示名称
            if cat == 'bridge':
                clean_num = raw_name.replace('{!}', '').strip()
                display_name = f"桥梁 #{clean_num}" if clean_num.isdigit() else (f"桥梁 {clean_num}" if clean_num else f"桥梁 ({raw_id})")
            elif cat == 'spawn_point':
                clean_sp = raw_name.replace('{!}', '').replace('_spawn_point', '').replace('_sp', '').replace('_', ' ').strip()
                display_name = f"刷新点: {clean_sp}" if clean_sp else f"刷新点 ({raw_id})"
            elif cat == 'hidden_system':
                display_name = f"[隐匿] {raw_name}"
            else:
                display_name = raw_name.replace('_', ' ')

            # 解析图标 ID (flags 的低 8 位)
            flags = int(parts[5]) if len(parts) > 5 and parts[5].isdigit() else 0
            icon_id = flags & 0xFF

            def safe_float(s):
                try:
                    return float(s)
                except ValueError:
                    match = re.match(r'^-?\d+(?:\.\d+)?', str(s))
                    return float(match.group(0)) if match else 0.0


            p_idx = (i - 2) // 2
            true_faction_id = parts[8]
            if p_idx in self.party_faction_indices:
                fac_val = self.script_ops[self.party_faction_indices[p_idx]]
                if fac_val.startswith("432345564227567"):
                    true_faction_id = fac_val.replace("432345564227567", "")

            p = {
                'index': i,
                'id': raw_id,
                'name': raw_name,
                'display_name': display_name,
                'category': cat,
                'angle': angle,
                'faction_id': true_faction_id,
                'faction_name': self.faction_names.get(true_faction_id, f"Faction {true_faction_id}"),
                'p_idx': p_idx,

                'icon_id': icon_id,
                'flags': flags,
                'x': safe_float(parts[14]),
                'y': safe_float(parts[15]),
                'z': safe_float(parts[16]) if len(parts) > 16 else 0.0,
                'parts': parts
            }
            self.parties.append(p)

        self.parties_filepath = filepath
        self.update_party_list()
        self.draw_parties()
        hidden_count = sum(1 for p in self.parties if p.get('category') == 'hidden_system')
        self.status_bar.showMessage(f"成功加载 {len(self.parties)} 个据点 (已默认隐匿 {hidden_count} 个引擎系统项)。")

    def apply_party_filters(self):
        self.update_party_list()
        self.draw_parties()

    def on_toggle_show_hidden(self, checked):
        self.apply_party_filters()

    def update_party_list(self):
        self.list_widget.clear()
        show_hidden = self.cb_show_hidden.isChecked() if hasattr(self, 'cb_show_hidden') else False
        selected_cat = self.combo_category.currentData() if hasattr(self, 'combo_category') else 'all'
        search_text = self.filter_input.text().lower().strip() if hasattr(self, 'filter_input') else ''

        hidden_total = 0
        visible_count = 0

        for p in self.parties:
            cat = p.get('category', 'special_scene')
            if cat == 'hidden_system':
                hidden_total += 1

            # 隐匿项过滤
            if cat == 'hidden_system' and not show_hidden:
                continue
            # 分类过滤
            if selected_cat != 'all' and cat != selected_cat:
                continue
            # 搜索文本过滤
            full_str = f"{p['display_name']} {p['id']} {p['name']}".lower()
            if search_text and (search_text not in full_str):
                continue

            visible_count += 1
            item = QListWidgetItem(f"{p['display_name']} ({p['id']})")
            item.setData(Qt.UserRole, p['id'])

            # 赋予 18x18 拿战风格迷你矢量图标
            icon = create_category_icon(cat)
            if icon:
                item.setIcon(icon)

            # 颜色分级显示
            if cat == 'hidden_system':
                item.setForeground(QColor('#6c7086'))
            elif cat == 'town':
                item.setForeground(QColor('#89b4fa'))
            elif cat == 'castle':
                item.setForeground(QColor('#f38ba8'))
            elif cat == 'village':
                item.setForeground(QColor('#fab387'))
            elif cat == 'bridge':
                item.setForeground(QColor('#94e2d5'))
            elif cat == 'training_camp':
                item.setForeground(QColor('#a6e3a1'))
            elif cat == 'special_scene':
                item.setForeground(QColor('#cba6f7'))
            elif cat == 'spawn_point':
                item.setForeground(QColor('#f9e2af'))

            self.list_widget.addItem(item)

        if hasattr(self, 'lbl_party_stats'):
            self.lbl_party_stats.setText(f"显示: {visible_count} / {len(self.parties)} (隐匿 {hidden_total})")

    def draw_parties(self):
        for item in self.party_items.values():
            self.scene.removeItem(item)
        self.party_items.clear()

        show_hidden = self.cb_show_hidden.isChecked() if hasattr(self, 'cb_show_hidden') else False
        selected_cat = self.combo_category.currentData() if hasattr(self, 'combo_category') else 'all'
        search_text = self.filter_input.text().lower().strip() if hasattr(self, 'filter_input') else ''

        for party in self.parties:
            cat = party.get('category', 'special_scene')
            if cat == 'hidden_system' and not show_hidden:
                continue
            if selected_cat != 'all' and cat != selected_cat:
                continue
            if search_text:
                full_str = f"{party['display_name']} {party['id']} {party['name']}".lower()
                if search_text not in full_str:
                    continue

            item = PartyItem(party, self)
            item.setPos(self.game_to_pixel_pt(party['x'], party['y']))
            item.setFlag(QGraphicsItem.ItemIsMovable, self.active_tool == "party")
            self.scene.addItem(item)
            self.party_items[party['id']] = item

    def rotate_selected_bridge(self, delta_deg):
        # 旋转当前选中的桥梁朝向
        target_item = None
        for it in self.scene.selectedItems():
            if isinstance(it, PartyItem) and it.party.get('category') == 'bridge':
                target_item = it
                break

        if not target_item and hasattr(self, 'current_selected_party') and self.current_selected_party:
            if self.current_selected_party.get('category') == 'bridge':
                target_item = self.party_items.get(self.current_selected_party['id'])

        if target_item:
            p = target_item.party
            delta_rad = math.radians(delta_deg)
            p['angle'] = (p.get('angle', 0.0) + delta_rad) % (2 * math.pi)
            target_item.update()
            self.is_modified = True
            deg = math.degrees(p['angle'])
            self.lbl_bridge_heading.setText(f"🌉 桥梁朝向: {deg:.1f}° ({p['angle']:.3f} rad)")
            self.update_status(f"已旋转桥梁 {p['display_name']} 朝向至 {deg:.1f}° ({p['angle']:.4f} rad)")

    def on_party_name_changed(self, text):
        if not hasattr(self, 'current_selected_party') or not self.current_selected_party:
            return
        new_name = text.strip()
        if not new_name:
            return
        self.current_selected_party['display_name'] = new_name
        self.current_selected_party['parts'][4] = new_name.replace(' ', '_')
        self.is_modified = True
        
        target_item = self.party_items.get(self.current_selected_party['id'])
        if target_item:
            target_item.update()
            target_item.setToolTip(f"【{CATEGORY_META.get(self.current_selected_party.get('category', 'special_scene'), CATEGORY_META['special_scene'])['name']}】{self.current_selected_party['display_name']}\nID: {self.current_selected_party['id']}\n势力: {self.current_selected_party.get('faction_name', '未知')}\n坐标: ({self.current_selected_party['x']:.2f}, {self.current_selected_party['y']:.2f})")
            
        # 同步左侧列表名字
        for i in range(self.list_widget.count()):
            l_item = self.list_widget.item(i)
            if l_item.data(Qt.UserRole) == self.current_selected_party['id']:
                l_item.setText(f"{new_name} ({self.current_selected_party['id']})")
                break

    def on_faction_changed(self, index):
        if not hasattr(self, 'current_selected_party') or not self.current_selected_party:
            return
        faction_id = self.combo_properties_faction.itemData(index)
        faction_name = self.combo_properties_faction.currentText()
        if faction_id and self.current_selected_party.get('faction_id') != faction_id:
            self.current_selected_party['faction_id'] = faction_id
            self.current_selected_party['faction_name'] = faction_name
            self.current_selected_party['parts'][8] = faction_id

            # [INJECTED] Update scripts
            p_idx = self.current_selected_party.get('p_idx')
            if hasattr(self, 'party_faction_indices') and p_idx in self.party_faction_indices:
                fac_token_idx = self.party_faction_indices[p_idx]
                self.script_ops[fac_token_idx] = "432345564227567" + faction_id

            self.is_modified = True
            self.update_status(f"已修改据点 {self.current_selected_party['display_name']} 阵营为 {faction_name}")
            # Refresh party visual
            target_item = self.party_items.get(self.current_selected_party['id'])
            if target_item:
                target_item.update()
                target_item.setToolTip(f"【{CATEGORY_META.get(self.current_selected_party.get('category', 'special_scene'), CATEGORY_META['special_scene'])['name']}】{self.current_selected_party['display_name']}\nID: {self.current_selected_party['id']}\n势力: {faction_name}\n坐标: ({self.current_selected_party['x']:.2f}, {self.current_selected_party['y']:.2f})")


    def on_icon_changed(self, index):
        if not hasattr(self, 'current_selected_party') or not self.current_selected_party:
            return
        icon_id = self.combo_properties_icon.itemData(index)
        icon_name = self.combo_properties_icon.currentText()
        if icon_id is not None and self.current_selected_party.get('icon_id') != icon_id:
            self.current_selected_party['icon_id'] = icon_id
            flags = self.current_selected_party.get('flags', 0)
            new_flags = (flags & ~0xFF) | icon_id
            self.current_selected_party['flags'] = new_flags
            self.current_selected_party['parts'][5] = str(new_flags)
            self.is_modified = True
            self.update_status(f"已修改据点 {self.current_selected_party['display_name']} 图标为 {icon_name}")


    def update_properties_panel(self):
        if not hasattr(self, 'current_selected_party') or not self.current_selected_party:
            self.party_properties_panel.hide()
            return

        self.party_properties_panel.show()
        p = self.current_selected_party

        # 更新名称
        self.txt_properties_name.blockSignals(True)
        self.txt_properties_name.setText(p.get('display_name', ''))
        self.txt_properties_name.blockSignals(False)

        # 更新阵营列表并选中当前
        self.combo_properties_faction.blockSignals(True)
        self.combo_properties_faction.clear()
        
        # 收集所有出现的 faction_id，以及从 factions.txt 解析到的所有 faction
        all_fac_ids = set({party.get('faction_id', '0') for party in self.parties})
        if hasattr(self, 'faction_names'):
            all_fac_ids.update(self.faction_names.keys())
            
        all_fac_ids_sorted = sorted(list(all_fac_ids), key=lambda x: int(x) if str(x).isdigit() else 0)
        
        for fid in all_fac_ids_sorted:
            if hasattr(self, 'faction_names'):
                fname = self.faction_names.get(str(fid), f"Faction {fid}")
            else:
                fname = f"Faction {fid}"
            self.combo_properties_faction.addItem(f"{fname} (ID:{fid})", str(fid))
            
        current_fid = p.get('faction_id', '0')
        idx = self.combo_properties_faction.findData(current_fid)
        if idx >= 0:
            self.combo_properties_faction.setCurrentIndex(idx)
        self.combo_properties_faction.blockSignals(False)

        # 更新图标
        self.combo_properties_icon.blockSignals(True)
        self.combo_properties_icon.clear()
        
        # 收集所有出现的 icon_id，以及从 map_icons.txt 解析到的所有 icon
        all_icon_ids = set({party.get('icon_id', 0) for party in self.parties})
        if hasattr(self, 'icon_names'):
            all_icon_ids.update(self.icon_names.keys())
            
        cat = p.get('category', '')
        recommended_icons = []
        other_icons = []
        
        for iid in sorted(list(all_icon_ids)):
            if hasattr(self, 'icon_names') and iid in self.icon_names:
                iname = self.icon_names[iid]
            else:
                iname = f"Icon {iid}"
                
            is_rec = False
            iname_lower = iname.lower()
            
            # 根据当前类型智能推荐图标
            if cat == 'town' and ('town' in iname_lower or 'city' in iname_lower):
                is_rec = True
            elif cat == 'castle' and 'castle' in iname_lower:
                is_rec = True
            elif cat == 'village' and 'village' in iname_lower:
                is_rec = True
            elif cat == 'bridge' and 'bridge' in iname_lower:
                is_rec = True
            elif cat == 'spawn_point' and ('player' in iname_lower or 'knight' in iname_lower):
                is_rec = True
                
            if is_rec:
                recommended_icons.append((iid, iname))
            else:
                other_icons.append((iid, iname))

        # 先添加推荐图标，再添加其他图标
        for iid, iname in recommended_icons:
            self.combo_properties_icon.addItem(f"★ {iname} (ID:{iid})", iid)
            
        if recommended_icons and other_icons:
            self.combo_properties_icon.insertSeparator(self.combo_properties_icon.count())
            
        for iid, iname in other_icons:
            self.combo_properties_icon.addItem(f"{iname} (ID:{iid})", iid)
            
        current_iid = p.get('icon_id', 0)
        idx = self.combo_properties_icon.findData(current_iid)
        if idx >= 0:
            self.combo_properties_icon.setCurrentIndex(idx)
        self.combo_properties_icon.blockSignals(False)

        # 桥梁专属控件
        if p.get('category') == 'bridge':
            self.bridge_control_widget.show()
            deg = math.degrees(p.get('angle', 0.0))
            self.lbl_bridge_heading.setText(f"🌉 桥梁朝向: {deg:.1f}° ({p.get('angle', 0.0):.3f} rad)")
        else:
            self.bridge_control_widget.hide()

    def on_map_selection_changed(self):
        items = self.scene.selectedItems()
        target = None
        for it in items:
            if isinstance(it, PartyItem):
                target = it
                break

        if target:
            self.current_selected_party = target.party
            self.update_properties_panel()

            # 同步高亮左侧列表对应项
            pid = target.party['id']
            for i in range(self.list_widget.count()):
                l_item = self.list_widget.item(i)
                if l_item.data(Qt.UserRole) == pid:
                    self.list_widget.blockSignals(True)
                    self.list_widget.setCurrentItem(l_item)
                    self.list_widget.blockSignals(False)
                    break
        else:
            self.current_selected_party = None
            self.update_properties_panel()

    def on_list_click(self, list_item):
        pid = list_item.data(Qt.UserRole)
        item = self.party_items.get(pid)
        if item:
            self.view.centerOn(item)
            self.scene.clearSelection()
            item.setSelected(True)
            self.current_selected_party = item.party
            self.update_properties_panel()

    def game_to_pixel_pt(self, x, y):
        px = (x - self.min_x) * self.scale_factor
        py = self.img_height - (y - self.min_y) * self.scale_factor
        return QPointF(px, py)
        
    def pixel_to_game(self, px, py):
        x = (px / self.scale_factor) + self.min_x
        y = self.min_y + (self.img_height - py) / self.scale_factor
        return x, y

    def update_status(self, msg):
        self.status_bar.showMessage(msg)
        
    def save_all(self):
        try:
            if self.map_filepath and self.faces:
                lines = [f"{len(self.vertices)}\n"]
                for v in self.vertices:
                    lines.append(f"{v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
                lines.append(f"{len(self.faces)}\n")
                for f in self.faces:
                    parts = f['orig_parts']
                    parts[0] = str(f['terrain'])
                    lines.append(" ".join(parts) + "\n")
                with open(self.map_filepath, 'w') as fh:
                    fh.writelines(lines)
                    
            if self.parties_filepath and self.original_parties_lines:
                for p in self.parties:
                    parts = p['parts']
                    x_str, y_str = f"{p['x']:.6f}", f"{p['y']:.6f}"
                    parts[14:20] = [x_str, y_str, x_str, y_str, x_str, y_str]
                    self.original_parties_lines[p['index']] = " " + " ".join(parts) + " \n"
                    # 写回第二行角度数据，保留桥梁及实体的精确朝向
                    if 'angle' in p and p['index'] + 1 < len(self.original_parties_lines):
                        self.original_parties_lines[p['index'] + 1] = f"{p['angle']:.6f}\n"

                with open(self.parties_filepath, 'w', encoding='utf-8') as f:
                    f.writelines(self.original_parties_lines)

            # [INJECTED] Save scripts.txt
            if hasattr(self, 'scripts_filepath') and hasattr(self, 'script_ops') and self.script_ops:
                self.scripts_lines[3] = " " + " ".join(self.script_ops) + " \n"
                with open(self.scripts_filepath, 'w') as f:
                    f.writelines(self.scripts_lines)

                    
            self.is_modified = False
            QMessageBox.information(self, "保存成功", "map.txt 与 parties.txt 已成功精确写回！")
            self.status_bar.showMessage("已保存所有修改。")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败:\n{str(e)}")


    def subdivide_map(self):
        if not self.faces or not self.vertices:
            return
        
        reply = QMessageBox.question(self, '高危操作警告', 
                                     '全局细分将使得地图网格的面数变为原来的 4 倍，顶点数大幅增加。此操作虽然能大幅度缓解水陆交接处的狗牙现象，但也可能导致游戏内卡顿或超出引擎上限。建议在备份好的项目上使用。\n\n是否继续？',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.No:
            return
        
        self.status_bar.showMessage("正在全局细分网格，请耐心等待...")
        QApplication.processEvents()
        
        edge_to_midpoint = {}
        new_vertices = self.vertices.copy()
        new_faces = []
        
        def get_midpoint(v1, v2):
            edge = (min(v1, v2), max(v1, v2))
            if edge in edge_to_midpoint:
                return edge_to_midpoint[edge]
            pt1 = self.vertices[v1]
            pt2 = self.vertices[v2]
            mid_pt = ((pt1[0]+pt2[0])/2, (pt1[1]+pt2[1])/2, (pt1[2]+pt2[2])/2)
            idx = len(new_vertices)
            new_vertices.append(mid_pt)
            edge_to_midpoint[edge] = idx
            return idx

        for f in self.faces:
            v1, v2, v3 = f['v1'], f['v2'], f['v3']
            m12 = get_midpoint(v1, v2)
            m23 = get_midpoint(v2, v3)
            m31 = get_midpoint(v3, v1)
            
            terrain = f['terrain']
            def create_face(va, vb, vc):
                cx, cy = (new_vertices[va][0]+new_vertices[vb][0]+new_vertices[vc][0])/3, (new_vertices[va][1]+new_vertices[vb][1]+new_vertices[vc][1])/3
                parts = [str(terrain), '0', '3', str(va), str(vb), str(vc)]
                return {
                    'terrain': terrain, 'v1': va, 'v2': vb, 'v3': vc,
                    'orig_parts': parts, 'cx': cx, 'cy': cy
                }
            
            new_faces.append(create_face(v1, m12, m31))
            new_faces.append(create_face(v2, m23, m12))
            new_faces.append(create_face(v3, m31, m23))
            new_faces.append(create_face(m12, m23, m31))
            
        self.vertices = new_vertices
        self.faces = new_faces
        
        self.status_bar.showMessage("正在重构细分后的空间网格拓扑...")
        QApplication.processEvents()
        
        num_faces = len(self.faces)
        self.spatial_grid = {}
        for i, f_dict in enumerate(self.faces):
            cx, cy = f_dict['cx'], f_dict['cy']
            gx, gy = int(cx // self.grid_size), int(cy // self.grid_size)
            if (gx, gy) not in self.spatial_grid: self.spatial_grid[(gx, gy)] = []
            self.spatial_grid[(gx, gy)].append(i)
            
        self.adj = [[] for _ in range(num_faces)]
        for (gx, gy) in self.spatial_grid:
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if (gx+dx, gy+dy) in self.spatial_grid:
                        for f1 in self.spatial_grid[(gx, gy)]:
                            for f2 in self.spatial_grid[(gx+dx, gy+dy)]:
                                if f1 != f2:
                                    s1 = {self.faces[f1]['v1'], self.faces[f1]['v2'], self.faces[f1]['v3']}
                                    s2 = {self.faces[f2]['v1'], self.faces[f2]['v2'], self.faces[f2]['v3']}
                                    if len(s1.intersection(s2)) == 2:
                                        if f2 not in self.adj[f1]:
                                            self.adj[f1].append(f2)
                                        
        self.is_modified = True
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.status_bar.showMessage("细分完成！正在渲染新地图...")
        QApplication.processEvents()
        
        self.rebuild_visual_map()
        QMessageBox.information(self, "细分完成", f"网格已成功细分！\n现在顶点数: {len(self.vertices)}\n面数: {len(self.faces)}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MapEditor()
    ex.show()
    sys.exit(app.exec_())
