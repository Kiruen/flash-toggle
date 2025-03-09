#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
窗口实例管理模块

该模块负责集中管理所有窗口实例，提供统一的访问接口。
主要功能：
1. 管理所有窗口实例的生命周期
2. 提供统一的访问接口
3. 确保窗口实例的单例性

作者：AI Assistant
创建日期：2024-03-21
"""

from typing import Optional
from PyQt5.QtWidgets import QWidget
from window_manager import WindowManager
from window_search import WindowIndexManager, SearchWindow
from virtual_desktop import VirtualDesktopManager
from config_manager import ConfigManager
from hotkey_manager import HotkeyManager
from gui import MainWindow

class WindowInstances:
    """窗口实例管理器"""
    
    # 单例实例
    _instance = None
    
    # 窗口实例
    _main_window: Optional[MainWindow] = None
    _search_window: Optional[SearchWindow] = None
    
    # 管理器实例
    _window_manager: Optional[WindowManager] = None
    _window_index: Optional[WindowIndexManager] = None
    _virtual_desktop: Optional[VirtualDesktopManager] = None
    _hotkey_manager: Optional[HotkeyManager] = None
    _config_manager: Optional[ConfigManager] = None
    
    @classmethod
    def initialize(cls) -> None:
        """初始化所有窗口和管理器实例"""
        if cls._instance is not None:
            return
            
        cls._instance = cls()
        
        # 初始化管理器
        cls._virtual_desktop = VirtualDesktopManager()
        cls._config_manager = ConfigManager()
        cls._window_manager = WindowManager()
        cls._hotkey_manager = HotkeyManager()
        cls._window_index = WindowIndexManager(cls._virtual_desktop, cls._config_manager)
        
        # 初始化窗口
        cls._search_window = SearchWindow(cls._window_index)
        cls._search_window.window_selected.connect(cls._window_manager.toggle_window_visibility)
        
        cls._main_window = MainWindow(
            cls._window_manager,
            cls._hotkey_manager,
            cls._window_index,
            cls._search_window
        )
    
    @classmethod
    def main_window(cls) -> Optional[MainWindow]:
        """获取主窗口实例"""
        return cls._main_window
        
    @classmethod
    def search_window(cls) -> Optional[SearchWindow]:
        """获取搜索窗口实例"""
        return cls._search_window
        
    @classmethod
    def window_manager(cls) -> Optional[WindowManager]:
        """获取窗口管理器实例"""
        return cls._window_manager
        
    @classmethod
    def window_index(cls) -> Optional[WindowIndexManager]:
        """获取窗口索引管理器实例"""
        return cls._window_index
        
    @classmethod
    def virtual_desktop(cls) -> Optional[VirtualDesktopManager]:
        """获取虚拟桌面管理器实例"""
        return cls._virtual_desktop
        
    @classmethod
    def hotkey_manager(cls) -> Optional[HotkeyManager]:
        """获取快捷键管理器实例"""
        return cls._hotkey_manager
        
    @classmethod
    def config_manager(cls) -> Optional[ConfigManager]:
        """获取配置管理器实例"""
        return cls._config_manager

    @classmethod
    def get_all_app_window_handles(cls) -> set[int]:
        """
        获取本程序所有窗口的句柄
        
        Returns:
            set[int]: 窗口句柄集合
        """
        handles = set()
        
        # 添加主窗口句柄
        if cls._main_window:
            handles.add(int(cls._main_window.winId()))
            
        # 添加搜索窗口句柄
        if cls._search_window:
            handles.add(int(cls._search_window.winId()))
            
        return handles 