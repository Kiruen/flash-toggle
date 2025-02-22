#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
窗口搜索界面

该模块实现了窗口搜索的用户界面，包括：
1. 搜索输入框
2. 候选窗口列表
3. 快捷键绑定
4. 窗口跳转功能

作者：AI Assistant
创建日期：2024-03-20
"""

import sys
import logging
from typing import List, Optional, Callable
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLineEdit, QListWidget,
    QListWidgetItem, QLabel, QHBoxLayout, QFrame
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QKeyEvent, QIcon, QPixmap

from .window_index import WindowInfo, WindowIndexManager

class WindowListItem(QWidget):
    """
    窗口列表项组件
    
    用于在候选列表中显示窗口信息，包括：
    - 窗口图标
    - 窗口标题
    - 进程名称
    - 虚拟桌面信息
    """
    
    def __init__(
        self,
        window: WindowInfo,
        parent: Optional[QWidget] = None
    ):
        """
        初始化窗口列表项
        
        Args:
            window: 窗口元数据
            parent: 父组件
        """
        super().__init__(parent)
        
        # 创建布局
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)
        
        # 添加图标
        icon_label = QLabel(self)
        try:
            # 尝试获取窗口图标
            import win32gui
            import win32ui
            import win32con
            from PIL import Image
            import io
            
            # 获取窗口图标
            icon_handle = win32gui.SendMessage(
                window.handle,
                win32con.WM_GETICON,
                win32con.ICON_SMALL,
                0
            )
            
            if not icon_handle:  # 如果获取小图标失败，尝试获取大图标
                icon_handle = win32gui.SendMessage(
                    window.handle,
                    win32con.WM_GETICON,
                    win32con.ICON_BIG,
                    0
                )
                
            if not icon_handle:  # 如果仍然失败，使用窗口类的图标
                icon_handle = win32gui.GetClassLong(
                    window.handle,
                    win32con.GCL_HICON
                )
                
            if icon_handle:
                # 创建设备上下文
                dc = win32gui.GetDC(0)
                dc_obj = win32ui.CreateDCFromHandle(dc)
                save_dc = dc_obj.CreateCompatibleDC()
                
                # 创建位图
                bmp = win32ui.CreateBitmap()
                bmp.CreateCompatibleBitmap(dc_obj, 16, 16)
                save_dc.SelectObject(bmp)
                
                # 绘制图标
                save_dc.DrawIcon((0, 0), icon_handle)
                
                # 转换为 QPixmap
                bmpstr = bmp.GetBitmapBits(True)
                img = Image.frombuffer(
                    'RGBA', (16, 16),
                    bmpstr, 'raw', 'BGRA', 0, 1
                )
                
                # 保存为字节流
                byte_array = io.BytesIO()
                img.save(byte_array, format='PNG')
                pixmap = QPixmap()
                pixmap.loadFromData(byte_array.getvalue())
                
                # 清理资源
                win32gui.DeleteObject(bmp.GetHandle())
                save_dc.DeleteDC()
                dc_obj.DeleteDC()
                win32gui.ReleaseDC(0, dc)
                
                # 设置图标
                icon_label.setPixmap(pixmap)
            else:
                # 使用默认图标
                icon_label.setText("🪟")
                
        except Exception as e:
            logging.warning(f"获取窗口图标失败: {str(e)}")
            icon_label.setText("🪟")
            
        icon_label.setFixedSize(16, 16)
        layout.addWidget(icon_label)
        
        # 添加标题和进程信息
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        title_label = QLabel(window.title, self)
        title_label.setStyleSheet("font-weight: bold;")
        info_layout.addWidget(title_label)
        
        process_label = QLabel(f"{window.process_name} (PID: {window.process_id})", self)
        process_label.setStyleSheet("color: gray; font-size: 9pt;")
        info_layout.addWidget(process_label)
        
        layout.addLayout(info_layout)
        layout.addStretch()
        
        # 添加虚拟桌面信息
        if window.desktop_id:
            desktop_label = QLabel(f"桌面 {window.desktop_id[-8:]}", self)
            desktop_label.setStyleSheet(
                "color: #666; background: #eee; padding: 2px 5px; border-radius: 3px;"
            )
            layout.addWidget(desktop_label)
            
        # 设置样式
        self.setStyleSheet("""
            QWidget {
                background: transparent;
            }
            QWidget:hover {
                background: rgba(0, 0, 0, 0.05);
            }
        """)

class SearchWindow(QWidget):
    """
    窗口搜索界面
    
    主搜索界面，包含：
    - 搜索输入框
    - 候选窗口列表
    - 快捷键处理
    - 窗口跳转逻辑
    """
    
    # 自定义信号
    window_selected = pyqtSignal(WindowInfo)  # 当用户选择一个窗口时发出
    show_requested = pyqtSignal()  # 请求显示窗口的信号
    
    def __init__(
        self,
        window_index: WindowIndexManager,
        parent: Optional[QWidget] = None
    ):
        """
        初始化搜索窗口
        
        Args:
            window_index: 窗口索引管理器
            parent: 父组件
        """
        super().__init__(parent)
        
        self._logger = logging.getLogger(__name__)
        self._window_index = window_index
        self._search_delay = 100  # 搜索延迟（毫秒）
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._do_search)
        
        # 连接显示信号
        self.show_requested.connect(self._do_show)
        
        self._init_ui()
        
    def _init_ui(self):
        """初始化用户界面"""
        # 设置窗口属性
        self.setWindowTitle("搜索窗口")
        self.setWindowFlags(
            Qt.FramelessWindowHint |  # 无边框
            Qt.Tool |  # 工具窗口
            Qt.WindowStaysOnTopHint  # 置顶
        )
        
        # 创建主布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # 创建搜索框
        self._search_input = QLineEdit(self)
        self._search_input.setPlaceholderText("输入窗口标题搜索...")
        self._search_input.textChanged.connect(self._on_search_text_changed)
        self._search_input.installEventFilter(self)  # 安装事件过滤器
        layout.addWidget(self._search_input)
        
        # 创建分隔线
        line = QFrame(self)
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)
        
        # 创建候选列表
        self._window_list = QListWidget(self)
        self._window_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._window_list.itemActivated.connect(self._on_item_activated)
        self._window_list.setStyleSheet("""
            QListWidget {
                border: none;
                background: white;
            }
            QListWidget::item {
                padding: 5px;
                border-radius: 3px;
            }
            QListWidget::item:selected {
                background: rgba(0, 120, 215, 0.1);
                color: black;
            }
            QListWidget::item:hover {
                background: rgba(0, 0, 0, 0.05);
            }
        """)
        layout.addWidget(self._window_list)
        
        # 设置窗口样式
        self.setStyleSheet("""
            SearchWindow {
                background: white;
                border: 1px solid #ccc;
                border-radius: 5px;
            }
            QLineEdit {
                padding: 8px;
                border: 1px solid #ccc;
                border-radius: 3px;
                font-size: 12pt;
            }
            QLineEdit:focus {
                border-color: #0078d7;
            }
        """)
        
        # 设置初始大小
        self.resize(500, 400)
        
    def _on_search_text_changed(self, text: str):
        """
        处理搜索文本变化
        
        使用定时器延迟执行搜索，避免频繁搜索。
        
        Args:
            text: 搜索文本
        """
        self._search_timer.start(self._search_delay)
        
    def _do_search(self):
        """执行搜索"""
        query = self._search_input.text().strip()
        
        # 清空列表
        self._window_list.clear()
        
        if not query:
            return
            
        # 搜索窗口
        results = self._window_index.search_windows(query)
        
        # 添加结果到列表
        for window in results:
            item = QListWidgetItem(self._window_list)
            item.setData(Qt.ItemDataRole.UserRole, window)
            widget = WindowListItem(window, self._window_list)
            item.setSizeHint(widget.sizeHint())
            self._window_list.addItem(item)
            self._window_list.setItemWidget(item, widget)
            
        # 如果有结果，选中第一项
        if self._window_list.count() > 0:
            self._window_list.setCurrentRow(0)
            
    def _on_item_activated(self, item: QListWidgetItem):
        """
        处理列表项激活
        
        当用户点击或按回车时触发。
        
        Args:
            item: 激活的列表项
        """
        window = item.data(Qt.ItemDataRole.UserRole)
        if window:
            self.window_selected.emit(window)
            self.hide()
            
    def eventFilter(self, obj: QWidget, event) -> bool:
        """
        事件过滤器
        
        处理特殊按键：
        - Esc: 关闭窗口
        - Up/Down: 在列表中移动
        - Enter: 选择当前项
        - Tab: 切换焦点
        
        Args:
            obj: 产生事件的组件
            event: 事件对象
            
        Returns:
            bool: 是否已处理事件
        """
        if obj == self._search_input and isinstance(event, QKeyEvent):
            key = event.key()
            
            if key == Qt.Key.Key_Escape:
                self.hide()
                return True
                
            elif key in (Qt.Key.Key_Up, Qt.Key.Key_Down):
                # 获取当前选中项
                current = self._window_list.currentRow()
                count = self._window_list.count()
                
                if count == 0:
                    return True
                    
                # 计算新的选中项
                if key == Qt.Key.Key_Up:
                    new_index = count - 1 if current <= 0 else current - 1
                else:
                    new_index = 0 if current >= count - 1 else current + 1
                    
                # 设置新的选中项
                self._window_list.setCurrentRow(new_index)
                return True
                
            elif key == Qt.Key.Key_Return:
                # 获取当前选中项
                current = self._window_list.currentItem()
                if current:
                    self._on_item_activated(current)
                return True
                
            elif key == Qt.Key.Key_Tab:
                # 在搜索框和列表之间切换焦点
                if self._window_list.count() > 0:
                    if self._search_input.hasFocus():
                        self._window_list.setFocus()
                    else:
                        self._search_input.setFocus()
                return True
                
        return super().eventFilter(obj, event)
        
    def showEvent(self, event):
        """窗口显示时，清空搜索框并设置焦点"""
        super().showEvent(event)
        self._search_input.clear()
        self._window_list.clear()
        self._search_input.setFocus()
        
    def hideEvent(self, event):
        """窗口隐藏时，清空搜索框和列表"""
        super().hideEvent(event)
        self._search_input.clear()
        self._window_list.clear()
        
    def center_on_screen(self):
        """将窗口居中显示"""
        # 获取屏幕几何信息
        screen = self.screen()
        if not screen:
            return
            
        screen_geometry = screen.geometry()
        
        # 计算居中位置
        x = (screen_geometry.width() - self.width()) // 2
        y = (screen_geometry.height() - self.height()) // 2
        
        # 移动窗口
        self.move(x, y)
        
    def request_show(self):
        """从任何线程安全地请求显示窗口"""
        self.show_requested.emit()
        
    def _do_show(self):
        """在主线程中实际显示窗口"""
        if not self.isVisible():
            self.center_on_screen()
            self.show()
            self.activateWindow()
            self.raise_()
            self._search_input.setFocus() 