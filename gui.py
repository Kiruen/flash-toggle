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
                           QGridLayout, QCheckBox)
from PyQt5.QtCore import Qt, QSize, pyqtSignal, QPoint, QSize
from PyQt5.QtGui import QIcon, QCloseEvent
import keyboard
from typing import Optional, Dict, Callable
import logging
from dataclasses import dataclass
import win32gui

from window_manager import WindowManager, WindowInfo
from hotkey_manager import HotkeyManager
from config_manager import ConfigManager, AppConfig

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
    
    hotkey_changed = pyqtSignal(str) 
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setPlaceholderText("点击此处按下快捷键")
        self._keys = set()
        
    def keyPressEvent(self, event):
        """处理按键按下事件"""
        if event.key() == Qt.Key_Escape:
            self.clear()
            self._keys.clear()
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
                self.hotkey_changed.emit(self.text())
                
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
    
    def __init__(self, window_manager: WindowManager, hotkey_manager: HotkeyManager):
        """
        初始化主窗口
        
        Args:
            window_manager: 窗口管理器实例
            hotkey_manager: 快捷键管理器实例
        """
        super().__init__()
        
        self._window_manager = window_manager
        self._hotkey_manager = hotkey_manager
        self._config_manager = ConfigManager()
        self._logger = logging.getLogger(__name__)
        
        # 加载配置
        config = self._config_manager.get_config()
        
        # 初始化全局快捷键配置
        self._global_hotkeys = {
            "toggle_main": GlobalHotkey(
                "toggle_main", "显示/隐藏主窗口",
                config.global_hotkeys["toggle_main"], "",
                self._toggle_main_window
            ),
            "capture": GlobalHotkey(
                "capture", "捕获当前窗口",
                config.global_hotkeys["capture"], "",
                self._on_capture_window
            ),
            "toggle_topmost": GlobalHotkey(
                "toggle_topmost", "切换当前窗口置顶状态",
                config.global_hotkeys["toggle_topmost"], "",
                self._toggle_active_window_topmost
            )
        }
        
        self._init_ui()
        self._setup_tray_icon()
        self._setup_global_hotkeys()
        
        # 恢复窗口状态
        self._restore_window_state(config)
        
        # 恢复保存的窗口配置
        self._restore_saved_windows(config)
        
    def _init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("Flash-Toggle")
        self.setMinimumSize(500, 600)
        
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
        layout.addWidget(QLabel("已捕获的窗口:"))
        layout.addWidget(self.window_list)
        
        # 创建快捷键配置区域
        hotkey_layout = QHBoxLayout()
        self.hotkey_input = HotkeyInput()
        self.hotkey_input.hotkey_changed.connect(self._on_hotkey_input_changed)
        self.set_hotkey_btn = QPushButton("设置快捷键")
        self.set_hotkey_btn.clicked.connect(self._on_set_hotkey)
        self.clear_hotkey_btn = QPushButton("清除快捷键")
        self.clear_hotkey_btn.clicked.connect(self._on_clear_hotkey)
        hotkey_layout.addWidget(self.hotkey_input)
        hotkey_layout.addWidget(self.set_hotkey_btn)
        hotkey_layout.addWidget(self.clear_hotkey_btn)
        layout.addLayout(hotkey_layout)
        
        # 创建底部按钮
        button_layout = QHBoxLayout()
        clear_btn = QPushButton("清除列表")
        clear_btn.clicked.connect(self._on_clear_list)
        button_layout.addWidget(clear_btn)
        layout.addLayout(button_layout)
        
    def _init_hotkey_tab(self, tab: QWidget):
        """初始化快捷键设置标签页"""
        layout = QGridLayout(tab)
        
        # 添加说明标签
        layout.addWidget(QLabel("全局快捷键设置:"), 0, 0, 1, 2)
        
        # 为每个全局快捷键创建设置行
        row = 1
        for hotkey in self._global_hotkeys.values():
            layout.addWidget(QLabel(f"{hotkey.description}:"), row, 0)
            
            hotkey_layout = QHBoxLayout()
            hotkey_input = HotkeyInput()
            hotkey_input.setText(hotkey.current or hotkey.default)
            hotkey_input.hotkey_changed.connect(
                lambda h, n=hotkey.name: self._on_global_hotkey_changed(n, h)
            )
            
            clear_btn = QPushButton("重置")
            clear_btn.clicked.connect(
                lambda _, n=hotkey.name: self._reset_global_hotkey(n)
            )
            
            hotkey_layout.addWidget(hotkey_input)
            hotkey_layout.addWidget(clear_btn)
            layout.addLayout(hotkey_layout, row, 1)
            row += 1
            
        # 添加弹性空间
        layout.setRowStretch(row, 1)
        
    def _setup_global_hotkeys(self):
        """设置全局快捷键"""
        for hotkey in self._global_hotkeys.values():
            self._hotkey_manager.register_hotkey(
                hotkey.current or hotkey.default,
                hotkey.callback
            )
            
    def _on_global_hotkey_changed(self, name: str, hotkey: str):
        """
        处理全局快捷键变更
        
        Args:
            name: 快捷键配置名称
            hotkey: 新的快捷键
        """
        if not hotkey or not self._hotkey_manager.is_valid_hotkey(hotkey):
            return
            
        config = self._global_hotkeys[name]
        old_hotkey = config.current or config.default
        
        # 更新快捷键
        if self._hotkey_manager.register_hotkey(hotkey, config.callback):
            self._hotkey_manager.unregister_hotkey(old_hotkey)
            config.current = hotkey
            
            # 保存配置
            self._config_manager.update_global_hotkey(name, hotkey)
            QMessageBox.information(self, "成功", "快捷键设置成功")
            
    def _reset_global_hotkey(self, name: str):
        """
        重置全局快捷键为默认值
        
        Args:
            name: 快捷键配置名称
        """
        config = self._global_hotkeys[name]
        if config.current:
            self._hotkey_manager.unregister_hotkey(config.current)
            config.current = ""
            self._hotkey_manager.register_hotkey(config.default, config.callback)
            
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
            
    def _on_set_hotkey(self):
        """处理设置快捷键事件"""
        item = self.window_list.currentItem()
        if not item:
            QMessageBox.warning(self, "错误", "请先选择一个窗口")
            return
            
        handle = item.data(Qt.UserRole)
        window_info = self._window_manager.get_window_info(handle)
        if not window_info:
            return
            
        hotkey = self.hotkey_input.text().strip()
        if not hotkey:
            QMessageBox.warning(self, "错误", "请输入快捷键")
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
            QMessageBox.information(self, "成功", "快捷键设置成功")
            
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
            self._update_window_item(handle)
            
    def _toggle_main_window(self):
        """切换主窗口显示状态"""
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.activateWindow()
            
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
        
        # 创建托盘菜单
        tray_menu = QMenu()
        show_action = tray_menu.addAction("显示")
        show_action.triggered.connect(self.show)
        quit_action = tray_menu.addAction("退出")
        quit_action.triggered.connect(self._on_quit)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        
    def _on_quit(self):
        """处理退出事件"""
        # 保存窗口配置
        for handle, window in self._window_manager._windows.items():
            self._config_manager.save_window_config(window.title, {
                "hotkey": window.hotkey,
                "is_visible": window.is_visible,
                "is_topmost": window.is_topmost
            })
            
        # 清理资源
        self._hotkey_manager.clear_all_hotkeys()
        self.tray_icon.hide()
        self.close()
        QApplication.quit()  # 确保应用程序完全退出
        
    def closeEvent(self, event: QCloseEvent):
        """处理窗口关闭事件"""
        if self.tray_icon.isVisible():
            self.hide()
            event.ignore()
        else:
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
            # 尝试找到窗口
            hwnd = win32gui.FindWindow(None, title)
            if hwnd and win32gui.IsWindow(hwnd):
                # 创建窗口信息
                window_info = WindowInfo(
                    handle=hwnd,
                    title=title,
                    hotkey=window_config.get("hotkey", ""),
                    is_visible=window_config.get("is_visible", True),
                    is_topmost=window_config.get("is_topmost", False)
                )
                
                # 添加到管理器
                self._window_manager._windows[hwnd] = window_info
                self._add_window_to_list(window_info)
                
                # 注册快捷键
                if window_info.hotkey:
                    self._hotkey_manager.register_hotkey(
                        window_info.hotkey,
                        lambda h=hwnd: self._window_manager.toggle_window_visibility(h)
                    )
                    
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