#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
窗口搜索模块

该模块提供了窗口搜索和跳转功能，包括：
1. 窗口索引管理
2. 搜索界面
3. 配置界面
4. 窗口跳转逻辑

作者：AI Assistant
创建日期：2024-03-20
"""

from .window_index import WindowInfo, WindowIndexManager
from .search_window import SearchWindow
from .config_page import SearchConfigPage

__all__ = [
    'WindowInfo',
    'WindowIndexManager',
    'SearchWindow',
    'SearchConfigPage'
] 