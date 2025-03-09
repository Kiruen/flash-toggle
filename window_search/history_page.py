#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
窗口历史记录展示页面

该模块实现了窗口历史记录的可视化界面，包括：
1. 历史堆栈列表
2. 当前位置指示
3. 实时更新功能

作者：AI Assistant
创建日期：2024-03-21
"""

import logging
from typing import Optional
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QLabel, QHeaderView, QFrame, QMenu
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QBrush
import win32gui

from .window_history import WindowHistoryManager

class HistoryPage(QWidget):
    """窗口历史记录展示页面"""
    
    def __init__(
        self,
        window_history: WindowHistoryManager,
        parent: Optional[QWidget] = None
    ):
        """
        初始化历史记录页面
        
        Args:
            window_history: 窗口历史管理器实例
            parent: 父组件
        """
        super().__init__(parent)
        self._logger = logging.getLogger(__name__)
        self._window_history = window_history
        
        # 初始化界面
        self._init_ui()
        
        # 设置定时更新
        self._update_timer = QTimer(self)
        self._update_timer.timeout.connect(self._update_history_list)
        self._update_timer.start(1000)  # 每秒更新一次
        
    def _init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)
        
        # 添加说明标签
        help_text = QLabel(
            "窗口历史记录列表，显示最近激活的窗口和当前位置。\n"
            "使用全局快捷键 Ctrl+Alt+← 和 Ctrl+Alt+→ 在历史记录中前进和后退。\n"
            "双击列表项可以直接跳转到对应窗口。右键点击可以移除记录。",
            self
        )
        help_text.setStyleSheet("""
            color: #CCC;
            font-size: 9pt;
            margin-top: 10px;
            padding: 10px;
            background-color: #3A3A3A;
            border-radius: 5px;
        """)
        layout.addWidget(help_text)
        
        # 创建历史记录表格
        self._history_table = QTableWidget(self)
        self._history_table.setColumnCount(4)  # 增加一列用于显示句柄
        self._history_table.setHorizontalHeaderLabels(["窗口标题", "句柄", "状态", "位置"])
        
        # 设置表格样式
        self._history_table.setFrameShape(QFrame.NoFrame)
        self._history_table.setAlternatingRowColors(True)
        self._history_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._history_table.setSelectionMode(QTableWidget.SingleSelection)
        self._history_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._history_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self._history_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self._history_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        
        # 设置表格样式
        self._history_table.setStyleSheet("""
            QTableWidget {
                background-color: #2E2E2E;
                gridline-color: #555;
                color: #FFF;
            }
            QTableWidget::item {
                color: #FFF;
                background-color: transparent;
            }
            QTableWidget::item:selected {
                background-color: #0078D7;
            }
            QTableWidget::item:alternate {
                background-color: #333333;
            }
            QHeaderView::section {
                background-color: #3E3E3E;
                color: #FFF;
                padding: 5px;
                border: none;
                border-right: 1px solid #555;
                border-bottom: 1px solid #555;
            }
        """)
        
        # 连接双击信号
        self._history_table.itemDoubleClicked.connect(self._on_item_double_clicked)
        
        # 添加右键菜单
        self._history_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self._history_table.customContextMenuRequested.connect(self._show_context_menu)
        
        layout.addWidget(self._history_table)
        
        # 首次更新列表
        self._update_history_list()
        
    def _update_history_list(self):
        """更新历史记录列表"""
        if not hasattr(self._window_history, '_history'):
            return
            
        history = list(self._window_history._history)
        current_index = self._window_history._current_index
        
        self._history_table.setRowCount(len(history))
        
        for i, hwnd in enumerate(history):
            try:
                # 获取窗口标题
                title = win32gui.GetWindowText(hwnd)
                
                # 检查窗口状态
                is_valid = win32gui.IsWindow(hwnd)
                is_visible = win32gui.IsWindowVisible(hwnd)
                is_iconic = win32gui.IsIconic(hwnd)
                
                # 设置窗口标题
                title_item = QTableWidgetItem(title or f"<无标题>")
                if not is_valid:
                    title_item.setForeground(QBrush(QColor("#FF6B6B")))
                self._history_table.setItem(i, 0, title_item)
                
                # 设置句柄
                hwnd_item = QTableWidgetItem(f"0x{hwnd:08X}")
                self._history_table.setItem(i, 1, hwnd_item)
                
                # 设置状态
                status = []
                if not is_valid:
                    status.append("已失效")
                if not is_visible:
                    status.append("已隐藏")
                if is_iconic:
                    status.append("最小化")
                status_text = "、".join(status) if status else "正常"
                status_item = QTableWidgetItem(status_text)
                self._history_table.setItem(i, 2, status_item)
                
                # 设置位置指示
                position = ""
                if i == current_index:
                    position = "◀ 当前"
                    # 设置当前行的背景色
                    for col in range(4):
                        item = self._history_table.item(i, col)
                        if item:
                            item.setBackground(QBrush(QColor(0, 120, 215, 50)))
                position_item = QTableWidgetItem(position)
                self._history_table.setItem(i, 3, position_item)
                
            except Exception as e:
                self._logger.error(f"更新历史记录项失败 (hwnd={hwnd}): {str(e)}")
                # 添加错误项
                self._history_table.setItem(i, 0, QTableWidgetItem(f"错误"))
                self._history_table.setItem(i, 1, QTableWidgetItem(f"0x{hwnd:08X}"))
                self._history_table.setItem(i, 2, QTableWidgetItem("错误"))
                self._history_table.setItem(i, 3, QTableWidgetItem(""))
                
    def _on_item_double_clicked(self, item):
        """处理双击事件"""
        row = item.row()
        if 0 <= row < len(self._window_history._history):
            hwnd = self._window_history._history[row]
            if win32gui.IsWindow(hwnd):
                # 跳转到目标窗口并更新当前索引
                if self._window_history._jump_to_window(hwnd):
                    self._window_history._current_index = row
                    self._update_history_list()  # 更新显示
                    
    def _show_context_menu(self, pos):
        """显示右键菜单"""
        menu = QMenu(self)
        remove_action = menu.addAction("从历史记录中移除")
        
        action = menu.exec_(self._history_table.mapToGlobal(pos))
        if action == remove_action:
            self._remove_selected_item()
            
    def _remove_selected_item(self):
        """移除选中的历史记录项"""
        row = self._history_table.currentRow()
        if row >= 0:
            history = list(self._window_history._history)
            if 0 <= row < len(history):
                hwnd = history[row]
                try:
                    self._window_history._history.remove(hwnd)
                    if self._window_history._current_index >= row:
                        self._window_history._current_index = max(0, self._window_history._current_index - 1)
                    self._update_history_list()
                except ValueError:
                    pass 