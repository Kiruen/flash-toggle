#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Flash-Toggle 主程序入口

该程序用于管理Windows窗口的显示状态，通过全局快捷键快速切换窗口的显示/隐藏。
主要功能：
1. 捕获活动窗口并管理
2. 为窗口配置显示/隐藏快捷键
3. 提供图形界面和系统托盘支持
4. 窗口快速搜索和跳转

作者：AI Assistant
创建日期：2024-03-20
"""

import sys
import logging
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from window_instances import WindowInstances

from window_manager import WindowManager
from hotkey_manager import HotkeyManager
from window_search import WindowIndexManager, SearchWindow
from virtual_desktop import VirtualDesktopManager
from gui import MainWindow
from config_manager import ConfigManager

def setup_logging():
    """配置日志系统"""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('flash_toggle.log', encoding='utf-8')
        ]
    )

def main():
    """程序入口函数"""
    # 配置日志
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Flash-Toggle 启动")
    
    try:
        # 创建应用实例
        app = QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(False)  # 关闭窗口时不退出应用
        
        # 初始化所有窗口和管理器实例
        WindowInstances.initialize()
        
        # 显示主窗口
        main_window = WindowInstances.main_window()
        if main_window:
            main_window.show()
        
        # 启动应用
        sys.exit(app.exec_())
        
    except Exception as e:
        logger.error(f"程序运行出错: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main() 