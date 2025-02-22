#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
窗口搜索配置页面

该模块实现了窗口搜索功能的配置界面，包括：
1. 快捷键设置
2. 搜索选项配置
3. 界面外观设置
4. 窗口索引列表

作者：AI Assistant
创建日期：2024-03-20
"""

import logging
from typing import Optional, Dict, Any
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSpinBox, QCheckBox, QGroupBox,
    QFormLayout, QTableWidget, QTableWidgetItem,
    QHeaderView
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer

from .window_index import WindowIndexManager

class SearchConfigPage(QWidget):
    """
    窗口搜索配置页面
    
    提供以下配置选项：
    - 搜索快捷键
    - 搜索延迟
    - 窗口扫描间隔
    - 界面外观选项
    - 窗口索引列表
    """
    
    # 配置变更信号
    config_changed = pyqtSignal(dict)  # 当配置发生变化时发出
    
    def __init__(
        self,
        config: Dict[str, Any],
        window_index: Optional[WindowIndexManager] = None,
        parent: Optional[QWidget] = None
    ):
        """
        初始化配置页面
        
        Args:
            config: 当前配置
            window_index: 窗口索引管理器实例
            parent: 父组件
        """
        super().__init__(parent)
        self._logger = logging.getLogger(__name__)
        self._config = config.copy()
        self._window_index = window_index
        
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
        # 创建主布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # 添加标题
        title = QLabel("窗口搜索设置", self)
        title.setStyleSheet("""
            font-size: 16pt;
            font-weight: bold;
            color: #333;
            margin-bottom: 10px;
        """)
        layout.addWidget(title)
        
        # 创建快捷键设置组
        hotkey_group = QGroupBox("快捷键设置", self)
        hotkey_layout = QFormLayout(hotkey_group)
        
        # 搜索快捷键
        self._hotkey_button = QPushButton("点击设置快捷键...", self)
        self._hotkey_button.clicked.connect(self._on_hotkey_clicked)
        hotkey_layout.addRow("搜索快捷键:", self._hotkey_button)
        
        layout.addWidget(hotkey_group)
        
        # 创建搜索设置组
        search_group = QGroupBox("搜索设置", self)
        search_layout = QFormLayout(search_group)
        
        # 搜索延迟
        self._search_delay = QSpinBox(self)
        self._search_delay.setRange(0, 1000)
        self._search_delay.setSingleStep(50)
        self._search_delay.setSuffix(" ms")
        self._search_delay.setToolTip("输入时延迟多久开始搜索")
        self._search_delay.valueChanged.connect(self._on_config_changed)
        search_layout.addRow("搜索延迟:", self._search_delay)
        
        # 窗口扫描间隔
        self._scan_interval = QSpinBox(self)
        self._scan_interval.setRange(1, 10)
        self._scan_interval.setSingleStep(1)
        self._scan_interval.setSuffix(" 秒")
        self._scan_interval.setToolTip("多久扫描一次所有窗口")
        self._scan_interval.valueChanged.connect(self._on_config_changed)
        search_layout.addRow("扫描间隔:", self._scan_interval)
        
        layout.addWidget(search_group)
        
        # 创建界面设置组
        ui_group = QGroupBox("界面设置", self)
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
        
        layout.addWidget(ui_group)
        
        # 创建窗口索引列表组
        index_group = QGroupBox("窗口索引列表", self)
        index_layout = QVBoxLayout(index_group)
        
        # 创建表格
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
        
        self._window_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #ccc;
                border-radius: 3px;
                background: white;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QHeaderView::section {
                background: #f0f0f0;
                padding: 5px;
                border: none;
                border-right: 1px solid #ccc;
                border-bottom: 1px solid #ccc;
            }
        """)
        
        index_layout.addWidget(self._window_table)
        layout.addWidget(index_group)
        
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
        """)
        layout.addWidget(help_text)
        
        # 添加弹性空间
        layout.addStretch()

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
        from hotkey_manager import HotkeyDialog
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