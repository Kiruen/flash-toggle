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
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field
from virtual_desktop import VirtualDesktopManager
from config_manager import ConfigManager
import pinyin

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
    tags: str = ""  # 窗口标签，默认为空字符串

class WindowIndexManager:
    """
    窗口索引管理器
    
    负责维护所有窗口的索引，提供搜索功能
    """
    
    def __init__(self, virtual_desktop_manager: VirtualDesktopManager, config_manager: ConfigManager):
        """
        初始化窗口索引管理器
        
        Args:
            virtual_desktop_manager: 虚拟桌面管理器实例
            config_manager: 配置管理器实例
        """
        self._logger = logging.getLogger(__name__)
        self._virtual_desktop = virtual_desktop_manager
        self._config_manager = config_manager
        self._scan_interval = self._config_manager.get_config().window_search.get('scan_interval', 2)  # 从配置中加载扫描间隔
        
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
        
        Args:cc
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
        try:
            valid_count = 0
            invalid_count = 0
            
            # 获取所有顶级窗口
            def enum_windows_callback(hwnd, _):
                nonlocal valid_count, invalid_count
                
                try:
                    # 跳过不可见窗口
                    style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
                    if not (style & win32con.WS_VISIBLE):
                        invalid_count += 1
                        return True
                        
                    # 跳过无标题窗口
                    title = win32gui.GetWindowText(hwnd)
                    if not title:
                        invalid_count += 1
                        return True
                        
                    # 获取进程信息
                    _, process_id = win32process.GetWindowThreadProcessId(hwnd)
                    try:
                        process = psutil.Process(process_id)
                        process_name = process.name()
                    except:
                        process_name = "未知进程"
                        
                    # 获取窗口状态
                    is_visible = bool(style & win32con.WS_VISIBLE)
                    is_minimized = bool(style & win32con.WS_MINIMIZE)
                    
                    # 获取虚拟桌面ID（静默模式）
                    try:
                        # 确保虚拟桌面管理器初始化（静默模式）
                        if not self._virtual_desktop._ensure_initialized(silent=True):
                            invalid_count += 1
                            return True
                            
                        desktop_id = self._virtual_desktop.get_window_desktop_id(hwnd, silent=True)
                        if not desktop_id:  # 如果获取失败，跳过该窗口
                            invalid_count += 1
                            return True
                    except:
                        invalid_count += 1
                        return True
                        
                    # 更新窗口信息
                    if hwnd in self._windows:
                        # 如果窗口已存在，仅更新需要实时反映的属性
                        existing_window = self._windows[hwnd]
                        existing_window.title = title
                        existing_window.process_id = process_id
                        existing_window.process_name = process_name
                        existing_window.desktop_id = desktop_id
                        existing_window.is_visible = is_visible
                        existing_window.is_minimized = is_minimized
                        existing_window.last_active = time.time()
                    else:
                        # 如果是新窗口，创建新的WindowInfo对象
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
                    
                return True
                
            # 枚举所有顶级窗口
            win32gui.EnumWindows(enum_windows_callback, None)
            
            # 记录扫描结果
            self._logger.info(f"窗口扫描完成: 有效={valid_count}, 无效={invalid_count}")
            
        except Exception as e:
            self._logger.error(f"窗口扫描失败: {str(e)}", exc_info=True)
        
    def _scan_loop(self):
        """窗口扫描循环"""
        while self._running:
            try:
                self._scan_interval = self._config_manager.get_config().window_search.get('scan_interval', 2)  # 从配置中加载扫描间隔
                self._scan_windows()
            except Exception as e:
                self._logger.error(f"窗口扫描失败: {str(e)}")
            time.sleep(self._scan_interval)  # 每次扫描后根据配置的间隔休眠
            
    def get_all_windows(self) -> List[WindowInfo]:
        """
        获取所有窗口信息
        
        Returns:
            List[WindowInfo]: 窗口信息列表
        """
        with self._lock:
            return list(self._windows.values())
            
    def search_windows(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """搜索窗口，支持多关键词和拼音搜索"""
        results = []
        # 将关键词转换为小写
        keywords = [keyword.lower() for keyword in keywords]
        
        for window in self.get_all_windows():
            match_count = 0
            # 检查窗口标题、标签及他们的拼音（转换为小写）
            title = window.title.lower()
            tags = window.tags.lower()
            pinyin_title = pinyin.get(title, format="strip").lower()
            pinyin_tags = pinyin.get(tags, format="strip").lower()
            for keyword in keywords:
                if keyword.lower() in title or keyword.lower() in tags or keyword.lower() in pinyin_title or keyword.lower() in pinyin_tags:
                    match_count += 1
                
            if match_count > 0:
                results.append({
                    'window': window,
                    'match_count': match_count
                })
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