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
    QListWidgetItem, QLabel, QHBoxLayout, QFrame, QMenu, QInputDialog
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
        matched_title: str = None,
        is_history_match: bool = False,
        parent: Optional[QWidget] = None
    ):
        """
        初始化窗口列表项
        
        Args:
            window: 窗口元数据
            matched_title: 匹配的标题
            is_history_match: 是否为历史标题匹配
            parent: 父组件
        """
        super().__init__(parent)
        
        # 创建布局
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)  # 调整边距
        layout.setSpacing(12)  # 增加间距
        
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
                window.hwnd,
                win32con.WM_GETICON,
                win32con.ICON_SMALL,
                0
            )
            
            if not icon_handle:  # 如果获取小图标失败，尝试获取大图标
                icon_handle = win32gui.SendMessage(
                    window.hwnd,
                    win32con.WM_GETICON,
                    win32con.ICON_BIG,
                    0
                )
                
            if not icon_handle:  # 如果仍然失败，使用窗口类的图标
                icon_handle = win32gui.GetClassLong(
                    window.hwnd,
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
                # 设置固定尺寸，确保图标不会太大
                icon_label.setFixedSize(10, 10)
                icon_label.setScaledContents(True)
            else:
                # 使用默认图标
                icon_label.setText("🪟")
                icon_label.setStyleSheet("font-size: 14px;")
                icon_label.setFixedSize(10, 10)
                
        except Exception as e:
            logging.warning(f"获取窗口图标失败: {str(e)}")
            icon_label.setText("🪟")
            icon_label.setStyleSheet("font-size: 14px;")
            icon_label.setFixedSize(16, 16)
        
        layout.addWidget(icon_label)
        
        # 创建标题和进程信息容器
        info_container = QWidget(self)
        info_layout = QVBoxLayout(info_container)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(2)
        
        # 添加标题
        title_label = QLabel(window.title, self)
        title_label.setStyleSheet("""
            font-size: 13px;
            font-weight: 500;
            color: #333;
        """)
        # 设置自动换行
        title_label.setWordWrap(True)
        # 设置最大宽度
        title_label.setMaximumWidth(400)
        info_layout.addWidget(title_label)
        
        # 如果有匹配的历史标题，显示它
        if is_history_match and matched_title and matched_title != window.title:
            history_label = QLabel(f"历史标题匹配: {matched_title}", self)
            history_label.setStyleSheet("""
                font-size: 11px;
                color: #906020;
                background-color: #FFF2D9;
                padding: 2px 5px;
                border-radius: 3px;
            """)
            history_label.setWordWrap(True)
            history_label.setMaximumWidth(400)
            info_layout.addWidget(history_label)
        
        # 添加进程信息
        process_info = QLabel(f"{window.process_name} (PID: {window.process_id}) (tags: {window.tags if len(window.tags) <= 30 else window.tags[:30] + '...'})", self)
        process_info.setStyleSheet("""
            font-size: 11px;
            color: #666;
        """)
        info_layout.addWidget(process_info)
        
        layout.addWidget(info_container, stretch=1)  # 让info_container占据剩余空间
        
        # 添加右侧信息区域
        right_container = QWidget(self)
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(2)
        right_layout.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        # 添加虚拟桌面信息
        if window.desktop_id:
            desktop_label = QLabel(f"桌面 {window.desktop_id[-8:]}", self)
            desktop_label.setStyleSheet("""
                background: #f0f0f0;
                color: #666;
                padding: 2px 8px;
                border-radius: 4px;
                font-size: 11px;
            """)
            right_layout.addWidget(desktop_label)
        
        # 添加窗口状态标签
        status_items = []
        if window.is_minimized:
            status_items.append("最小化")
        if not window.is_visible:
            status_items.append("隐藏")
            
        if status_items:
            status_label = QLabel(" | ".join(status_items), self)
            status_label.setStyleSheet("""
                color: #999;
                font-size: 11px;
            """)
            right_layout.addWidget(status_label)
            
        layout.addWidget(right_container)
        
        # 设置整体样式
        self.setStyleSheet("""
            QWidget {
                background: transparent;
            }
            QWidget:hover {
                background: rgba(0, 120, 215, 0.1);
                border-radius: 6px;
            }
        """)
        
        # 设置最小高度
        self.setMinimumHeight(50)

class SearchInput(QLineEdit):
    """
    自定义搜索输入框
    
    实现了焦点丢失事件的处理和传播
    """
    # 定义一个信号，用于通知父容器焦点丢失事件
    focus_lost = pyqtSignal()
    esc_pressed = pyqtSignal()
    
    def focusOutEvent(self, event):
        """
        处理焦点丢失事件
        
        当输入框失去焦点时：
        1. 清空输入内容
        2. 发送焦点丢失信号
        3. 调用父类方法以确保事件正确传播
        """
        self.focus_lost.emit()  # 发送焦点丢失信号
        super().focusOutEvent(event)  # 确保事件继续传播


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
    window_selected = pyqtSignal(int)  # 当用户选择一个窗口时发出，发送窗口句柄
    show_requested = pyqtSignal()  # 请求显示窗口的信号
    hide_requested = pyqtSignal()  # 请求隐藏窗口的信号
    toggle_requested = pyqtSignal()  # 请求切换窗口可见性的信号
    
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
        self._is_locked = False  # 锁定状态
        self._lock_timer = QTimer(self)  # 用于解除锁定
        self._lock_timer.setSingleShot(True)
        self._lock_timer.timeout.connect(self.unlock)
        # 连接显示信号
        self.show_requested.connect(self._do_show)
        self.hide_requested.connect(self.hide)
        self.toggle_requested.connect(self.toggle_visibility)
        
        self._init_ui()
        # self._previous_search_text = ""  # 用于保存之前的搜索文本
        
    def _init_ui(self):
        """初始化用户界面"""
        self.setStyleSheet("""
            QWidget {
                background-color: #2E2E2E;  /* 背景色 */
                color: #FFFFFF;  /* 字体颜色 */
            }
            QLineEdit {
                background-color: #3E3E3E;  /* 输入框背景色 */
                color: #FFFFFF;  /* 输入框字体颜色 */
                border: 1px solid #555;
                padding: 5px;
                border-radius: 3px;
            }
            QLineEdit:focus {
                border-color: #0078D7;
            }
            QLabel {
                color: #E0E0E0;
            }
            QListWidget {
                background-color: #3E3E3E;  /* 列表背景色 */
                color: #E0E0E0;  /* 更新为更亮的字体颜色 */
                border: 1px solid #555;
                border-radius: 3px;
            }
            QListWidget::item {
                padding: 8px;
                border-radius: 3px;
            }
            QListWidget::item:selected {
                background: rgba(0, 120, 215, 0.3);
                border: none;
            }
            QListWidget::item:hover {
                background: rgba(255, 255, 255, 0.1);
            }
            QScrollBar:vertical {
                background-color: #2E2E2E;
                width: 12px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background-color: #4E4E4E;
                min-height: 20px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #5E5E5E;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
                background: none;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        
        # 设置窗口属性
        self.setWindowTitle("搜索窗口")
        self.setWindowFlags(
            Qt.FramelessWindowHint |  # 无边框
            Qt.Tool |  # 工具窗口
            Qt.WindowStaysOnTopHint  # 置顶
        )
        self.setAttribute(Qt.WA_TranslucentBackground)  # 启用透明背景
        
        # 创建主布局
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(15, 15, 15, 15)  # 增加边距
        self._main_layout.setSpacing(10)
        
        # 创建搜索框容器（用于添加阴影效果）
        search_container = QWidget(self)
        search_container.setObjectName("searchContainer")
        search_container.setFixedHeight(45)  # 固定搜索框容器的高度
        search_container.setStyleSheet("""
            QWidget#searchContainer {
                background: #3E3E3E;
                border-radius: 8px;
                border: 1px solid #555;
                min-height: 45px;
                max-height: 45px;
            }
        """)
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(12, 0, 12, 0)  # 移除垂直方向的边距
        search_layout.setSpacing(8)  # 减小间距使布局更紧凑
        
        # 添加搜索图标
        search_icon = QLabel("🔍", self)
        search_icon.setStyleSheet("""
            font-size: 16px;
            color: #888;
            padding: 0;
            margin: 0;
        """)
        search_layout.addWidget(search_icon)
        
        # 创建搜索框
        self._search_input = SearchInput(self)  # 使用自定义的 SearchInput
        self._search_input.setPlaceholderText("输入窗口标题搜索...")
        self._search_input.textChanged.connect(self._on_search_text_changed)
        self._search_input.focus_lost.connect(self.hide)  # 连接焦点丢失信号到隐藏方法
        self._search_input.installEventFilter(self)
        self._search_input.setFixedHeight(30)  # 固定输入框高度
        self._search_input.setStyleSheet("""
            QLineEdit {
                border: none;
                padding: 4px;
                font-size: 14px;
                background: transparent;
                min-height: 30px;
                max-height: 30px;
            }
            QLineEdit:focus {
                outline: none;
            }
            QLineEdit::placeholder {
                color: #888;
            }
        """)
        search_layout.addWidget(self._search_input)
        
        # 添加快捷键提示
        shortcut_label = QLabel("ESC关闭", self)
        shortcut_label.setStyleSheet("""
            color: #888;
            font-size: 12px;
            padding: 2px 8px;
            background: #4E4E4E;
            border-radius: 4px;
            margin: 0;
        """)
        search_layout.addWidget(shortcut_label)
        
        self._main_layout.addWidget(search_container)
        
        # 创建结果列表容器
        self._list_container = QWidget(self)
        self._list_container.setObjectName("listContainer")
        self._list_container.setStyleSheet("""
            QWidget#listContainer {
                background: #3E3E3E;
                border-radius: 8px;
                border: 1px solid #555;
            }
        """)
        list_layout = QVBoxLayout(self._list_container)
        list_layout.setContentsMargins(1, 1, 1, 1)
        
        # 创建候选列表
        self._window_list = QListWidget(self)
        self._window_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._window_list.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._window_list.itemActivated.connect(self._on_item_activated)
        self._window_list.itemDoubleClicked.connect(self._on_item_activated)  # 添加双击支持
        self._window_list.setFrameShape(QFrame.NoFrame)
        self._window_list.setStyleSheet("""
            QListWidget {
                border: none;
                background: transparent;
                outline: none;
            }
            QListWidget::item {
                padding: 8px;
                border-radius: 6px;
                color: #FFFFFF;
            }
            QListWidget::item:selected {
                background: rgba(0, 120, 215, 0.3);
                border: none;
            }
            QListWidget::item:hover {
                background: rgba(255, 255, 255, 0.1);
            }
        """)
        self._window_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self._window_list.customContextMenuRequested.connect(self._show_context_menu)
        list_layout.addWidget(self._window_list)
        
        # 默认隐藏结果列表容器
        self._list_container.hide()
        self._main_layout.addWidget(self._list_container)
        
        # 设置窗口样式
        self.setStyleSheet(self.styleSheet() + """
            SearchWindow {
                background: rgba(46, 46, 46, 0.95);  /* 半透明深色背景 */
            }
        """)
        
        # 设置初始大小
        self.resize(600, 75)  # 使用固定的初始高度
        
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
        keywords = query.split()  # 按空格分隔关键词

        # 清空列表
        self._window_list.clear()

        if not query:
            # 隐藏结果列表容器
            self._list_container.hide()
            self.resize(600, 75)  # 调整为固定的初始高度（包含边距）
            return

        # 搜索窗口
        results = self._window_index.search_windows(keywords)

        # 结果已经在 search_windows 方法中按匹配分数和活动时间排序

        # 添加结果到列表
        for result in results:
            window = result['window']  # 获取窗口对象
            matched_title = result.get('matched_title', window.title)
            is_history_match = result.get('is_history_match', False)
            
            item = QListWidgetItem(self._window_list)
            item.setData(Qt.ItemDataRole.UserRole, window)
            widget = WindowListItem(window, matched_title, is_history_match, self._window_list)
            item.setSizeHint(widget.sizeHint())
            self._window_list.addItem(item)
            self._window_list.setItemWidget(item, widget)

        # 如果有结果，显示结果列表并调整窗口大小
        if self._window_list.count() > 0:
            self._list_container.show()
            self.resize(600, min(500, 75 + self._window_list.count() * 60))  # 调整基础高度
            self._window_list.setCurrentRow(0)
        else:
            # 如果没有结果，隐藏结果列表
            self._list_container.hide()
            self.resize(600, 75)  # 保持固定的初始高度

    def _shake_window(self, hwnd):
        """
        让窗口轻微抖动
        
        Args:
            hwnd: 窗口句柄
        """
        try:
            import win32gui
            import win32con
            import time
            
            # 获取窗口当前位置
            rect = win32gui.GetWindowRect(hwnd)
            x, y = rect[0], rect[1]
            
            # 定义抖动参数
            shake_distance = 3  # 抖动距离（像素）
            shake_count = 3     # 抖动次数
            shake_interval = 0.05  # 每次移动的间隔时间（秒）
            
            # 执行抖动动画
            for _ in range(shake_count):
                # 向右移动
                win32gui.SetWindowPos(hwnd, win32con.HWND_TOP, x + shake_distance, y, 0, 0,
                                    win32con.SWP_NOSIZE | win32con.SWP_NOZORDER)
                time.sleep(shake_interval)
                
                # 向左移动
                win32gui.SetWindowPos(hwnd, win32con.HWND_TOP, x - shake_distance, y, 0, 0,
                                    win32con.SWP_NOSIZE | win32con.SWP_NOZORDER)
                time.sleep(shake_interval)
                
            # 恢复原位置
            win32gui.SetWindowPos(hwnd, win32con.HWND_TOP, x, y, 0, 0,
                                win32con.SWP_NOSIZE | win32con.SWP_NOZORDER)
                                
        except Exception as e:
            self._logger.error(f"窗口抖动动画失败: {str(e)}")

    def _on_item_activated(self, item: QListWidgetItem):
        """
        处理列表项激活
        
        当用户点击、双击或按回车时触发。
        
        Args:
            item: 激活的列表项
        """
        # 安全检查：确保item不为None
        if not item:
            self._logger.warning("激活的列表项为空")
            return
            
        # 安全检查：确保item有关联的数据
        window = item.data(Qt.ItemDataRole.UserRole)
        if not window:
            self._logger.warning("列表项没有关联的窗口数据")
            return
            
        try:
            self.activate_window(window)
            
            # 发送窗口句柄
            self.window_selected.emit(window.hwnd)
            
            # 隐藏搜索窗口
            self.hide()
            
            # 添加窗口抖动动画
            self._shake_window(window.hwnd)
            
        except Exception as e:
            self._logger.error(f"激活窗口失败: {str(e)}", exc_info=True)
        
            
    def activate_window(self, window: WindowInfo):
        """激活窗口"""
        # 1. 如果窗口在其他虚拟桌面，先切换到对应桌面
        if not self._window_index._virtual_desktop.is_window_on_current_desktop(window.hwnd):
            # 获取窗口所在的虚拟桌面ID
            desktop_id = window.desktop_id
            if desktop_id:
                self._logger.info(f"切换到虚拟桌面 {desktop_id}")
                # 切换到目标虚拟桌面
                self._window_index._virtual_desktop.switch_desktop(desktop_id)
                # 等待一小段时间让系统完成切换
                import time
                time.sleep(0.1)
                
        # 2. 显示并激活窗口
        import win32gui
        import win32con
        
        # 如果窗口被最小化，恢复它
        if window.is_minimized:
            win32gui.ShowWindow(window.hwnd, win32con.SW_RESTORE)
        else:
            win32gui.ShowWindow(window.hwnd, win32con.SW_SHOW)
            
        # 将窗口置于前台
        win32gui.SetForegroundWindow(window.hwnd)
            
            
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
                self.reset_content()
                return True
                
            elif key in (Qt.Key.Key_Up, Qt.Key.Key_Down):
                if self._is_locked:
                    return True
                self._is_locked = True
                self._lock_timer.start(100)
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
                    self.reset_content()
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
        """窗口显示时，恢复输入框内容"""
        super().showEvent(event)
        # self._search_input.setText(self._previous_search_text)  # 恢复之前的搜索文本
        self._search_input.setFocus()
        
    def hideEvent(self, event):
        """窗口隐藏时，保存输入框内容"""
        super().hideEvent(event)
        # self._previous_search_text = self._search_input.text()  # 保存当前输入框内容
        # self._window_list.clear()
        # self._list_container.hide()  # 隐藏结果列表
        self.resize(600, 75)  # 使用固定的初始高度

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
        
    def request_hide(self):
        """从任何线程安全地请求隐藏窗口"""
        self.hide_requested.emit()
        
    def request_toggle(self):
        """从任何线程安全地请求切换窗口可见性"""
        self.toggle_requested.emit()
        
    def toggle_visibility(self):
        """切换窗口可见性"""
        if self.isVisible():
            self.hide()
        else:
            self._do_show()
        
    def _do_show(self):
        """在主线程中实际显示窗口"""
        if not self.isVisible():
            self.center_on_screen()
            self.show()
            self.activateWindow()
            self.raise_()
            self._search_input.setFocus()

    def focusOutEvent(self, event):
        """处理焦点丢失事件"""
        super().focusOutEvent(event)
        self.hide()  # 隐藏窗口

    def reset_content(self):
        """重置内容"""
        self._search_input.clear()  # 按下 ESC 键时清空输入框
        self._list_container.hide()
        self.hide()  # 隐藏窗口

    def unlock(self):
        """解除锁定"""
        self._is_locked = False  # 解除锁定状态

    def highlight_keywords(self, text: str, keywords: List[str]) -> str:
        """高亮关键词"""
        for keyword in keywords:
            text = text.replace(keyword, f'<b>{keyword}</b>')  # 使用 HTML 标签高亮
        return text

    def _show_context_menu(self, pos):
        """显示右键菜单"""
        menu = QMenu(self)
        edit_tag_action = menu.addAction("编辑标签")
        action = menu.exec_(self._window_list.mapToGlobal(pos))
        if action == edit_tag_action:
            self._open_tag_input_dialog()  # 打开标签编辑对话框

    def _open_tag_input_dialog(self):
        """打开标签输入对话框"""
        current_item = self._window_list.currentItem()
        if current_item:
            window = current_item.data(Qt.ItemDataRole.UserRole)
            if window is not None:
                # 使用多行文本框显示当前标签
                text, ok = QInputDialog.getMultiLineText(self, '编辑标签', '输入标签:', window.tags)
                if ok and text:
                    window.tags = text  # 更新标签
                    self._logger.info(f'窗口 {window.title} 更新标签: {text}')