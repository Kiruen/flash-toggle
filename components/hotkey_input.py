#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
快捷键输入组件

提供一个可重用的快捷键输入框组件，支持：
1. 直接捕获任意按键组合
2. 实时显示当前按下的按键
3. 支持清除和重置
4. 所见即所得的操作方式
5. 支持快捷键持久化和注册

作者：AI Assistant
创建日期：2024-03-21
"""

import logging
from typing import Set, Optional, Dict, Callable
from PyQt5.QtWidgets import QLineEdit
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QKeyEvent, QFocusEvent

class HotkeyInput(QLineEdit):
    """
    快捷键输入框组件
    
    特点：
    - 直接在输入框中按下快捷键即可捕获
    - 支持任意按键组合
    - 实时显示当前按下的按键
    - 按ESC清除当前输入
    - 失去焦点时自动确认
    - 支持快捷键持久化
    """
    
    # 当快捷键变更时发出信号，参数为：快捷键ID, 新的快捷键文本
    hotkey_changed = pyqtSignal(str, str)
    
    # 占位符文本
    PLACEHOLDER_TEXT = "点击设置快捷键..."
    
    def __init__(self, hotkey_id: str, description: str, initial_hotkey: str = "", callback: Optional[Callable] = None, parent=None):
        """
        初始化快捷键输入框
        
        Args:
            hotkey_id: 快捷键唯一标识
            description: 快捷键描述
            initial_hotkey: 初始快捷键
            callback: 快捷键触发时的回调函数
            parent: 父组件
        """
        super().__init__(parent)
        self._logger = logging.getLogger(__name__)
        
        self._hotkey_id = hotkey_id
        self._description = description
        self._callback = callback
        
        # 设置为只读，防止普通文本输入
        self.setReadOnly(True)
        
        # 设置占位符文本
        self.setPlaceholderText(self.PLACEHOLDER_TEXT)
        
        # 当前按下的按键集合
        self._pressed_keys: Set[int] = set()
        
        # 当前组合键的修饰键状态
        self._modifiers = {
            "ctrl": False,
            "alt": False,
            "shift": False,
            "meta": False
        }
        
        # 设置初始快捷键
        if initial_hotkey:
            self.set_hotkey(initial_hotkey)
        
        # 设置样式
        self.setStyleSheet("""
            QLineEdit {
                background-color: #3E3E3E;
                color: #FFFFFF;
                border: 1px solid #555;
                border-radius: 3px;
                padding: 5px;
                min-height: 25px;
            }
            QLineEdit:focus {
                border-color: #0078D7;
            }
            QLineEdit::placeholder {
                color: #888;
            }
        """)
        
        # 设置工具提示
        self.setToolTip(f"{description}\n当前快捷键: {initial_hotkey or '未设置'}")
        
    def keyPressEvent(self, event: QKeyEvent):
        """
        处理按键按下事件
        
        Args:
            event: 按键事件
        """
        key = event.key()
        modifiers = event.modifiers()
        
        # 如果是ESC键，清除当前输入
        if key == Qt.Key_Escape:
            self.clear_hotkey()
            return
            
        # 更新修饰键状态
        self._modifiers["ctrl"] = bool(modifiers & Qt.ControlModifier)
        self._modifiers["alt"] = bool(modifiers & Qt.AltModifier)
        self._modifiers["shift"] = bool(modifiers & Qt.ShiftModifier)
        self._modifiers["meta"] = bool(modifiers & Qt.MetaModifier)
        
        # 记录按下的按键
        if key not in self._pressed_keys:
            self._pressed_keys.add(key)
            self._update_display()
            
    def keyReleaseEvent(self, event: QKeyEvent):
        """
        处理按键释放事件
        
        Args:
            event: 按键事件
        """
        key = event.key()
        
        # 从按下的按键集合中移除
        if key in self._pressed_keys:
            self._pressed_keys.remove(key)
            
        # 如果所有按键都已释放，发出信号
        if not self._pressed_keys:
            hotkey = self.get_hotkey()
            if hotkey:
                self.hotkey_changed.emit(self._hotkey_id, hotkey)
            
        self._update_display()
        
    def focusOutEvent(self, event: QFocusEvent):
        """
        处理失去焦点事件
        
        Args:
            event: 焦点事件
        """
        super().focusOutEvent(event)
        
        # 如果有未释放的按键，发出最后的组合
        if self._pressed_keys:
            hotkey = self.get_hotkey()
            if hotkey:
                self.hotkey_changed.emit(self._hotkey_id, hotkey)
            self._pressed_keys.clear()
            
    def _update_display(self):
        """更新显示的快捷键文本"""
        keys = []
        
        # 添加修饰键
        if self._modifiers["ctrl"]:
            keys.append("ctrl")
        if self._modifiers["alt"]:
            keys.append("alt")
        if self._modifiers["shift"]:
            keys.append("shift")
        if self._modifiers["meta"]:
            keys.append("meta")
            
        # 添加其他按键
        for key in self._pressed_keys:
            if key not in [Qt.Key_Control, Qt.Key_Alt, Qt.Key_Shift, Qt.Key_Meta]:
                key_text = self._get_key_text(key)
                if key_text and key_text not in keys:
                    keys.append(key_text)
                    
        # 更新显示文本
        if keys:
            hotkey = "+".join(keys)
            self.setText(hotkey)
            self.setToolTip(f"{self._description}\n当前快捷键: {hotkey}")
        else:
            self.clear()
            self.setToolTip(f"{self._description}\n当前快捷键: 未设置")
            
    def _get_key_text(self, key: int) -> str:
        """
        获取按键的文本表示
        
        Args:
            key: Qt按键代码
            
        Returns:
            str: 按键的文本表示
        """
        try:
            # 数字键
            if Qt.Key_0 <= key <= Qt.Key_9:
                return str(key - Qt.Key_0)
                
            # 字母键
            if Qt.Key_A <= key <= Qt.Key_Z:
                return chr(key).lower()
                
            # 功能键
            if Qt.Key_F1 <= key <= Qt.Key_F35:
                return f"f{key - Qt.Key_F1 + 1}"
                
            # 小键盘数字键
            if Qt.Key_0 <= key <= Qt.Key_9:
                return f"num{key - Qt.Key_0}"
                
            # 特殊按键映射
            special_keys = {
                Qt.Key_Tab: "tab",
                Qt.Key_Return: "enter",
                Qt.Key_Enter: "enter",
                Qt.Key_Space: "space",
                Qt.Key_Backspace: "backspace",
                Qt.Key_Delete: "delete",
                Qt.Key_Insert: "insert",
                Qt.Key_Home: "home",
                Qt.Key_End: "end",
                Qt.Key_PageUp: "pageup",
                Qt.Key_PageDown: "pagedown",
                Qt.Key_Escape: "esc",
                Qt.Key_Print: "print",
                Qt.Key_ScrollLock: "scrolllock",
                Qt.Key_Pause: "pause",
                Qt.Key_Menu: "menu",
                Qt.Key_Help: "help",
                Qt.Key_Left: "left",
                Qt.Key_Right: "right",
                Qt.Key_Up: "up",
                Qt.Key_Down: "down",
                Qt.Key_CapsLock: "capslock",
                Qt.Key_NumLock: "numlock",
                
                # 符号键
                Qt.Key_Plus: "+",
                Qt.Key_Minus: "-",
                Qt.Key_Asterisk: "*",
                Qt.Key_Slash: "/",
                Qt.Key_Backslash: "\\",
                Qt.Key_Period: ".",
                Qt.Key_Comma: ",",
                Qt.Key_Semicolon: ";",
                Qt.Key_Colon: ":",
                Qt.Key_At: "@",
                Qt.Key_NumberSign: "#",
                Qt.Key_Dollar: "$",
                Qt.Key_Percent: "%",
                Qt.Key_Ampersand: "&",
                Qt.Key_Equal: "=",
                Qt.Key_QuoteDbl: "\"",
                Qt.Key_Apostrophe: "'",
                Qt.Key_BracketLeft: "[",
                Qt.Key_BracketRight: "]",
                Qt.Key_BraceLeft: "{",
                Qt.Key_BraceRight: "}",
                Qt.Key_ParenLeft: "(",
                Qt.Key_ParenRight: ")",
                Qt.Key_Less: "<",
                Qt.Key_Greater: ">",
                Qt.Key_Question: "?",
                Qt.Key_Bar: "|",
                Qt.Key_AsciiTilde: "~",
                Qt.Key_AsciiCircum: "^",
                Qt.Key_Underscore: "_",
                Qt.Key_QuoteLeft: "`",
                Qt.Key_Exclam: "!",
            }
            
            if key in special_keys:
                return special_keys[key]
                
            # 如果是未知按键，尝试获取原始按键文本
            return chr(key).lower() if 32 <= key <= 126 else f"key_{key}"
            
        except Exception as e:
            self._logger.warning(f"处理按键文本时出错 (key={key}): {e}")
            return f"key_{key}"
        
    def get_hotkey(self) -> str:
        """
        获取当前快捷键
        
        Returns:
            str: 当前快捷键的文本表示，如果未设置则返回空字符串
        """
        text = self.text()
        return "" if text == self.PLACEHOLDER_TEXT else text
        
    def set_hotkey(self, hotkey: str):
        """
        设置快捷键
        
        Args:
            hotkey: 快捷键文本
        """
        if not hotkey:
            self.clear()
            self.setToolTip(f"{self._description}\n当前快捷键: 未设置")
        else:
            self.setText(hotkey)
            self.setToolTip(f"{self._description}\n当前快捷键: {hotkey}")
        
    def clear_hotkey(self):
        """清除当前快捷键"""
        self.clear()
        self._pressed_keys.clear()
        self._modifiers = {k: False for k in self._modifiers}
        self.setToolTip(f"{self._description}\n当前快捷键: 未设置")
        self.hotkey_changed.emit(self._hotkey_id, "") 