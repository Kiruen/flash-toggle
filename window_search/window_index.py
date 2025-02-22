#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
窗口索引管理模块

该模块负责管理和维护所有窗口的索引，包括：
1. 定期扫描所有窗口
2. 维护窗口信息缓存
3. 提供窗口搜索功能
4. 处理窗口状态变化

作者：AI Assistant
创建日期：2024-03-20
"""

import win32gui
import win32process
import win32con
import psutil
import threading
import time
import logging
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from virtual_desktop import VirtualDesktopManager

@dataclass
class WindowInfo:
    """窗口信息数据类"""
    hwnd: int  # 窗口句柄
    title: str  # 窗口标题
    process_id: int  # 进程ID
    process_name: str  # 进程名称
    desktop_id: Optional[str]  # 虚拟桌面ID
    is_visible: bool  # 是否可见
    is_minimized: bool  # 是否最小化
    last_active: float  # 最后活动时间

class WindowIndexManager:
    """
    窗口索引管理器
    
    负责维护所有窗口的索引，提供搜索功能
    """
    
    def __init__(self, virtual_desktop_manager: VirtualDesktopManager):
        """
        初始化窗口索引管理器
        
        Args:
            virtual_desktop_manager: 虚拟桌面管理器实例
        """
        self._logger = logging.getLogger(__name__)
        self._virtual_desktop = virtual_desktop_manager
        
        # 窗口信息缓存
        self._windows: Dict[int, WindowInfo] = {}
        self._lock = threading.Lock()
        
        # 扫描线程
        self._scan_thread = threading.Thread(
            target=self._scan_loop,
            name="WindowScanThread",
            daemon=True
        )
        self._running = True
        self._scan_thread.start()
        self._logger.info("窗口扫描线程已启动")
        
    def _is_valid_window(self, hwnd: int) -> bool:
        """
        检查窗口是否有效
        
        Args:
            hwnd: 窗口句柄
            
        Returns:
            bool: 是否是有效的窗口
        """
        # 检查窗口是否可见
        if not win32gui.IsWindowVisible(hwnd):
            return False
            
        # 检查窗口标题
        try:
            title = win32gui.GetWindowText(hwnd)
            if not title.strip():
                return False
        except:
            return False
            
        # 检查窗口类名
        try:
            class_name = win32gui.GetClassName(hwnd)
            if not class_name:
                return False
                
            # 排除一些特殊窗口
            excluded = {
                "Windows.UI.Core.CoreWindow",  # UWP窗口
                "ApplicationFrameWindow",      # UWP框架窗口
                "Windows.UI.Composition.DesktopWindowContentBridge",  # Win11小组件
                "Shell_TrayWnd",              # 任务栏
                "Progman",                    # 桌面
                "WorkerW",                    # 桌面工作区
            }
            if class_name in excluded:
                return False
        except:
            return False
            
        # 检查窗口样式
        try:
            style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
            if not (style & win32con.WS_VISIBLE):
                return False
                
            if style & win32con.WS_POPUP:  # 弹出窗口
                return False
        except:
            return False
            
        return True
        
    def _scan_windows(self):
        """扫描所有窗口"""
        # 获取所有顶层窗口
        def enum_windows_callback(hwnd: int, windows: Set[int]):
            if self._is_valid_window(hwnd):
                windows.add(hwnd)
            return True
            
        windows = set()
        win32gui.EnumWindows(enum_windows_callback, windows)
        
        # 更新窗口信息
        valid_count = 0
        invalid_count = 0
        
        with self._lock:
            # 移除已不存在的窗口
            for hwnd in list(self._windows.keys()):
                if hwnd not in windows:
                    del self._windows[hwnd]
            
            # 更新或添加窗口信息
            for hwnd in windows:
                try:
                    # 获取窗口标题
                    title = win32gui.GetWindowText(hwnd)
                    
                    # 获取进程信息
                    _, process_id = win32process.GetWindowThreadProcessId(hwnd)
                    try:
                        process = psutil.Process(process_id)
                        process_name = process.name()
                    except:
                        process_name = "未知进程"
                    
                    # 获取窗口状态
                    style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
                    is_visible = bool(style & win32con.WS_VISIBLE)
                    is_minimized = bool(style & win32con.WS_MINIMIZE)
                    
                    # 获取虚拟桌面ID
                    try:
                        desktop_id = self._virtual_desktop.get_window_desktop_id(hwnd)
                        if not desktop_id:  # 如果获取失败，跳过该窗口
                            invalid_count += 1
                            continue
                    except:
                        invalid_count += 1
                        continue
                    
                    # 更新窗口信息
                    self._windows[hwnd] = WindowInfo(
                        hwnd=hwnd,
                        title=title,
                        process_id=process_id,
                        process_name=process_name,
                        desktop_id=desktop_id,
                        is_visible=is_visible,
                        is_minimized=is_minimized,
                        last_active=time.time()
                    )
                    valid_count += 1
                    
                except Exception as e:
                    self._logger.error(f"更新窗口信息失败 (hwnd={hwnd}): {str(e)}")
                    invalid_count += 1
                    continue
        
        self._logger.debug(f"窗口扫描完成: 有效={valid_count}, 失效={invalid_count}")
        
    def _scan_loop(self):
        """窗口扫描循环"""
        while self._running:
            try:
                self._scan_windows()
            except Exception as e:
                self._logger.error(f"窗口扫描失败: {str(e)}")
            time.sleep(2)  # 每2秒扫描一次
            
    def get_all_windows(self) -> List[WindowInfo]:
        """
        获取所有窗口信息
        
        Returns:
            List[WindowInfo]: 窗口信息列表
        """
        with self._lock:
            return list(self._windows.values())
            
    def search_windows(self, query: str) -> List[WindowInfo]:
        """
        搜索窗口
        
        Args:
            query: 搜索关键词
            
        Returns:
            List[WindowInfo]: 匹配的窗口列表
        """
        query = query.lower()
        results = []
        
        with self._lock:
            for window in self._windows.values():
                # 匹配窗口标题
                if query in window.title.lower():
                    results.append(window)
                    continue
                    
                # 匹配进程名
                if query in window.process_name.lower():
                    results.append(window)
                    continue
        
        # 按最后活动时间排序
        results.sort(key=lambda w: w.last_active, reverse=True)
        return results
        
    def stop(self):
        """停止窗口扫描"""
        self._running = False
        if self._scan_thread.is_alive():
            self._scan_thread.join()
            
    def update_window_activity(self, hwnd: int):
        """
        更新窗口活动时间
        
        Args:
            hwnd: 窗口句柄
        """
        with self._lock:
            if hwnd in self._windows:
                self._windows[hwnd].last_active = time.time() 