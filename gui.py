#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
图形用户界面模块

该模块负责创建和管理应用程序的图形界面，包括主窗口、系统托盘等。
主要功能：
1. 创建主窗口和系统托盘
2. 显示和管理窗口列表
3. 处理用户输入和快捷键配置

作者：AI Assistant
创建日期：2024-03-20
"""

from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                           QPushButton, QLineEdit, QListWidget, QListWidgetItem,
                           QLabel, QSystemTrayIcon, QMenu, QMessageBox, QTabWidget,
                           QGridLayout, QCheckBox, QStatusBar, QApplication, QGroupBox)
from PyQt5.QtCore import Qt, QSize, pyqtSignal, QPoint, QSize, QTimer
from PyQt5.QtGui import QIcon, QCloseEvent, QColor, QBrush
import keyboard
from typing import Optional, Dict, Callable
import logging
from dataclasses import dataclass
import win32gui
import sys
import win32con
import os
import time
import signal

from window_manager import WindowManager, WindowInfo
from hotkey_manager import HotkeyManager
from config_manager import ConfigManager, AppConfig
from window_search import WindowIndexManager, SearchWindow, SearchConfigPage, WindowHistoryManager

@dataclass
class GlobalHotkey:
    """全局快捷键配置"""
    name: str
    description: str
    default: str
    current: str
    callback: Callable

class HotkeyInput(QLineEdit):
    """快捷键输入框"""
    
    hotkey_changed = pyqtSignal(str, str)  # 发送 hotkey_id 和 hotkey
    
    def __init__(
        self,
        hotkey_id: str = "",
        description: str = "",
        initial_hotkey: str = "",
        callback: Optional[Callable] = None,
        parent: Optional[QWidget] = None
    ):
        """
        初始化快捷键输入框
        
        Args:
            hotkey_id: 快捷键ID
            description: 快捷键描述
            initial_hotkey: 初始快捷键
            callback: 快捷键触发时的回调函数
            parent: 父组件
        """
        super().__init__(parent)
        self._hotkey_id = hotkey_id
        self._description = description
        self._callback = callback
        self._keys = set()
        
        self.setReadOnly(True)
        self.setPlaceholderText("点击此处按下快捷键 (ESC或退格键清除)")
        self.setToolTip(f"{description}\n当前快捷键: {initial_hotkey or '未设置'}\n按ESC或退格键可清除快捷键")
        
        if initial_hotkey:
            self.setText(initial_hotkey)
        
    def keyPressEvent(self, event):
        """处理按键按下事件"""
        if event.key() == Qt.Key_Escape:
            self.clear()
            self._keys.clear()
            self.hotkey_changed.emit(self._hotkey_id, "")
            return
            
        # 添加对退格键的处理
        if event.key() == Qt.Key_Backspace:
            self.clear()
            self._keys.clear()
            self.hotkey_changed.emit(self._hotkey_id, "")
            return
            
        key = event.key()
        if key not in self._keys:
            self._keys.add(key)
            self._update_text()
            
    def keyReleaseEvent(self, event):
        """处理按键释放事件"""
        key = event.key()
        if key in self._keys:
            self._keys.remove(key)
            if not self._keys:  # 所有按键都已释放
                self.hotkey_changed.emit(self._hotkey_id, self.text())
                
    def _update_text(self):
        """更新显示的快捷键文本"""
        keys = []
        # 添加修饰键
        if Qt.Key_Control in self._keys:
            keys.append("ctrl")
        if Qt.Key_Alt in self._keys:
            keys.append("alt")
        if Qt.Key_Shift in self._keys:
            keys.append("shift")
            
        # 添加其他按键
        for key in self._keys:
            if key not in [Qt.Key_Control, Qt.Key_Alt, Qt.Key_Shift]:
                # 处理特殊按键
                key_text = self._get_key_text(key)
                if key_text:
                    keys.append(key_text)
                
        self.setText("+".join(keys))
        
    def _get_key_text(self, key: int) -> str:
        """
        获取按键的文本表示
        
        Args:
            key: Qt按键代码
            
        Returns:
            str: 按键的文本表示
        """
        # 数字键
        if Qt.Key_0 <= key <= Qt.Key_9:
            return str(key - Qt.Key_0)
            
        # 字母键
        if Qt.Key_A <= key <= Qt.Key_Z:
            return chr(key).lower()
            
        # 功能键
        if Qt.Key_F1 <= key <= Qt.Key_F12:
            return f"f{key - Qt.Key_F1 + 1}"
            
        # 其他特殊按键
        special_keys = {
            Qt.Key_Tab: "tab",
            Qt.Key_Return: "enter",
            Qt.Key_Space: "space",
            Qt.Key_Home: "home",
            Qt.Key_End: "end",
            Qt.Key_PageUp: "pageup",
            Qt.Key_PageDown: "pagedown",
            Qt.Key_Insert: "insert",
            Qt.Key_Delete: "delete",
            Qt.Key_Left: "left",
            Qt.Key_Right: "right",
            Qt.Key_Up: "up",
            Qt.Key_Down: "down",
            Qt.Key_Escape: "esc",
            Qt.Key_Print: "print",
            Qt.Key_ScrollLock: "scrolllock",
            Qt.Key_Pause: "pause",
            Qt.Key_Menu: "menu",
        }
        
        return special_keys.get(key, "")

class MainWindow(QMainWindow):
    """主窗口类"""
    
    def __init__(
        self,
        window_manager: WindowManager,
        hotkey_manager: HotkeyManager,
        window_index: WindowIndexManager,
        search_window: SearchWindow,
        parent: Optional[QWidget] = None
    ):
        """
        初始化主窗口
        
        Args:
            window_manager: 窗口管理器实例
            hotkey_manager: 快捷键管理器实例
            window_index: 窗口索引管理器实例
            search_window: 搜索窗口实例
            parent: 父窗口实例
        """
        super().__init__(parent)
        
        self._window_manager = window_manager
        self._hotkey_manager = hotkey_manager
        self._window_index = window_index
        self._search_window = search_window
        self._config_manager = ConfigManager()
        self._logger = logging.getLogger(__name__)
        
        # 初始化窗口历史管理器
        self._window_history = WindowHistoryManager()
        
        # 加载配置
        config = self._config_manager.get_config()
        
        # 初始化全局快捷键配置
        self._global_hotkeys = {
            "toggle_main": GlobalHotkey(
                "toggle_main", "显示/隐藏主窗口",
                config.global_hotkeys.get("toggle_main", "ctrl+shift+c"),
                "",
                self._toggle_main_window
            ),
            "capture": GlobalHotkey(
                "capture", "捕获当前窗口",
                config.global_hotkeys.get("capture", "space+c"),
                "",
                self._on_capture_window
            ),
            "toggle_topmost": GlobalHotkey(
                "toggle_topmost", "切换当前窗口置顶状态",
                config.global_hotkeys.get("toggle_topmost", "space+t"),
                "",
                self._toggle_active_window_topmost
            ),
            "search": GlobalHotkey(
                "search", "显示窗口搜索",
                config.global_hotkeys.get("search", "alt+space"),
                "",
                self._show_search_window
            ),
            "prev_window": GlobalHotkey(
                "prev_window", "跳转到前一个窗口",
                config.global_hotkeys.get("prev_window", "ctrl+alt+left"),
                "",
                self._window_history.jump_to_previous
            ),
            "next_window": GlobalHotkey(
                "next_window", "跳转到后一个窗口",
                config.global_hotkeys.get("next_window", "ctrl+alt+right"),
                "",
                self._window_history.jump_to_next
            )
        }
        
        # 初始化界面
        self._init_ui()
        
        # 注册所有全局快捷键
        self._setup_global_hotkeys()
        
        # 恢复窗口状态
        self._restore_window_state(config)
        
        # 恢复保存的窗口配置
        self._restore_saved_windows(config)
        
        # 设置定时检查窗口状态
        self._check_timer = QTimer(self)
        self._check_timer.timeout.connect(self._check_windows_status)
        self._check_timer.start(5000)  # 每5秒检查一次
        
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
        self.setWindowTitle("Flash-Toggle")
        self.setMinimumSize(500, 600)
        
        # 创建状态栏
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.show_status("就绪")
        
        # 创建中央部件和标签页
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        tab_widget = QTabWidget()
        layout.addWidget(tab_widget)
        
        # 添加窗口管理标签页
        window_tab = QWidget()
        tab_widget.addTab(window_tab, "窗口管理")
        self._init_window_tab(window_tab)
        
        # 添加快捷键设置标签页
        hotkey_tab = QWidget()
        tab_widget.addTab(hotkey_tab, "快捷键设置")
        self._init_hotkey_tab(hotkey_tab)
        
        # 添加其他设置标签页
        settings_tab = QWidget()
        tab_widget.addTab(settings_tab, "其他设置")
        self._init_settings_tab(settings_tab)
        
        # 获取配置
        config = self._config_manager.get_config()
        
        # 添加搜索配置页
        search_config = SearchConfigPage(
            window_index=self._window_index,
            config=config.window_search if hasattr(config, 'window_search') else {}
        )
        search_config.config_changed.connect(self._on_search_config_changed)
        tab_widget.addTab(search_config, "窗口搜索")
        
        # 设置托盘图标
        self._setup_tray_icon()
        
    def _init_window_tab(self, tab: QWidget):
        """初始化窗口管理标签页"""
        layout = QVBoxLayout(tab)
        
        # 添加主窗口置顶复选框
        self.always_on_top_checkbox = QCheckBox("主窗口置顶")
        self.always_on_top_checkbox.setChecked(True)  # 默认选中
        self.always_on_top_checkbox.stateChanged.connect(self._on_always_on_top_changed)
        layout.addWidget(self.always_on_top_checkbox)
        
        # 创建窗口列表
        self.window_list = QListWidget()
        self.window_list.itemClicked.connect(self._on_window_selected)
        self.window_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.window_list.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(QLabel("已捕获的窗口:"))
        layout.addWidget(self.window_list)
        
        # 创建快捷键配置区域
        hotkey_group = QGroupBox("窗口快捷键", self)
        hotkey_layout = QVBoxLayout(hotkey_group)
        
        # 窗口快捷键输入框
        self.hotkey_input = HotkeyInput(
            hotkey_id="window_hotkey",
            description="为选中的窗口设置快捷键",
            parent=self
        )
        self.hotkey_input.hotkey_changed.connect(self._on_window_hotkey_changed)
        hotkey_layout.addWidget(self.hotkey_input)
        
        # 快捷键操作按钮
        button_layout = QHBoxLayout()
        self.set_hotkey_btn = QPushButton("设置快捷键")
        self.set_hotkey_btn.clicked.connect(self._on_set_hotkey)
        self.clear_hotkey_btn = QPushButton("清除快捷键")
        self.clear_hotkey_btn.clicked.connect(self._on_clear_hotkey)
        button_layout.addWidget(self.set_hotkey_btn)
        button_layout.addWidget(self.clear_hotkey_btn)
        hotkey_layout.addLayout(button_layout)
        
        layout.addWidget(hotkey_group)
        
        # 创建底部按钮
        button_layout = QHBoxLayout()
        
        clear_btn = QPushButton("清除列表")
        clear_btn.clicked.connect(self._on_clear_list)
        button_layout.addWidget(clear_btn)
        
        remove_btn = QPushButton("删除选中")
        remove_btn.clicked.connect(self._on_remove_window)
        button_layout.addWidget(remove_btn)
        
        cleanup_btn = QPushButton("清理无效窗口")
        cleanup_btn.clicked.connect(self._cleanup_invalid_windows)
        button_layout.addWidget(cleanup_btn)
        
        layout.addLayout(button_layout)
        
    def _init_hotkey_tab(self, tab: QWidget):
        """初始化快捷键设置标签页"""
        layout = QVBoxLayout(tab)
        
        # 添加说明标签
        layout.addWidget(QLabel("全局快捷键设置:"))
        
        # 全局快捷键设置组
        hotkey_group = QGroupBox("全局快捷键", self)
        hotkey_layout = QVBoxLayout(hotkey_group)
        
        # 获取配置
        config = self._config_manager.get_config()
        
        # 主窗口快捷键
        toggle_main_layout = QHBoxLayout()
        self._toggle_main_hotkey = HotkeyInput(
            hotkey_id="toggle_main",
            description="显示/隐藏主窗口",
            initial_hotkey=config.global_hotkeys.get("toggle_main", ""),
            callback=self._toggle_main_window,
            parent=self
        )
        self._toggle_main_hotkey.hotkey_changed.connect(self._on_global_hotkey_changed)
        toggle_main_layout.addWidget(QLabel("显示/隐藏主窗口:"))
        toggle_main_layout.addWidget(self._toggle_main_hotkey)
        hotkey_layout.addLayout(toggle_main_layout)
        
        # 捕获窗口快捷键
        capture_layout = QHBoxLayout()
        self._capture_hotkey = HotkeyInput(
            hotkey_id="capture",
            description="捕获当前窗口",
            initial_hotkey=config.global_hotkeys.get("capture", ""),
            callback=self._on_capture_window,
            parent=self
        )
        self._capture_hotkey.hotkey_changed.connect(self._on_global_hotkey_changed)
        capture_layout.addWidget(QLabel("捕获当前窗口:"))
        capture_layout.addWidget(self._capture_hotkey)
        hotkey_layout.addLayout(capture_layout)
        
        # 切换置顶快捷键
        toggle_topmost_layout = QHBoxLayout()
        self._toggle_topmost_hotkey = HotkeyInput(
            hotkey_id="toggle_topmost",
            description="切换当前窗口置顶状态",
            initial_hotkey=config.global_hotkeys.get("toggle_topmost", ""),
            callback=self._toggle_active_window_topmost,
            parent=self
        )
        self._toggle_topmost_hotkey.hotkey_changed.connect(self._on_global_hotkey_changed)
        toggle_topmost_layout.addWidget(QLabel("切换窗口置顶:"))
        toggle_topmost_layout.addWidget(self._toggle_topmost_hotkey)
        hotkey_layout.addLayout(toggle_topmost_layout)
        
        # 搜索窗口快捷键
        search_layout = QHBoxLayout()
        self._search_hotkey = HotkeyInput(
            hotkey_id="search",
            description="显示窗口搜索",
            initial_hotkey=config.global_hotkeys.get("search", ""),
            callback=self._show_search_window,
            parent=self
        )
        self._search_hotkey.hotkey_changed.connect(self._on_global_hotkey_changed)
        search_layout.addWidget(QLabel("显示窗口搜索:"))
        search_layout.addWidget(self._search_hotkey)
        hotkey_layout.addLayout(search_layout)
        
        # 前一个窗口快捷键
        prev_window_layout = QHBoxLayout()
        self._prev_window_hotkey = HotkeyInput(
            hotkey_id="prev_window",
            description="跳转到前一个窗口",
            initial_hotkey=config.global_hotkeys.get("prev_window", ""),
            callback=self._window_history.jump_to_previous,
            parent=self
        )
        self._prev_window_hotkey.hotkey_changed.connect(self._on_global_hotkey_changed)
        prev_window_layout.addWidget(QLabel("跳转到前一个窗口:"))
        prev_window_layout.addWidget(self._prev_window_hotkey)
        hotkey_layout.addLayout(prev_window_layout)
        
        # 后一个窗口快捷键
        next_window_layout = QHBoxLayout()
        self._next_window_hotkey = HotkeyInput(
            hotkey_id="next_window",
            description="跳转到后一个窗口",
            initial_hotkey=config.global_hotkeys.get("next_window", ""),
            callback=self._window_history.jump_to_next,
            parent=self
        )
        self._next_window_hotkey.hotkey_changed.connect(self._on_global_hotkey_changed)
        next_window_layout.addWidget(QLabel("跳转到后一个窗口:"))
        next_window_layout.addWidget(self._next_window_hotkey)
        hotkey_layout.addLayout(next_window_layout)
        
        # 添加到主布局
        layout.addWidget(hotkey_group)
        
        # 添加说明文本
        help_text = QLabel(
            "提示：按ESC键或退格键可以清除快捷键。\n"
            "设置快捷键后会立即生效。",
            self
        )
        help_text.setStyleSheet("""
            color: #666;
            font-size: 9pt;
            margin-top: 10px;
            padding: 10px;
        """)
        layout.addWidget(help_text)
        layout.addStretch()
        
    def _init_settings_tab(self, tab: QWidget):
        """初始化其他设置标签页"""
        layout = QVBoxLayout(tab)
        
        # 添加关闭行为设置
        close_group = QWidget()
        close_layout = QHBoxLayout(close_group)
        close_layout.setContentsMargins(0, 0, 0, 0)
        
        self.minimize_to_tray_checkbox = QCheckBox("关闭窗口时最小化到托盘")
        self.minimize_to_tray_checkbox.setChecked(
            self._config_manager.get_config().main_window["minimize_to_tray"]
        )
        self.minimize_to_tray_checkbox.stateChanged.connect(self._on_minimize_to_tray_changed)
        close_layout.addWidget(self.minimize_to_tray_checkbox)
        
        # 添加说明标签
        close_layout.addWidget(QLabel("（取消勾选则直接退出程序）"))
        close_layout.addStretch()
        
        layout.addWidget(close_group)
        layout.addStretch()
        
    def _setup_global_hotkeys(self):
        """设置全局快捷键"""
        # 注册所有全局快捷键
        for name, hotkey in self._global_hotkeys.items():
            if hotkey.default:
                self._hotkey_manager.register_hotkey(
                    hotkey.default,
                    hotkey.callback,
                    name
                )
            
    def _on_global_hotkey_changed(self, hotkey_id: str, hotkey: str):
        """
        处理全局快捷键变更
        
        Args:
            hotkey_id: 快捷键ID
            hotkey: 新的快捷键
        """
        self._logger.debug(f"全局快捷键变更: {hotkey_id} = {hotkey}")
        
        # 更新配置
        self._config_manager.update_global_hotkey(hotkey_id, hotkey)
        
        # 更新快捷键注册
        if hotkey_id in self._global_hotkeys:
            self._global_hotkeys[hotkey_id].current = hotkey
            
        # 保存配置
        self._config_manager.save_config()
        
    def _add_window_to_list(self, window_info: WindowInfo):
        """
        将窗口添加到列表中
        
        Args:
            window_info: 窗口信息对象
        """
        status = []
        if window_info.hotkey:
            status.append(f"快捷键: {window_info.hotkey}")
        if not window_info.is_visible:
            status.append("已隐藏")
        if window_info.is_topmost:
            status.append("已置顶")
            
        title = window_info.title
        if status:
            title = f"{title} ({', '.join(status)})"
            
        item = QListWidgetItem(title)
        item.setData(Qt.UserRole, window_info.handle)
        self.window_list.addItem(item)
        
    def _update_window_item(self, handle: int):
        """
        更新窗口列表项
        
        Args:
            handle: 窗口句柄
        """
        window_info = self._window_manager.get_window_info(handle)
        if not window_info:
            return
            
        # 查找并更新列表项
        for i in range(self.window_list.count()):
            item = self.window_list.item(i)
            if item.data(Qt.UserRole) == handle:
                self._add_window_to_list(window_info)  # 重新添加以更新显示
                self.window_list.takeItem(i)  # 移除旧项
                break
                
    def _on_hotkey_input_changed(self, hotkey: str):
        """
        处理快捷键输入变更
        
        Args:
            hotkey: 新的快捷键
        """
        if self._hotkey_manager.is_valid_hotkey(hotkey):
            self.set_hotkey_btn.setEnabled(True)
        else:
            self.set_hotkey_btn.setEnabled(False)
            
    def _on_window_hotkey_changed(self, hotkey_id: str, hotkey: str):
        """
        处理窗口快捷键变更
        
        Args:
            hotkey_id: 快捷键ID（在窗口快捷键中未使用）
            hotkey: 新的快捷键
        """
        if self._hotkey_manager.is_valid_hotkey(hotkey):
            self.set_hotkey_btn.setEnabled(True)
            self.hotkey_input.setText(hotkey)  # 保持输入框显示当前快捷键
        else:
            self.set_hotkey_btn.setEnabled(False)
            
    def _on_set_hotkey(self):
        """处理设置快捷键事件"""
        item = self.window_list.currentItem()
        if not item:
            self.show_status("请先选择一个窗口")
            return
            
        handle = item.data(Qt.UserRole)
        window_info = self._window_manager.get_window_info(handle)
        if not window_info:
            return
            
        hotkey = self.hotkey_input.text().strip()
        if not hotkey:
            self.show_status("请输入快捷键")
            return
            
        # 如果已有快捷键，先解除绑定
        if window_info.hotkey:
            self._hotkey_manager.unregister_hotkey(window_info.hotkey)
            
        # 设置新快捷键
        if self._window_manager.set_window_hotkey(handle, hotkey):
            self._hotkey_manager.register_hotkey(
                hotkey,
                lambda: self._window_manager.toggle_window_visibility(handle)
            )
            self._update_window_item(handle)
            self.show_status("快捷键设置成功")
            
    def _on_clear_hotkey(self):
        """处理清除快捷键事件"""
        item = self.window_list.currentItem()
        if not item:
            return
            
        handle = item.data(Qt.UserRole)
        window_info = self._window_manager.get_window_info(handle)
        if window_info and window_info.hotkey:
            self._hotkey_manager.unregister_hotkey(window_info.hotkey)
            self._window_manager.set_window_hotkey(handle, "")
            self.hotkey_input.clear()
            # 确保发出信号
            self.hotkey_input.hotkey_changed.emit("window_hotkey", "")
            self._update_window_item(handle)
            self.show_status("快捷键已清除")
            
    def _toggle_main_window(self):
        """切换主窗口显示状态"""
        if self.isVisible():
            self.hide()
        else:
            self.show_and_activate()  # 使用新方法
            
    def _on_capture_window(self):
        """处理窗口捕获事件"""
        window_info = self._window_manager.capture_active_window()
        if window_info:
            self._add_window_to_list(window_info)
            self.show()  # 显示主窗口
            self.activateWindow()
            
    def _on_window_selected(self, item: QListWidgetItem):
        """
        处理窗口选择事件
        
        Args:
            item: 被选中的列表项
        """
        handle = item.data(Qt.UserRole)
        window_info = self._window_manager.get_window_info(handle)
        if window_info and window_info.hotkey:
            self.hotkey_input.setText(window_info.hotkey)
            
    def _on_clear_list(self):
        """处理清除列表事件"""
        self.window_list.clear()
        self._window_manager.clear_windows()
        self._hotkey_manager.clear_all_hotkeys()
        self._setup_global_hotkeys()  # 重新注册全局快捷键
        
    def _setup_tray_icon(self):
        """设置系统托盘图标"""
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.style().standardIcon(self.style().SP_ComputerIcon))
        self.tray_icon.setToolTip("Flash-Toggle - 快捷窗口管理工具")
        
        # 连接双击信号
        self.tray_icon.activated.connect(self._on_tray_icon_activated)
        
        # 创建托盘菜单
        tray_menu = QMenu()
        show_action = tray_menu.addAction("显示")
        show_action.triggered.connect(self.show_and_activate)
        quit_action = tray_menu.addAction("退出")
        quit_action.triggered.connect(self._on_quit)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

    def show_and_activate(self):
        """显示并激活窗口，确保窗口正确显示"""
        if not self.isVisible():
            self.show()
        self.setWindowState(self.windowState() & ~Qt.WindowMinimized)  # 取消最小化状态
        self.activateWindow()  # 激活窗口
        self.raise_()  # 将窗口置于最前

    def _on_quit(self):
        """处理退出事件，确保程序完全退出并清理所有资源"""
        try:
            self._logger.info("=== 开始程序退出流程 ===")
            
            # 1. 停止定时器
            self._logger.info("1. 停止定时器...")
            if hasattr(self, '_check_timer'):
                self._check_timer.stop()
                self._check_timer = None
                self._logger.info("定时器已停止")
            
            # 2. 保存窗口配置
            self._logger.info("2. 保存窗口配置...")
            for handle, window in self._window_manager._windows.items():
                self._config_manager.save_window_config(window.title, {
                    "handle": handle,  # 保存窗口句柄
                    "hotkey": window.hotkey,
                    "is_visible": window.is_visible,
                    "is_topmost": window.is_topmost
                })
            self._logger.info("窗口配置已保存")
            
            # 3. 恢复所有窗口状态
            self._logger.info("3. 恢复所有窗口状态...")
            for handle, window in self._window_manager._windows.items():
                try:
                    if not window.is_visible and win32gui.IsWindow(handle):
                        win32gui.ShowWindow(handle, win32con.SW_SHOW)
                        self._logger.info(f"已显示窗口: {window.title}")
                    if window.is_topmost and win32gui.IsWindow(handle):
                        win32gui.SetWindowPos(
                            handle, win32con.HWND_NOTOPMOST, 0, 0, 0, 0,
                            win32con.SWP_NOMOVE | win32con.SWP_NOSIZE
                        )
                        self._logger.info(f"已取消置顶: {window.title}")
                except Exception as e:
                    self._logger.error(f"恢复窗口状态失败: {window.title}, 错误: {str(e)}")
            
            # 4. 清理所有快捷键
            self._logger.info("4. 清理所有快捷键...")
            try:
                # 先清理所有窗口的快捷键
                for handle, window in self._window_manager._windows.items():
                    if window.hotkey:
                        self._hotkey_manager.unregister_hotkey(window.hotkey)
                
                # 清理所有全局快捷键
                for hotkey in self._global_hotkeys.values():
                    if hotkey.current:
                        self._hotkey_manager.unregister_hotkey(hotkey.current)
                    self._hotkey_manager.unregister_hotkey(hotkey.default)
                
                # 强制清理所有keyboard库的钩子
                keyboard.unhook_all()  # 解除所有钩子
                if hasattr(keyboard, '_listener') and keyboard._listener:
                    keyboard._listener.stop()  # 停止监听器
                    keyboard._listener = None
                keyboard._hotkeys.clear()  # 清理所有快捷键
                keyboard._pressed_events.clear()  # 清理按键事件
                keyboard._physically_pressed_keys.clear()  # 清理物理按键状态
                keyboard._logically_pressed_keys.clear()  # 清理逻辑按键状态
                
                self._logger.info("快捷键已清理")
            except Exception as e:
                self._logger.error(f"清理快捷键时发生错误: {str(e)}")
            
            # 5. 保存主窗口状态
            self._logger.info("5. 保存主窗口状态...")
            self._save_window_state()
            self._logger.info("主窗口状态已保存")
            
            # 6. 移除托盘图标
            self._logger.info("6. 移除托盘图标...")
            if hasattr(self, 'tray_icon'):
                try:
                    self.tray_icon.hide()
                    self.tray_icon.setParent(None)
                    self.tray_icon.deleteLater()
                    self.tray_icon = None
                    self._logger.info("托盘图标已移除")
                except Exception as e:
                    self._logger.error(f"移除托盘图标时发生错误: {str(e)}")
            
            # 7. 关闭主窗口
            self._logger.info("7. 关闭主窗口...")
            self.hide()
            self.close()
            self._logger.info("主窗口已关闭")
            
            # 8. 确保程序完全退出
            self._logger.info("8. 退出应用程序...")
            app = QApplication.instance()
            app.closeAllWindows()
            
            # 9. 强制结束进程
            self._logger.info("=== 程序退出流程完成，即将强制退出 ===")
            
            # 使用 sys.exit() 而不是 os._exit()，让Python有机会清理资源
            sys.exit(0)
            
        except Exception as e:
            self._logger.error(f"退出程序时发生错误: {str(e)}")
            sys.exit(1)
        
    def closeEvent(self, event: QCloseEvent):
        """处理窗口关闭事件"""
        if event.spontaneous():  # 用户点击关闭按钮
            minimize_to_tray = self._config_manager.get_config().main_window["minimize_to_tray"]
            if minimize_to_tray and self.tray_icon.isVisible():
                self.hide()
                event.ignore()
            else:
                # 如果不最小化到托盘，则直接调用退出逻辑
                self._on_quit()
                event.accept()
            return
                
        # 程序真正退出时保存窗口状态
        self._save_window_state()
        event.accept()
            
    def _on_always_on_top_changed(self, state):
        """处理主窗口置顶状态变更"""
        is_top = state == Qt.Checked
        self.setWindowFlags(
            self.windowFlags() | Qt.WindowStaysOnTopHint
            if is_top
            else self.windowFlags() & ~Qt.WindowStaysOnTopHint
        )
        self.show()
        
        # 保存配置
        self._config_manager.update_main_window_config("always_on_top", is_top)
        
    def _restore_window_state(self, config: AppConfig):
        """
        恢复窗口状态
        
        Args:
            config: 应用程序配置
        """
        # 设置窗口置顶状态
        self.always_on_top_checkbox.setChecked(config.main_window["always_on_top"])
        self._on_always_on_top_changed(
            Qt.Checked if config.main_window["always_on_top"] else Qt.Unchecked
        )
        
        # 恢复窗口位置和大小
        if config.main_window["position"]:
            self.move(QPoint(*config.main_window["position"]))
        if config.main_window["size"]:
            self.resize(QSize(*config.main_window["size"]))
            
    def _restore_saved_windows(self, config: AppConfig):
        """
        恢复保存的窗口配置
        
        Args:
            config: 应用程序配置
        """
        for title, window_config in config.saved_windows.items():
            # 首先通过句柄查找窗口
            handle = window_config.get('handle', 0)
            found = False
            
            if handle and win32gui.IsWindow(handle):
                # 验证句柄对应的窗口标题是否匹配
                current_title = win32gui.GetWindowText(handle)
                if current_title == title:
                    found = True
                    self._logger.info(f"通过句柄找到窗口: {title}")
            
            # 如果通过句柄未找到，尝试通过标题查找
            if not found:
                handle = win32gui.FindWindow(None, title)
                if handle and win32gui.IsWindow(handle):
                    found = True
                    self._logger.info(f"通过标题找到窗口: {title}")
            
            if found:
                # 创建窗口信息
                window_info = WindowInfo(
                    handle=handle,
                    title=title,
                    hotkey=window_config.get("hotkey", ""),
                    is_visible=window_config.get("is_visible", True),
                    is_topmost=window_config.get("is_topmost", False)
                )
                
                # 添加到管理器
                self._window_manager._windows[handle] = window_info
                self._add_window_to_list(window_info)
                
                # 注册快捷键
                if window_info.hotkey:
                    self._hotkey_manager.register_hotkey(
                        window_info.hotkey,
                        lambda h=handle: self._window_manager.toggle_window_visibility(h)
                    )
                    
                # 恢复窗口状态
                if window_info.is_topmost:
                    self._window_manager.toggle_window_topmost(handle)
                if not window_info.is_visible:
                    self._window_manager.toggle_window_visibility(handle)
            else:
                # 将未找到的窗口也添加到列表，但标记为无效
                item = QListWidgetItem(f"{title} (未找到)")
                item.setForeground(QBrush(QColor("red")))
                self.window_list.addItem(item)
                
    def _save_window_state(self):
        """保存窗口状态"""
        self._config_manager.update_main_window_config("position", [
            self.pos().x(),
            self.pos().y()
        ])
        self._config_manager.update_main_window_config("size", [
            self.size().width(),
            self.size().height()
        ])
        
    def _toggle_active_window_topmost(self):
        """切换当前活动窗口的置顶状态"""
        try:
            hwnd = win32gui.GetForegroundWindow()
            if hwnd == self.winId():  # 忽略主窗口
                return
                
            # 如果窗口未被管理，先捕获它
            if hwnd not in self._window_manager._windows:
                window_info = self._window_manager.capture_active_window()
                if window_info:
                    self._add_window_to_list(window_info)
                    
            # 切换置顶状态
            if self._window_manager.toggle_window_topmost(hwnd):
                self._update_window_item(hwnd)
                
        except Exception as e:
            self._logger.error(f"切换窗口置顶状态失败: {str(e)}") 

    def show_status(self, message: str, timeout: int = 3000):
        """
        显示状态栏消息
        
        Args:
            message: 消息内容
            timeout: 显示时间（毫秒）
        """
        self.statusBar.showMessage(message, timeout)
        
    def _check_windows_status(self):
        """检查所有窗口的状态"""
        invalid_windows = []
        for i in range(self.window_list.count()):
            item = self.window_list.item(i)
            handle = item.data(Qt.UserRole)
            window_info = self._window_manager.get_window_info(handle)
            
            if not window_info or not win32gui.IsWindow(handle):
                # 获取原始标题（移除可能的状态标记）
                title = item.text().split(" (")[0]
                
                # 尝试通过标题重新查找窗口
                new_handle = win32gui.FindWindow(None, title)
                if new_handle and win32gui.IsWindow(new_handle):
                    # 更新窗口句柄
                    window_info.handle = new_handle
                    self._window_manager._windows[new_handle] = window_info
                    del self._window_manager._windows[handle]
                    item.setData(Qt.UserRole, new_handle)
                    # 更新配置中的句柄
                    if title in self._config_manager.get_config().saved_windows:
                        self._config_manager.get_config().saved_windows[title]['handle'] = new_handle
                        self._config_manager.save_config()
                    self.show_status(f"已更新窗口句柄: {title}")
                else:
                    # 标记为无效窗口
                    item.setForeground(QBrush(QColor("red")))
                    invalid_windows.append(title)
                    
        if invalid_windows:
            self.show_status(f"发现 {len(invalid_windows)} 个无效窗口，可以点击\"清理无效窗口\"按钮清理")
            
    def _cleanup_invalid_windows(self):
        """清理无效窗口"""
        invalid_count = 0
        for i in range(self.window_list.count() - 1, -1, -1):
            item = self.window_list.item(i)
            handle = item.data(Qt.UserRole)
            title = item.text().split(" (")[0]
            
            if not win32gui.IsWindow(handle):
                # 尝试通过标题重新查找窗口
                new_handle = win32gui.FindWindow(None, title)
                if not new_handle or not win32gui.IsWindow(new_handle):
                    # 删除无效窗口
                    self.window_list.takeItem(i)
                    if handle in self._window_manager._windows:
                        del self._window_manager._windows[handle]
                    self._config_manager.remove_window_config(title)
                    invalid_count += 1
                    
        if invalid_count > 0:
            self.show_status(f"已清理 {invalid_count} 个无效窗口")
        else:
            self.show_status("没有发现无效窗口")
            
    def _on_remove_window(self):
        """删除选中的窗口"""
        item = self.window_list.currentItem()
        if not item:
            self.show_status("请先选择一个窗口")
            return
            
        handle = item.data(Qt.UserRole)
        window_info = self._window_manager.get_window_info(handle)
        if window_info:
            # 解除快捷键绑定
            if window_info.hotkey:
                self._hotkey_manager.unregister_hotkey(window_info.hotkey)
                
            # 从配置文件中移除
            self._config_manager.remove_window_config(window_info.title)
            
            # 从管理器中移除
            self._window_manager.remove_window(handle)
            
        # 从列表中移除
        self.window_list.takeItem(self.window_list.row(item))
        self.show_status("已删除选中窗口")

    def _on_minimize_to_tray_changed(self, state):
        """处理最小化到托盘设置变更"""
        is_minimize = state == Qt.Checked
        self._config_manager.update_main_window_config("minimize_to_tray", is_minimize)
        self.show_status("设置已保存")

    def _on_tray_icon_activated(self, reason):
        """
        处理托盘图标激活事件
        
        Args:
            reason: 激活原因
        """
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_and_activate()  # 双击时显示主窗口 

    def _show_search_window(self):
        """切换搜索窗口的显示/隐藏状态"""
        # 使用线程安全的方式切换搜索窗口的可见性
        self._search_window.request_toggle()
        
    def _on_search_config_changed(self, config: dict):
        """处理搜索配置变更"""
        # 更新配置
        self._config_manager.update_config("window_search", config)
        self._config_manager.save_config()
        
        # 更新窗口索引管理器的扫描间隔
        self._window_index._scan_interval = config.get("scan_interval", 2.0)
        
        # 更新搜索窗口的延迟
        self._search_window._search_delay = config.get("search_delay", 100)
        
    def _on_window_activated(self, hwnd: int):
        """
        处理窗口激活事件
        
        Args:
            hwnd: 窗口句柄
        """
        # 记录窗口激活历史
        self._window_history.record_window_activation(hwnd)

    def _load_config(self):
        """加载配置"""
        # 实现加载配置的逻辑
        pass

    def _save_config(self):
        """保存配置"""
        # 实现保存配置的逻辑
        pass

    def _show_context_menu(self, pos):
        """显示右键菜单"""
        menu = QMenu(self)
        add_tag_action = menu.addAction("添加标签")
        action = menu.exec_(self.window_list.mapToGlobal(pos))
        if action == add_tag_action:
            self._open_tag_input_dialog() 