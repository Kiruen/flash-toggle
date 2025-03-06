#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
窗口激活历史管理器

该模块实现了窗口激活历史的记录和跳转功能，包括：
1. 记录窗口激活历史
2. 前后跳转功能
3. 循环跳转支持

作者：AI Assistant
创建日期：2024-03-21
"""

import logging
from typing import Optional, List
import win32gui
import win32con
from collections import deque

class WindowHistoryManager:
    """
    窗口激活历史管理器
    
    使用双端队列记录窗口激活历史，支持前后循环跳转
    """
    
    def __init__(self, max_history: int = 50):
        """
        初始化历史管理器
        
        Args:
            max_history: 最大历史记录数
        """
        self._logger = logging.getLogger(__name__)
        self._history = deque(maxlen=max_history)  # 使用双端队列存储历史
        self._current_index = -1  # 当前位置
        self._is_jumping = False  # 是否正在执行跳转（防止跳转时的窗口激活被记录）
        
    def record_window_activation(self, hwnd: int):
        """
        记录窗口激活
        
        Args:
            hwnd: 窗口句柄
        """
        if self._is_jumping or not hwnd or not win32gui.IsWindow(hwnd):
            return
            
        # 如果是重复激活最后一个窗口，不记录
        if self._history and self._history[-1] == hwnd:
            return
            
        # 添加到历史
        self._history.append(hwnd)
        self._current_index = len(self._history) - 1
        self._logger.debug(f"记录窗口激活: {hwnd}, 当前索引: {self._current_index}")
        
    def jump_to_previous(self) -> bool:
        """
        跳转到前一个窗口
        
        Returns:
            bool: 是否跳转成功
        """
        if not self._history:
            return False
            
        try:
            self._is_jumping = True
            
            # 计算目标索引（循环）
            target_index = (self._current_index - 1) % len(self._history)
            hwnd = self._history[target_index]
            
            # 确保窗口仍然有效
            if not win32gui.IsWindow(hwnd):
                self._history.remove(hwnd)
                return self.jump_to_previous()
                
            # 激活窗口
            if win32gui.IsIconic(hwnd):  # 如果窗口最小化，先恢复
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
            
            self._current_index = target_index
            self._logger.debug(f"跳转到前一个窗口: {hwnd}, 新索引: {self._current_index}")
            return True
            
        except Exception as e:
            self._logger.error(f"跳转到前一个窗口失败: {str(e)}")
            return False
            
        finally:
            self._is_jumping = False
            
    def jump_to_next(self) -> bool:
        """
        跳转到后一个窗口
        
        Returns:
            bool: 是否跳转成功
        """
        if not self._history:
            return False
            
        try:
            self._is_jumping = True
            
            # 计算目标索引（循环）
            target_index = (self._current_index + 1) % len(self._history)
            hwnd = self._history[target_index]
            
            # 确保窗口仍然有效
            if not win32gui.IsWindow(hwnd):
                self._history.remove(hwnd)
                return self.jump_to_next()
                
            # 激活窗口
            if win32gui.IsIconic(hwnd):  # 如果窗口最小化，先恢复
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
            
            self._current_index = target_index
            self._logger.debug(f"跳转到后一个窗口: {hwnd}, 新索引: {self._current_index}")
            return True
            
        except Exception as e:
            self._logger.error(f"跳转到后一个窗口失败: {str(e)}")
            return False
            
        finally:
            self._is_jumping = False
            
    def clear_history(self):
        """清空历史记录"""
        self._history.clear()
        self._current_index = -1
        self._logger.debug("历史记录已清空") 