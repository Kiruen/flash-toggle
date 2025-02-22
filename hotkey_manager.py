#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
快捷键管理模块

该模块负责管理全局快捷键的注册、监听和触发。
主要功能：
1. 注册和管理全局快捷键
2. 处理快捷键事件
3. 提供快捷键绑定和解绑功能
4. 提供快捷键设置对话框

作者：AI Assistant
创建日期：2024-03-20
"""

import keyboard
from typing import Dict, Callable, Optional, Set
import threading
import logging
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QDialogButtonBox, QHBoxLayout
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QKeyEvent

class HotkeyInput(QLineEdit):
    """
    快捷键输入框
    
    用于捕获用户的按键组合，支持：
    - 修饰键 (Ctrl, Alt, Shift, Win)
    - 普通按键
    - 组合键
    """
    
    hotkey_changed = pyqtSignal(str)  # 当快捷键改变时发出信号
    
    def __init__(self, parent=None):
        """初始化快捷键输入框"""
        super().__init__(parent)
        self.setReadOnly(True)  # 设置为只读
        self._keys: Set[int] = set()  # 当前按下的键
        self._modifiers: Set[int] = set()  # 当前按下的修饰键
        
    def keyPressEvent(self, event: QKeyEvent):
        """处理按键按下事件"""
        key = event.key()
        
        # 忽略单独的修饰键
        if key in (Qt.Key.Key_Control, Qt.Key.Key_Alt, Qt.Key.Key_Shift, Qt.Key.Key_Meta):
            return
            
        # 记录按键
        self._keys.add(key)
        
        # 记录修饰键
        modifiers = event.modifiers()
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            self._modifiers.add(Qt.Key.Key_Control)
        if modifiers & Qt.KeyboardModifier.AltModifier:
            self._modifiers.add(Qt.Key.Key_Alt)
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            self._modifiers.add(Qt.Key.Key_Shift)
        if modifiers & Qt.KeyboardModifier.MetaModifier:
            self._modifiers.add(Qt.Key.Key_Meta)
            
        self._update_text()
        event.accept()
        
    def keyReleaseEvent(self, event: QKeyEvent):
        """处理按键释放事件"""
        key = event.key()
        
        # 从集合中移除释放的键
        self._keys.discard(key)
        self._modifiers.discard(key)
        
        self._update_text()
        event.accept()
        
    def _update_text(self):
        """更新显示的文本"""
        parts = []
        
        # 添加修饰键
        if Qt.Key.Key_Control in self._modifiers:
            parts.append("ctrl")
        if Qt.Key.Key_Alt in self._modifiers:
            parts.append("alt")
        if Qt.Key.Key_Shift in self._modifiers:
            parts.append("shift")
        if Qt.Key.Key_Meta in self._modifiers:
            parts.append("win")
            
        # 添加普通键
        for key in self._keys:
            if key not in (Qt.Key.Key_Control, Qt.Key.Key_Alt, Qt.Key.Key_Shift, Qt.Key.Key_Meta):
                key_text = self._get_key_text(key)
                if key_text:
                    parts.append(key_text)
                    
        # 组合成快捷键字符串
        hotkey = "+".join(parts)
        self.setText(hotkey)
        
        # 如果是有效的组合键，发出信号
        if len(parts) > 1:  # 至少需要两个键
            self.hotkey_changed.emit(hotkey)
            
    def _get_key_text(self, key: int) -> Optional[str]:
        """获取按键的文本表示"""
        # 特殊键映射
        special_keys = {
            Qt.Key.Key_Space: "space",
            Qt.Key.Key_Tab: "tab",
            Qt.Key.Key_Return: "enter",
            Qt.Key.Key_Enter: "enter",
            Qt.Key.Key_Escape: "esc",
            Qt.Key.Key_Backspace: "backspace",
            Qt.Key.Key_Delete: "delete",
            Qt.Key.Key_Insert: "insert",
            Qt.Key.Key_Home: "home",
            Qt.Key.Key_End: "end",
            Qt.Key.Key_PageUp: "pageup",
            Qt.Key.Key_PageDown: "pagedown",
            Qt.Key.Key_Up: "up",
            Qt.Key.Key_Down: "down",
            Qt.Key.Key_Left: "left",
            Qt.Key.Key_Right: "right",
            Qt.Key.Key_F1: "f1",
            Qt.Key.Key_F2: "f2",
            Qt.Key.Key_F3: "f3",
            Qt.Key.Key_F4: "f4",
            Qt.Key.Key_F5: "f5",
            Qt.Key.Key_F6: "f6",
            Qt.Key.Key_F7: "f7",
            Qt.Key.Key_F8: "f8",
            Qt.Key.Key_F9: "f9",
            Qt.Key.Key_F10: "f10",
            Qt.Key.Key_F11: "f11",
            Qt.Key.Key_F12: "f12",
        }
        
        if key in special_keys:
            return special_keys[key]
            
        # 字母和数字键
        char = chr(key).lower()
        if char.isalnum():
            return char
            
        return None

class HotkeyDialog(QDialog):
    """
    快捷键设置对话框
    
    用于设置新的快捷键，包括：
    - 快捷键输入框
    - 提示信息
    - 确定/取消按钮
    """
    
    def __init__(self, parent=None):
        """初始化对话框"""
        super().__init__(parent)
        self._hotkey = ""
        self._init_ui()
        
    def _init_ui(self):
        """初始化用户界面"""
        # 设置窗口属性
        self.setWindowTitle("设置快捷键")
        self.setModal(True)
        
        # 创建布局
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # 添加提示标签
        hint = QLabel(
            "请按下新的快捷键组合...\n"
            "支持的按键：\n"
            "- 修饰键：Ctrl, Alt, Shift, Win\n"
            "- 字母和数字键\n"
            "- 功能键：F1-F12\n"
            "- 其他特殊键：Space, Tab, Enter 等",
            self
        )
        hint.setStyleSheet("color: #666;")
        layout.addWidget(hint)
        
        # 添加输入框
        self._input = HotkeyInput(self)
        self._input.setPlaceholderText("按下快捷键...")
        self._input.hotkey_changed.connect(self._on_hotkey_changed)
        layout.addWidget(self._input)
        
        # 添加按钮
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Orientation.Horizontal,
            self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self._ok_button = buttons.button(QDialogButtonBox.Ok)
        self._ok_button.setEnabled(False)
        layout.addWidget(buttons)
        
        # 设置初始大小
        self.resize(300, 200)
        
    def _on_hotkey_changed(self, hotkey: str):
        """处理快捷键变化"""
        self._hotkey = hotkey
        self._ok_button.setEnabled(bool(hotkey))
        
    def get_hotkey(self) -> str:
        """获取设置的快捷键"""
        return self._hotkey

class HotkeyManager:
    """
    快捷键管理器类
    
    负责管理所有的快捷键绑定和事件处理
    """
    
    def __init__(self):
        """初始化快捷键管理器"""
        self._hotkeys: Dict[str, Callable] = {}
        self._lock = threading.Lock()
        self._logger = logging.getLogger(__name__)
        
    def register_hotkey(self, hotkey: str, callback: Callable, description: str = "") -> bool:
        """
        注册新的快捷键
        
        Args:
            hotkey: 快捷键组合（例如：'ctrl+shift+c'）
            callback: 快捷键触发时调用的回调函数
            description: 快捷键的描述信息（可选）
            
        Returns:
            bool: 注册是否成功
        """
        try:
            with self._lock:
                # 如果快捷键已存在，先解除绑定
                if hotkey in self._hotkeys:
                    self.unregister_hotkey(hotkey)
                
                # 注册新的快捷键
                keyboard.add_hotkey(hotkey, callback, suppress=True)
                self._hotkeys[hotkey] = callback
                self._logger.info(f"成功注册快捷键: {hotkey} ({description})")
                return True
        except Exception as e:
            self._logger.error(f"注册快捷键失败: {hotkey}, 错误: {str(e)}")
            return False
            
    def unregister_hotkey(self, hotkey: str) -> bool:
        """
        解除快捷键绑定
        
        Args:
            hotkey: 要解除绑定的快捷键
            
        Returns:
            bool: 解除绑定是否成功
        """
        try:
            with self._lock:
                if hotkey in self._hotkeys:
                    keyboard.remove_hotkey(hotkey)
                    del self._hotkeys[hotkey]
                    self._logger.info(f"成功解除快捷键绑定: {hotkey}")
                return True
        except Exception as e:
            self._logger.error(f"解除快捷键绑定失败: {hotkey}, 错误: {str(e)}")
            return False
            
    def clear_all_hotkeys(self):
        """清除所有已注册的快捷键"""
        with self._lock:
            for hotkey in list(self._hotkeys.keys()):
                self.unregister_hotkey(hotkey)
                
    def is_valid_hotkey(self, hotkey: str) -> bool:
        """
        检查快捷键格式是否有效
        
        Args:
            hotkey: 要检查的快捷键字符串
            
        Returns:
            bool: 快捷键格式是否有效
        """
        try:
            # 测试快捷键是否可以被keyboard库解析
            keyboard.parse_hotkey(hotkey)
            return True
        except:
            return False
            
    def get_registered_hotkeys(self) -> Dict[str, Callable]:
        """
        获取所有已注册的快捷键
        
        Returns:
            Dict[str, Callable]: 快捷键和对应回调函数的字典
        """
        with self._lock:
            return self._hotkeys.copy() 