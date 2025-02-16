#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
窗口管理模块

该模块负责Windows窗口的操作，包括获取窗口信息、控制窗口显示状态等。
主要功能：
1. 获取活动窗口信息
2. 控制窗口的显示和隐藏
3. 管理窗口列表

作者：AI Assistant
创建日期：2024-03-20
"""

import win32gui
import win32con
import win32api
import win32process
import ctypes
from typing import Dict, Tuple, Optional
import logging
from dataclasses import dataclass
import time

@dataclass
class WindowInfo:
    """窗口信息数据类"""
    handle: int
    title: str
    hotkey: str = ""
    is_visible: bool = True
    is_topmost: bool = False

class WindowManager:
    """
    窗口管理器类
    
    负责管理和操作Windows窗口
    """
    
    def __init__(self):
        """初始化窗口管理器"""
        self._windows: Dict[int, WindowInfo] = {}
        self._logger = logging.getLogger(__name__)
        
    def capture_active_window(self) -> Optional[WindowInfo]:
        """
        捕获当前活动窗口
        
        Returns:
            Optional[WindowInfo]: 如果成功返回窗口信息，否则返回None
        """
        try:
            hwnd = win32gui.GetForegroundWindow()
            if hwnd == 0:
                return None
                
            title = win32gui.GetWindowText(hwnd)
            if not title or hwnd in self._windows:
                return None
                
            window_info = WindowInfo(handle=hwnd, title=title)
            self._windows[hwnd] = window_info
            self._logger.info(f"捕获窗口: {title} (handle: {hwnd})")
            return window_info
            
        except Exception as e:
            self._logger.error(f"捕获窗口失败: {str(e)}")
            return None
            
    def _try_set_foreground_window(self, handle: int) -> bool:
        """
        尝试将窗口设置为前台窗口
        
        Args:
            handle: 窗口句柄
            
        Returns:
            bool: 是否成功
        """
        try:
            # 获取当前前台窗口的线程ID
            foreground_window = win32gui.GetForegroundWindow()
            foreground_thread_id = win32process.GetWindowThreadProcessId(foreground_window)[0]
            
            # 获取目标窗口的线程ID
            target_thread_id = win32process.GetWindowThreadProcessId(handle)[0]
            
            # 连接输入状态
            win32api.AttachThreadInput(target_thread_id, foreground_thread_id, True)
            
            try:
                # 显示窗口并尝试激活
                win32gui.ShowWindow(handle, win32con.SW_SHOW)
                win32gui.SetWindowPos(handle, win32con.HWND_TOP, 0, 0, 0, 0,
                                    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
                win32gui.BringWindowToTop(handle)
                
                # 尝试多次设置前台窗口
                for _ in range(3):
                    if win32gui.SetForegroundWindow(handle):
                        return True
                    time.sleep(0.1)
                    
                return False
                
            finally:
                # 断开输入状态连接
                win32api.AttachThreadInput(target_thread_id, foreground_thread_id, False)
                
        except Exception as e:
            self._logger.debug(f"设置前台窗口失败: {str(e)}")
            return False
            
    def toggle_window_visibility(self, handle: int) -> bool:
        """
        切换窗口的显示状态
        
        Args:
            handle: 窗口句柄
            
        Returns:
            bool: 操作是否成功
        """
        try:
            if handle not in self._windows:
                return False
                
            window = self._windows[handle]
            
            # 检查窗口是否仍然有效
            if not win32gui.IsWindow(handle):
                self._logger.warning(f"窗口已失效: {window.title}")
                return False
                
            if window.is_visible:
                # 隐藏窗口
                win32gui.ShowWindow(handle, win32con.SW_HIDE)
                window.is_visible = False
                self._logger.info(f"隐藏窗口: {window.title}")
                return True
            else:
                # 显示并激活窗口
                if self._try_set_foreground_window(handle):
                    window.is_visible = True
                    self._logger.info(f"显示窗口: {window.title}")
                    return True
                else:
                    # 如果无法激活，至少尝试显示窗口
                    win32gui.ShowWindow(handle, win32con.SW_SHOW)
                    window.is_visible = True
                    self._logger.warning(f"窗口已显示但无法激活: {window.title}")
                    return True
                    
        except Exception as e:
            self._logger.error(f"切换窗口可见性失败: {str(e)}")
            return False
            
    def set_window_hotkey(self, handle: int, hotkey: str) -> bool:
        """
        为窗口设置快捷键
        
        Args:
            handle: 窗口句柄
            hotkey: 快捷键字符串
            
        Returns:
            bool: 设置是否成功
        """
        if handle in self._windows:
            self._windows[handle].hotkey = hotkey
            self._logger.info(f"为窗口 {self._windows[handle].title} 设置快捷键: {hotkey}")
            return True
        return False
        
    def remove_window(self, handle: int) -> bool:
        """
        从管理器中移除窗口
        
        Args:
            handle: 窗口句柄
            
        Returns:
            bool: 移除是否成功
        """
        if handle in self._windows:
            window = self._windows.pop(handle)
            self._logger.info(f"移除窗口: {window.title}")
            return True
        return False
        
    def clear_windows(self):
        """清除所有管理的窗口"""
        self._windows.clear()
        self._logger.info("清除所有窗口")
        
    def get_window_info(self, handle: int) -> Optional[WindowInfo]:
        """
        获取窗口信息
        
        Args:
            handle: 窗口句柄
            
        Returns:
            Optional[WindowInfo]: 窗口信息对象
        """
        return self._windows.get(handle)
        
    def get_all_windows(self) -> Dict[int, WindowInfo]:
        """
        获取所有管理的窗口
        
        Returns:
            Dict[int, WindowInfo]: 窗口句柄到窗口信息的映射
        """
        return self._windows.copy()
        
    def is_window_valid(self, handle: int) -> bool:
        """
        检查窗口是否有效
        
        Args:
            handle: 窗口句柄
            
        Returns:
            bool: 窗口是否有效
        """
        try:
            return win32gui.IsWindow(handle) and handle in self._windows
        except:
            return False
        
    def toggle_window_topmost(self, handle: int) -> bool:
        """
        切换窗口的置顶状态
        
        Args:
            handle: 窗口句柄
            
        Returns:
            bool: 操作是否成功
        """
        try:
            if handle not in self._windows:
                return False
                
            window = self._windows[handle]
            # 获取当前窗口样式
            style = win32gui.GetWindowLong(handle, win32con.GWL_EXSTYLE)
            
            if window.is_topmost:
                # 取消置顶
                win32gui.SetWindowPos(
                    handle, win32con.HWND_NOTOPMOST, 0, 0, 0, 0,
                    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE
                )
                window.is_topmost = False
                self._logger.info(f"取消置顶窗口: {window.title}")
            else:
                # 设置置顶
                win32gui.SetWindowPos(
                    handle, win32con.HWND_TOPMOST, 0, 0, 0, 0,
                    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE
                )
                window.is_topmost = True
                self._logger.info(f"置顶窗口: {window.title}")
                
            return True
            
        except Exception as e:
            self._logger.error(f"切换窗口置顶状态失败: {str(e)}")
            return False 