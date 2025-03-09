#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
窗口激活历史管理器

该模块实现了窗口激活历史的记录和跳转功能，包括：
1. 记录窗口激活历史
2. 前后跳转功能
3. 循环跳转支持
4. 智能历史管理（类似 IDEA 的前进后退行为）

作者：AI Assistant
创建日期：2024-03-21
"""

import logging
from typing import Optional, List
import win32gui
import win32con
import win32process
import win32api
from collections import deque
import time

class WindowHistoryManager:
    """
    窗口激活历史管理器
    
    使用双端队列记录窗口激活历史，支持前后跳转。
    实现类似 IDEA 的智能历史管理：
    1. 在历史中间位置访问新位置时，会删除当前位置到栈顶的所有记录
    2. 连续访问同一位置只记录一次
    3. 有最大历史记录限制
    4. 在历史中导航时不会记录新的历史
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
            
        # 连续访问同一位置只记录一次
        if self._history and self._history[self._current_index] == hwnd:
            return
            
        # 如果当前不在栈顶，删除当前位置之后的所有记录
        if self._current_index < len(self._history) - 1:
            while len(self._history) > self._current_index + 1:
                self._history.pop()
                
        # 添加新记录
        self._history.append(hwnd)
        self._current_index = len(self._history) - 1
        self._logger.debug(f"记录窗口激活: {hwnd}, 当前历史索引: {self._current_index}")
        
    def _try_set_foreground_window(self, hwnd: int) -> bool:
        """
        尝试将窗口设置为前台窗口
        
        Args:
            hwnd: 窗口句柄
            
        Returns:
            bool: 是否成功
        """
        try:
            # 获取当前前台窗口的线程ID
            foreground_window = win32gui.GetForegroundWindow()
            foreground_thread_id = win32process.GetWindowThreadProcessId(foreground_window)[0]
            
            # 获取目标窗口的线程ID
            target_thread_id = win32process.GetWindowThreadProcessId(hwnd)[0]
            
            # 连接输入状态
            win32process.AttachThreadInput(target_thread_id, foreground_thread_id, True)
            
            try:
                # 显示窗口并尝试激活
                if win32gui.IsIconic(hwnd):  # 如果窗口最小化，先恢复
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                else:
                    win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
                    
                # 将窗口置于前台
                result = win32gui.SetForegroundWindow(hwnd)
                
                # 如果直接设置失败，尝试使用 ALT 键模拟
                if not result:
                    # 模拟按下 ALT 键
                    win32api.keybd_event(win32con.VK_MENU, 0, 0, 0)
                    win32gui.SetForegroundWindow(hwnd)
                    # 释放 ALT 键
                    win32api.keybd_event(win32con.VK_MENU, 0, win32con.KEYEVENTF_KEYUP, 0)
                    
                # 等待窗口激活
                time.sleep(0.1)
                return True
                
            finally:
                # 断开输入状态
                win32process.AttachThreadInput(target_thread_id, foreground_thread_id, False)
                
        except Exception as e:
            self._logger.error(f"设置前台窗口失败 (hwnd={hwnd}): {str(e)}")
            return False
            
    def _jump_to_window(self, hwnd: int) -> bool:
        """
        跳转到指定窗口
        
        Args:
            hwnd: 窗口句柄
            
        Returns:
            bool: 是否跳转成功
        """
        try:
            self._is_jumping = True
            
            # 确保窗口仍然有效
            if not win32gui.IsWindow(hwnd):
                return False
                
            # 尝试激活窗口
            return self._try_set_foreground_window(hwnd)
            
        except Exception as e:
            self._logger.error(f"跳转到窗口失败 (hwnd={hwnd}): {str(e)}")
            return False
            
        finally:
            self._is_jumping = False
            
    def jump_to_previous(self) -> bool:
        """
        跳转到前一个窗口
        
        Returns:
            bool: 是否跳转成功
        """
        if not self._history or self._current_index <= 0:
            return False
            
        # 移动到前一个位置
        self._current_index -= 1
        hwnd = self._history[self._current_index]
        
        # 如果窗口无效，从历史中移除并重试
        if not win32gui.IsWindow(hwnd):
            self._history.remove(hwnd)
            if self._current_index >= len(self._history):
                self._current_index = len(self._history) - 1
            return self.jump_to_previous() if self._history else False
            
        # 跳转到目标窗口
        if self._jump_to_window(hwnd):
            self._logger.debug(f"跳转到前一个窗口: {hwnd}, 新索引: {self._current_index}")
            return True
            
        return False
            
    def jump_to_next(self) -> bool:
        """
        跳转到后一个窗口
        
        Returns:
            bool: 是否跳转成功
        """
        if not self._history or self._current_index >= len(self._history) - 1:
            return False
            
        # 移动到后一个位置
        self._current_index += 1
        hwnd = self._history[self._current_index]
        
        # 如果窗口无效，从历史中移除并重试
        if not win32gui.IsWindow(hwnd):
            self._history.remove(hwnd)
            return self.jump_to_next() if self._history else False
            
        # 跳转到目标窗口
        if self._jump_to_window(hwnd):
            self._logger.debug(f"跳转到后一个窗口: {hwnd}, 新索引: {self._current_index}")
            return True
            
        return False
            
    def clear_history(self):
        """清空历史记录"""
        self._history.clear()
        self._current_index = -1
        self._logger.debug("历史记录已清空") 