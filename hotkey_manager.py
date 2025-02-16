#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
快捷键管理模块

该模块负责管理全局快捷键的注册、监听和触发。
主要功能：
1. 注册和管理全局快捷键
2. 处理快捷键事件
3. 提供快捷键绑定和解绑功能

作者：AI Assistant
创建日期：2024-03-20
"""

import keyboard
from typing import Dict, Callable
import threading
import logging

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
        
    def register_hotkey(self, hotkey: str, callback: Callable) -> bool:
        """
        注册新的快捷键
        
        Args:
            hotkey: 快捷键组合（例如：'ctrl+shift+c'）
            callback: 快捷键触发时调用的回调函数
            
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
                self._logger.info(f"成功注册快捷键: {hotkey}")
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