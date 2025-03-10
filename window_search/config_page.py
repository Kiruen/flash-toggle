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
    QTableWidgetItem, QHeaderView, QTabWidget, QSizePolicy,
    QMenu
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QColor, QBrush

from .window_index import WindowIndexManager
from .window_actions import jump_to_window, edit_window_tags
from components.hotkey_input import HotkeyInput  # 导入新的快捷键输入组件

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
            window_index: 窗口索引管理器实例
            config: 初始配置
            parent: 父组件
        """
        super().__init__(parent)
        self._logger = logging.getLogger(__name__)
        self._logger.debug("初始化搜索配置页面...")
        self._window_index = window_index
        self._config = config.copy()
        self._logger.debug(f"初始配置: {self._config}")
        
        # 创建定时器用于更新窗口列表
        self._update_timer = QTimer(self)
        self._update_timer.timeout.connect(self._update_window_list)
        self._update_timer.setInterval(2000)  # 每2秒更新一次
        
        self._init_ui()
        self._load_config()
        
        # 如果有窗口索引管理器，启动定时更新
        if self._window_index:
            self._update_timer.start()
            self._logger.debug("窗口列表更新定时器已启动")

    def _init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # 创建标签页
        tab_widget = QTabWidget(self)
        
        # 1. 基本设置标签页
        basic_tab = QWidget()
        basic_layout = QVBoxLayout(basic_tab)
        basic_layout.setSpacing(15)
        
        # 搜索设置组
        search_group = QGroupBox("搜索设置", basic_tab)
        search_layout = QVBoxLayout(search_group)
        
        # 搜索延迟
        delay_layout = QHBoxLayout()
        self._search_delay = QSpinBox(self)
        self._search_delay.setRange(0, 1000)
        self._search_delay.setSingleStep(50)
        self._search_delay.setSuffix(" ms")
        self._search_delay.setValue(self._config.get("search_delay", 100))
        self._search_delay.valueChanged.connect(self._on_config_changed)
        delay_layout.addWidget(QLabel("搜索延迟:"))
        delay_layout.addWidget(self._search_delay)
        delay_layout.addStretch()
        search_layout.addLayout(delay_layout)
        
        # 扫描间隔
        scan_layout = QHBoxLayout()
        self._scan_interval = QSpinBox(self)
        self._scan_interval.setRange(1, 10)
        self._scan_interval.setSuffix(" 秒")
        self._scan_interval.setValue(self._config.get("scan_interval", 2))
        self._scan_interval.valueChanged.connect(self._on_config_changed)
        scan_layout.addWidget(QLabel("扫描间隔:"))
        scan_layout.addWidget(self._scan_interval)
        scan_layout.addStretch()
        search_layout.addLayout(scan_layout)
        
        basic_layout.addWidget(search_group)
        
        # 界面设置组
        display_group = QGroupBox("界面设置", basic_tab)
        display_layout = QVBoxLayout(display_group)
        
        # 显示进程名
        self._show_process = QCheckBox("显示进程名")
        self._show_process.setChecked(self._config.get("show_process", True))
        self._show_process.stateChanged.connect(self._on_config_changed)
        display_layout.addWidget(self._show_process)
        
        # 显示虚拟桌面信息
        self._show_desktop = QCheckBox("显示虚拟桌面信息")
        self._show_desktop.setChecked(self._config.get("show_desktop", True))
        self._show_desktop.stateChanged.connect(self._on_config_changed)
        display_layout.addWidget(self._show_desktop)
        
        # 显示窗口图标
        self._show_icon = QCheckBox("显示窗口图标")
        self._show_icon.setChecked(self._config.get("show_icon", True))
        self._show_icon.stateChanged.connect(self._on_config_changed)
        display_layout.addWidget(self._show_icon)
        
        basic_layout.addWidget(display_group)
        basic_layout.addStretch()
        
        tab_widget.addTab(basic_tab, "基本设置")
        
        # 2. 窗口索引标签页
        index_tab = QWidget()
        index_layout = QVBoxLayout(index_tab)
        
        # 创建窗口列表表格
        self._window_table = QTableWidget(self)
        self._window_table.setColumnCount(5)
        self._window_table.setHorizontalHeaderLabels([
            "窗口标题", "进程名", "PID", "虚拟桌面", "状态"
        ])
        
        # 设置表格样式
        header = self._window_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # 标题列自适应
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        
        # 设置右键菜单策略
        self._window_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self._window_table.customContextMenuRequested.connect(self._show_context_menu)
        
        # 连接双击事件
        self._window_table.itemDoubleClicked.connect(self._on_item_double_clicked)
        
        index_layout.addWidget(self._window_table)
        
        tab_widget.addTab(index_tab, "窗口索引")
        layout.addWidget(tab_widget)
        
        # 添加说明文本
        help_text = QLabel(
            "说明：窗口搜索可通过全局快捷键触发，在快捷键设置页面配置。\n"
            "搜索时，输入窗口标题进行搜索，使用方向键选择，按回车键跳转。",
            self
        )
        help_text.setStyleSheet("""
            color: #666;
            font-size: 9pt;
            margin-top: 10px;
            padding: 10px;
            background-color: #3A3A3A;
            border-radius: 5px;
        """)
        layout.addWidget(help_text)

    def _load_config(self):
        """从配置加载设置"""
        self._logger.debug("开始加载搜索配置...")
        self._logger.debug(f"当前配置内容: {self._config}")
        
        # 搜索设置
        search_delay = self._config.get("search_delay", 100)
        scan_interval = self._config.get("scan_interval", 2)
        self._logger.debug(f"加载搜索延迟: {search_delay}ms")
        self._logger.debug(f"加载扫描间隔: {scan_interval}秒")
        self._search_delay.setValue(search_delay)
        self._scan_interval.setValue(scan_interval)
        
        # 界面设置
        show_process = self._config.get("show_process", True)
        show_desktop = self._config.get("show_desktop", True)
        show_icon = self._config.get("show_icon", True)
        self._logger.debug(f"加载界面设置: 进程={show_process}, 桌面={show_desktop}, 图标={show_icon}")
        self._show_process.setChecked(show_process)
        self._show_desktop.setChecked(show_desktop)
        self._show_icon.setChecked(show_icon)
        
        self._logger.debug("搜索配置加载完成")
        
    def _save_config(self):
        """保存设置到配置"""
        self._logger.debug("开始保存搜索配置...")
        
        new_config = {
            "search_delay": self._search_delay.value(),
            "scan_interval": self._scan_interval.value(),
            "show_process": self._show_process.isChecked(),
            "show_desktop": self._show_desktop.isChecked(),
            "show_icon": self._show_icon.isChecked()
        }
        
        self._logger.debug(f"新的配置内容: {new_config}")
        self._config.update(new_config)
        self._logger.debug("搜索配置保存完成")
        
    def _on_config_changed(self):
        """处理配置变更"""
        self._save_config()
        self.config_changed.emit(self._config)
        
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
            
    def _show_context_menu(self, pos):
        """
        显示右键菜单
        
        Args:
            pos: 鼠标位置
        """
        # 获取当前选中的行
        current_row = self._window_table.currentRow()
        if current_row < 0:
            return
            
        # 获取窗口信息
        windows = self._window_index.get_all_windows()
        if current_row >= len(windows):
            return
            
        window = windows[current_row]
        
        # 创建菜单
        menu = QMenu(self)
        jump_action = menu.addAction("跳转到窗口")
        edit_tags_action = menu.addAction("编辑标签")
        
        # 显示菜单并处理选择
        action = menu.exec_(self._window_table.viewport().mapToGlobal(pos))
        
        if action == jump_action:
            jump_to_window(window)
        elif action == edit_tags_action:
            if edit_window_tags(window, self._window_index, self):
                self._update_window_list()
                
    def _on_item_double_clicked(self, item):
        """
        处理双击事件
        
        Args:
            item: 被双击的表格项
        """
        # 获取当前行
        current_row = self._window_table.row(item)
        
        # 获取窗口信息
        windows = self._window_index.get_all_windows()
        if current_row >= len(windows):
            return
            
        # 跳转到窗口
        window = windows[current_row]
        jump_to_window(window)