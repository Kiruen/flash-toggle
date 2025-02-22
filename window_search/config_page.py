#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
窗口搜索配置页面

该模块实现了窗口搜索的配置界面，包括：
1. 搜索设置
2. 界面设置
3. 快捷键设置
4. 窗口索引管理

作者：AI Assistant
创建日期：2024-03-20
"""

import logging
from typing import Optional, Dict, Any
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLabel, QPushButton, QSpinBox, QCheckBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QTabWidget, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer

from .window_index import WindowIndexManager
from hotkey_manager import HotkeyDialog

class SearchConfigPage(QWidget):
    """
    窗口搜索配置页面
    
    包含以下配置项：
    - 搜索设置（延迟、扫描间隔等）
    - 界面设置（显示内容、样式等）
    - 快捷键设置
    - 窗口索引管理
    """
    
    # 配置变更信号
    config_changed = pyqtSignal(dict)
    
    def __init__(
        self,
        window_index: WindowIndexManager,
        config: Dict[str, Any],
        parent: QWidget = None
    ):
        """
        初始化配置页面
        
        Args:
            window_index: 窗口索引管理器
            config: 初始配置
            parent: 父组件
        """
        super().__init__(parent)
        self._logger = logging.getLogger(__name__)
        self._window_index = window_index
        self._config = config.copy()
        
        # 创建定时器用于更新窗口列表
        self._update_timer = QTimer(self)
        self._update_timer.timeout.connect(self._update_window_list)
        self._update_timer.setInterval(2000)  # 每2秒更新一次
        
        self._init_ui()
        self._load_config()
        
        # 如果有窗口索引管理器，启动定时更新
        if self._window_index:
            self._update_timer.start()

    def _init_ui(self):
        """初始化用户界面"""
        self.setStyleSheet("""
            QWidget {
                background-color: #2E2E2E;
                color: #FFFFFF;
            }
            QGroupBox {
                background-color: #3E3E3E;
                border: 1px solid #555;
                margin-top: 12px;
                padding-top: 12px;
            }
            QGroupBox::title {
                color: #FFFFFF;
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QLabel {
                color: #FFFFFF;
            }
            QPushButton {
                background-color: #3E3E3E;
                color: #FFFFFF;
                border: 1px solid #555;
                padding: 5px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #4E4E4E;
            }
            QPushButton:pressed {
                background-color: #2E2E2E;
            }
            QSpinBox {
                background-color: #3E3E3E;
                color: #FFFFFF;
                border: 1px solid #555;
                padding: 3px;
                border-radius: 3px;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                background-color: #4E4E4E;
                border: none;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background-color: #5E5E5E;
            }
            QCheckBox {
                color: #FFFFFF;
                spacing: 5px;
            }
            QCheckBox::indicator {
                width: 15px;
                height: 15px;
                background-color: #3E3E3E;
                border: 1px solid #555;
                border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                background-color: #0078D7;
            }
            QCheckBox::indicator:hover {
                border-color: #888;
            }
            QTableWidget {
                background-color: #3E3E3E;
                color: #FFFFFF;
                border: 1px solid #555;
                border-radius: 3px;
                gridline-color: #555;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QTableWidget::item:selected {
                background-color: rgba(0, 120, 215, 0.3);
            }
            QHeaderView::section {
                background-color: #4E4E4E;
                color: #FFFFFF;
                padding: 5px;
                border: none;
                border-right: 1px solid #555;
                border-bottom: 1px solid #555;
            }
            QScrollBar:vertical {
                background-color: #2E2E2E;
                width: 12px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background-color: #4E4E4E;
                min-height: 20px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #5E5E5E;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
                background: none;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
            QTabWidget::pane {
                border: 1px solid #555;
                background-color: #2E2E2E;
            }
            QTabBar::tab {
                background-color: #3E3E3E;
                color: #FFFFFF;
                padding: 8px 15px;
                border: 1px solid #555;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #2E2E2E;
                border-bottom: none;
            }
            QTabBar::tab:hover:!selected {
                background-color: #4E4E4E;
            }
        """)
        layout = QVBoxLayout(self)
        
        # 创建标签页
        tab_widget = QTabWidget(self)
        
        # 1. 基本设置标签页
        basic_tab = QWidget()
        basic_layout = QVBoxLayout(basic_tab)
        
        # 快捷键设置组
        hotkey_group = QGroupBox("快捷键设置", basic_tab)
        hotkey_layout = QHBoxLayout(hotkey_group)
        
        self._hotkey_button = QPushButton("点击设置快捷键...", self)
        self._hotkey_button.clicked.connect(self._on_hotkey_clicked)
        hotkey_layout.addWidget(self._hotkey_button)
        
        basic_layout.addWidget(hotkey_group)
        
        # 搜索设置组
        search_group = QGroupBox("搜索设置", basic_tab)
        search_layout = QFormLayout(search_group)
        
        # 搜索延迟
        self._search_delay = QSpinBox(self)
        self._search_delay.setRange(0, 1000)
        self._search_delay.setSingleStep(50)
        self._search_delay.setSuffix(" ms")
        self._search_delay.setToolTip("输入后等待多久开始搜索")
        self._search_delay.valueChanged.connect(self._on_config_changed)
        search_layout.addRow("搜索延迟:", self._search_delay)
        
        # 扫描间隔
        self._scan_interval = QSpinBox(self)
        self._scan_interval.setRange(1, 10)
        self._scan_interval.setSuffix(" 秒")
        self._scan_interval.setToolTip("多久扫描一次所有窗口")
        self._scan_interval.valueChanged.connect(self._on_config_changed)
        search_layout.addRow("扫描间隔:", self._scan_interval)
        
        basic_layout.addWidget(search_group)
        basic_layout.addStretch()
        
        # 2. 显示设置标签页
        display_tab = QWidget()
        display_layout = QVBoxLayout(display_tab)
        
        # 界面设置组
        ui_group = QGroupBox("显示内容", display_tab)
        ui_layout = QFormLayout(ui_group)
        
        # 显示进程信息
        self._show_process = QCheckBox("显示进程名称和PID", self)
        self._show_process.setToolTip("在候选列表中显示窗口的进程信息")
        self._show_process.stateChanged.connect(self._on_config_changed)
        ui_layout.addRow(self._show_process)
        
        # 显示虚拟桌面信息
        self._show_desktop = QCheckBox("显示虚拟桌面信息", self)
        self._show_desktop.setToolTip("在候选列表中显示窗口所在的虚拟桌面")
        self._show_desktop.stateChanged.connect(self._on_config_changed)
        ui_layout.addRow(self._show_desktop)
        
        # 显示窗口图标
        self._show_icon = QCheckBox("显示窗口图标", self)
        self._show_icon.setToolTip("在候选列表中显示窗口的图标")
        self._show_icon.stateChanged.connect(self._on_config_changed)
        ui_layout.addRow(self._show_icon)
        
        display_layout.addWidget(ui_group)
        display_layout.addStretch()
        
        # 3. 窗口索引标签页
        index_tab = QWidget()
        index_layout = QVBoxLayout(index_tab)
        index_layout.setContentsMargins(10, 10, 10, 10)  # 设置边距
        index_layout.setSpacing(10)  # 设置间距
        
        # 创建表格
        self._window_table = QTableWidget(self)
        self._window_table.setColumnCount(5)
        self._window_table.setHorizontalHeaderLabels([
            "窗口标题", "进程名", "PID", "虚拟桌面", "状态"
        ])
        
        # 设置表格大小策略
        self._window_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._window_table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._window_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # 设置表格样式
        header = self._window_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # 标题列自适应
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        
        self._window_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #ccc;
                border-radius: 3px;
                background: #3E3E3E;
                color: #FFFFFF;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QHeaderView::section {
                background: #4E4E4E;
                color: #FFFFFF;
            }
        """)
        
        # 将表格添加到布局中，并设置拉伸因子
        index_layout.addWidget(self._window_table, 1)  # 设置拉伸因子为1
        
        # 添加标签页
        tab_widget.addTab(basic_tab, "基本设置")
        tab_widget.addTab(display_tab, "显示设置")
        tab_widget.addTab(index_tab, "窗口索引")
        
        layout.addWidget(tab_widget, 1)  # 设置标签页的拉伸因子为1
        
        # 添加说明文本
        help_text = QLabel(
            "提示：按下快捷键后，输入窗口标题进行搜索。\n"
            "使用方向键选择窗口，按回车键跳转到选中的窗口。",
            self
        )
        help_text.setStyleSheet("""
            color: #666;
            font-size: 9pt;
            margin-top: 10px;
            padding: 10px;
        """)
        layout.addWidget(help_text)

    def _load_config(self):
        """从配置加载设置"""
        # 快捷键
        hotkey = self._config.get("hotkey", "")
        self._hotkey_button.setText(hotkey if hotkey else "点击设置快捷键...")
        
        # 搜索设置
        self._search_delay.setValue(self._config.get("search_delay", 100))
        self._scan_interval.setValue(self._config.get("scan_interval", 2))
        
        # 界面设置
        self._show_process.setChecked(self._config.get("show_process", True))
        self._show_desktop.setChecked(self._config.get("show_desktop", True))
        self._show_icon.setChecked(self._config.get("show_icon", True))
        
    def _save_config(self):
        """保存设置到配置"""
        self._config.update({
            "hotkey": self._hotkey_button.text(),
            "search_delay": self._search_delay.value(),
            "scan_interval": self._scan_interval.value(),
            "show_process": self._show_process.isChecked(),
            "show_desktop": self._show_desktop.isChecked(),
            "show_icon": self._show_icon.isChecked()
        })
        
    def _on_config_changed(self):
        """处理配置变更"""
        self._save_config()
        self.config_changed.emit(self._config)
        
    def _on_hotkey_clicked(self):
        """处理快捷键按钮点击"""
        dialog = HotkeyDialog(self)
        if dialog.exec():
            hotkey = dialog.get_hotkey()
            if hotkey:
                self._hotkey_button.setText(hotkey)
                self._on_config_changed()
                
    def get_config(self) -> Dict[str, Any]:
        """
        获取当前配置
        
        Returns:
            Dict[str, Any]: 配置字典
        """
        return self._config.copy()

    def _update_window_list(self):
        """更新窗口列表"""
        if not self._window_index:
            return
            
        # 获取所有窗口
        windows = self._window_index.get_all_windows()
        
        # 更新表格
        self._window_table.setRowCount(len(windows))
        
        for i, window in enumerate(windows):
            # 窗口标题
            self._window_table.setItem(i, 0, QTableWidgetItem(window.title))
            
            # 进程名
            self._window_table.setItem(i, 1, QTableWidgetItem(window.process_name))
            
            # PID
            self._window_table.setItem(i, 2, QTableWidgetItem(str(window.process_id)))
            
            # 虚拟桌面
            desktop_id = window.desktop_id[-8:] if window.desktop_id else "未知"
            self._window_table.setItem(i, 3, QTableWidgetItem(desktop_id))
            
            # 状态
            status = []
            if window.is_minimized:
                status.append("最小化")
            if not window.is_visible:
                status.append("隐藏")
            status_text = "、".join(status) if status else "正常"
            self._window_table.setItem(i, 4, QTableWidgetItem(status_text)) 