#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
配置管理模块

该模块负责管理程序的配置信息，包括快捷键设置和窗口状态等。
主要功能：
1. 加载和保存配置文件
2. 提供配置的读写接口
3. 实时同步配置变更

作者：AI Assistant
创建日期：2024-03-20
"""

import json
import os
from typing import Dict, Any
import logging
from dataclasses import dataclass, asdict

@dataclass
class AppConfig:
    """应用程序配置"""
    # 全局快捷键配置
    global_hotkeys: Dict[str, str] = None
    # 主窗口配置
    main_window: Dict[str, Any] = None
    # 已保存的窗口配置
    saved_windows: Dict[str, Dict[str, Any]] = None
    # 窗口搜索配置
    window_search: Dict[str, Any] = None
    
    def __post_init__(self):
        """初始化默认值"""
        if self.global_hotkeys is None:
            self.global_hotkeys = {
                "toggle_main": "ctrl+shift+c",    # 显示/隐藏主窗口
                "capture": "space+c",             # 捕获窗口
                "toggle_topmost": "space+t"       # 切换窗口置顶状态
            }
        if self.main_window is None:
            self.main_window = {
                "always_on_top": True,
                "minimize_to_tray": True,  # 关闭时最小化到托盘
                "position": None,
                "size": None
            }
        if self.saved_windows is None:
            self.saved_windows = {}
        if self.window_search is None:
            self.window_search = {
                "hotkey": "alt+space",  # 默认快捷键
                "search_delay": 100,    # 搜索延迟（毫秒）
                "scan_interval": 2.0,   # 扫描间隔（秒）
                "show_process": True,   # 显示进程名
                "show_desktop": True,   # 显示虚拟桌面信息
                "show_icon": True       # 显示窗口图标
            }

class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_file: str = "config.json"):
        """
        初始化配置管理器
        
        Args:
            config_file: 配置文件路径
        """
        self._config_file = config_file
        self._config = self._load_config()
        self._logger = logging.getLogger(__name__)
        
    def _load_config(self) -> AppConfig:
        """
        加载配置文件
        
        Returns:
            AppConfig: 应用程序配置对象
        """
        try:
            if os.path.exists(self._config_file):
                with open(self._config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 确保main_window中包含所有必要的字段
                    if 'main_window' in data:
                        default_main_window = {
                            "always_on_top": True,
                            "minimize_to_tray": True,
                            "position": None,
                            "size": None
                        }
                        # 使用默认值更新现有配置
                        data['main_window'] = {**default_main_window, **data['main_window']}
                        
                    # 确保window_search中包含所有必要的字段
                    if 'window_search' in data:
                        default_window_search = {
                            "hotkey": "alt+space",
                            "search_delay": 100,
                            "scan_interval": 2.0,
                            "show_process": True,
                            "show_desktop": True,
                            "show_icon": True
                        }
                        # 使用默认值更新现有配置
                        data['window_search'] = {**default_window_search, **data['window_search']}
                        
                    return AppConfig(**data)
        except Exception as e:
            self._logger.error(f"加载配置文件失败: {str(e)}")
        
        return AppConfig()
        
    def save_config(self):
        """保存配置到文件"""
        try:
            with open(self._config_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(self._config), f, indent=4, ensure_ascii=False)
            self._logger.info("配置已保存")
        except Exception as e:
            self._logger.error(f"保存配置文件失败: {str(e)}")
            
    def get_config(self) -> AppConfig:
        """
        获取当前配置
        
        Returns:
            AppConfig: 应用程序配置对象
        """
        return self._config
        
    def update_global_hotkey(self, name: str, hotkey: str):
        """
        更新全局快捷键配置
        
        Args:
            name: 快捷键名称
            hotkey: 快捷键字符串
        """
        self._config.global_hotkeys[name] = hotkey
        self.save_config()
        
    def update_main_window_config(self, key: str, value: Any):
        """
        更新主窗口配置
        
        Args:
            key: 配置键
            value: 配置值
        """
        self._config.main_window[key] = value
        self.save_config()
        
    def update_config(self, section: str, config: Dict[str, Any]):
        """
        更新指定部分的配置
        
        Args:
            section: 配置部分名称
            config: 新的配置
        """
        if hasattr(self._config, section):
            setattr(self._config, section, config)
            self.save_config()
        else:
            self._logger.error(f"配置部分不存在: {section}")
            
    def save_window_config(self, title: str, config: Dict[str, Any]):
        """
        保存窗口配置
        
        Args:
            title: 窗口标题
            config: 窗口配置，包含：
                   - handle: 窗口句柄
                   - hotkey: 快捷键
                   - is_visible: 可见性
                   - is_topmost: 置顶状态
        """
        # 确保配置中包含所有必要字段
        if 'handle' not in config:
            self._logger.warning(f"保存窗口配置时缺少句柄信息: {title}")
            config['handle'] = 0  # 使用0表示无效句柄
            
        self._config.saved_windows[title] = config
        self.save_config()
        
    def remove_window_config(self, title: str):
        """
        移除窗口配置
        
        Args:
            title: 窗口标题
        """
        if title in self._config.saved_windows:
            del self._config.saved_windows[title]
            self.save_config()
            
    def clear_saved_windows(self):
        """清除所有保存的窗口配置"""
        self._config.saved_windows.clear()
        self.save_config() 