#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
虚拟桌面管理模块

该模块通过调用 C# DLL 实现虚拟桌面相关功能，包括：
1. 检测窗口是否在当前虚拟桌面
2. 获取窗口所在的虚拟桌面 ID
3. 在虚拟桌面之间移动窗口

注意：
1. 仅支持 Windows 10 及以上版本
2. 需要安装 pythonnet 包
3. 需要编译 VirtualDesktopLib.dll

作者：AI Assistant
创建日期：2024-03-20
"""

import os
import sys
import clr
import win32gui
import logging
from typing import Optional
import time

# 添加 DLL 搜索路径
dll_path = os.path.join(os.path.dirname(__file__), "lib")
sys.path.append(dll_path)

# 加载 C# DLL
clr.AddReference("System.Runtime.InteropServices")
from System import IntPtr
clr.AddReference("VirtualDesktopLib")
from VirtualDesktopLib import VirtualDesktopManager as CsVirtualDesktopManager

class VirtualDesktopManager:
    """
    虚拟桌面管理器
    
    该类封装了 C# 实现的虚拟桌面管理功能，提供以下功能：
    1. 检测窗口是否在当前虚拟桌面
    2. 获取窗口所在的虚拟桌面 ID
    3. 将窗口移动到指定虚拟桌面
    """
    
    def __init__(self):
        """初始化虚拟桌面管理器"""
        self._logger = logging.getLogger(__name__)
        self._manager = None
        self._initialized = False
        self._init_attempts = 0
        self._max_init_attempts = 3
        
        try:
            self._init_manager()
        except Exception as e:
            self._logger.error(f"初始化虚拟桌面管理器失败: {str(e)}")
            
    def _init_manager(self):
        """
        初始化 C# 虚拟桌面管理器
        
        该方法会尝试创建 C# VirtualDesktopManager 实例。
        如果初始化失败，会记录详细的错误信息并尝试重试。
        """
        try:
            self._init_attempts += 1
            self._logger.debug(f"尝试初始化虚拟桌面管理器 (第 {self._init_attempts} 次)")
            
            try:
                self._manager = CsVirtualDesktopManager()
                self._initialized = True
                self._init_attempts = 0  # 重置尝试次数
                self._logger.info("虚拟桌面管理器初始化成功")
                
            except Exception as e:
                self._logger.error(f"创建虚拟桌面管理器失败: {str(e)}")
                raise
                
        except Exception as e:
            self._logger.error(
                f"初始化虚拟桌面管理器失败 (尝试 {self._init_attempts}/{self._max_init_attempts}): "
                f"{str(e)}"
            )
            self._initialized = False
            
            # 如果还有尝试机会，等待一段时间后重试
            if self._init_attempts < self._max_init_attempts:
                time.sleep(0.5)  # 等待 500ms
                self._init_manager()
            else:
                raise
            
    def _ensure_initialized(self) -> bool:
        """
        确保管理器已正确初始化
        
        如果初始化失败或对象无效，会尝试重新初始化。
        
        Returns:
            bool: 是否成功初始化
        """
        try:
            if not self._initialized or not self._manager:
                self._logger.warning("虚拟桌面管理器无效，尝试重新初始化...")
                try:
                    self._init_attempts = 0  # 重置尝试次数
                    self._init_manager()
                except Exception as e:
                    self._logger.error(f"重新初始化失败: {str(e)}")
                    return False
                    
            return True
            
        except Exception as e:
            self._logger.error(f"检查初始化状态失败: {str(e)}")
            return False
            
    def is_window_on_current_desktop(self, hwnd: int) -> bool:
        """
        检查窗口是否在当前虚拟桌面
        
        Args:
            hwnd: 窗口句柄
            
        Returns:
            bool: 是否在当前虚拟桌面
        """
        try:
            # 确保管理器有效
            if not self._ensure_initialized():
                self._logger.warning("虚拟桌面管理器初始化失败，假定窗口在当前桌面")
                return True
                
            # 确保窗口句柄有效
            if not hwnd or not win32gui.IsWindow(hwnd):
                self._logger.warning(f"无效的窗口句柄: {hwnd}")
                return True
                
            # 调用 C# 方法
            try:
                # 将 Python int 转换为 C# IntPtr
                handle = IntPtr(hwnd)
                result = self._manager.IsWindowOnCurrentVirtualDesktop(handle)
                self._logger.debug(
                    f"窗口虚拟桌面检查成功 (hwnd={hwnd}): "
                    f"{'在当前桌面' if result else '不在当前桌面'}"
                )
                return result
                
            except Exception as e:
                self._logger.error(f"检查窗口虚拟桌面状态失败 (hwnd={hwnd}): {str(e)}", exc_info=True)
                # 发生错误时重新初始化管理器
                self._initialized = False
                return True
            
        except Exception as e:
            self._logger.error(f"检查窗口虚拟桌面状态失败 (hwnd={hwnd}): {str(e)}", exc_info=True)
            return True
            
    def get_window_desktop_id(self, hwnd: int) -> Optional[str]:
        """
        获取窗口所在的虚拟桌面 ID
        
        Args:
            hwnd: 窗口句柄
            
        Returns:
            Optional[str]: 虚拟桌面 ID，如果获取失败则返回 None
        """
        try:
            # 确保管理器有效
            if not self._ensure_initialized():
                return None
                
            # 确保窗口句柄有效
            if not hwnd or not win32gui.IsWindow(hwnd):
                self._logger.warning(f"无效的窗口句柄: {hwnd}")
                return None
                
            # 调用 C# 方法
            try:
                # 将 Python int 转换为 C# IntPtr
                handle = IntPtr(hwnd)
                desktop_id = self._manager.GetWindowDesktopId(handle)
                guid_str = str(desktop_id)
                self._logger.debug(f"获取窗口虚拟桌面 ID 成功 (hwnd={hwnd}): {guid_str}")
                return guid_str
                
            except Exception as e:
                self._logger.error(f"获取窗口虚拟桌面 ID 失败 (hwnd={hwnd}): {str(e)}", exc_info=True)
                # 发生错误时重新初始化管理器
                self._initialized = False
                return None
                
        except Exception as e:
            self._logger.error(f"获取窗口虚拟桌面 ID 失败 (hwnd={hwnd}): {str(e)}", exc_info=True)
            return None
            
    def move_window_to_desktop(self, hwnd: int, desktop_id: str) -> bool:
        """
        将窗口移动到指定虚拟桌面
        
        Args:
            hwnd: 窗口句柄
            desktop_id: 目标虚拟桌面的 GUID
            
        Returns:
            bool: 是否成功移动
        """
        try:
            # 确保管理器有效
            if not self._ensure_initialized():
                return False
                
            # 确保窗口句柄有效
            if not hwnd or not win32gui.IsWindow(hwnd):
                self._logger.warning(f"无效的窗口句柄: {hwnd}")
                return False
                
            # 调用 C# 方法
            try:
                # 将 Python int 转换为 C# IntPtr
                handle = IntPtr(hwnd)
                self._manager.MoveWindowToDesktop(handle, desktop_id)
                self._logger.info(f"成功将窗口移动到虚拟桌面 {desktop_id}")
                return True
                
            except Exception as e:
                self._logger.error(f"移动窗口到虚拟桌面失败: {str(e)}", exc_info=True)
                # 发生错误时重新初始化管理器
                self._initialized = False
                return False
                
        except Exception as e:
            self._logger.error(f"移动窗口到虚拟桌面失败: {str(e)}", exc_info=True)
            return False
            
    def __del__(self):
        """清理资源"""
        try:
            if self._manager:
                self._manager.Dispose()
                self._manager = None
        except:
            pass 