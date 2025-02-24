#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
窗口操作公共模块

该模块提供了窗口跳转和标签编辑的公共功能，供搜索窗口和配置页面共用。

作者：AI Assistant
创建日期：2024-03-20
"""

import logging
from typing import Optional
from PyQt5.QtWidgets import QInputDialog, QWidget

from .window_index import WindowInfo, WindowIndexManager

def jump_to_window(window: WindowInfo) -> bool:
    """
    跳转到指定窗口
    
    Args:
        window: 要跳转到的窗口信息
        
    Returns:
        bool: 是否成功跳转
    """
    try:
        # 导入win32gui
        import win32gui
        import win32con
        
        # 如果窗口最小化，则恢复
        if window.is_minimized:
            win32gui.ShowWindow(window.hwnd, win32con.SW_RESTORE)
            
        # 激活并前置窗口
        win32gui.SetForegroundWindow(window.hwnd)
        return True
        
    except Exception as e:
        logging.error(f"跳转到窗口失败: {str(e)}")
        return False
        
def edit_window_tags(
    window: WindowInfo,
    window_index: WindowIndexManager,
    parent: Optional[QWidget] = None
) -> bool:
    """
    编辑窗口标签
    
    Args:
        window: 要编辑标签的窗口信息
        window_index: 窗口索引管理器
        parent: 父组件
        
    Returns:
        bool: 是否成功编辑标签
    """
    try:
        # 显示输入对话框
        tags, ok = QInputDialog.getText(
            parent,
            "编辑标签",
            "请输入窗口标签（多个标签用空格分隔）：",
            text=window.tags
        )
        
        if ok:
            # 更新标签
            window_index.update_window_tags(window.handle, tags)
            return True
            
        return False
        
    except Exception as e:
        logging.error(f"编辑窗口标签失败: {str(e)}")
        return False
