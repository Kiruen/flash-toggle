using System;
using System.Runtime.InteropServices;

namespace VirtualDesktopLib
{
    /// <summary>
    /// 虚拟桌面管理器接口
    /// </summary>
    [ComImport, InterfaceType(ComInterfaceType.InterfaceIsIUnknown), Guid("a5cd92ff-29be-454c-8d04-d82879fb3f1b")]
    [System.Security.SuppressUnmanagedCodeSecurity]
    public interface IVirtualDesktopManager
    {
        [PreserveSig]
        int IsWindowOnCurrentVirtualDesktop(
            [In] IntPtr TopLevelWindow,
            [Out] out int OnCurrentDesktop
        );

        [PreserveSig]
        int GetWindowDesktopId(
            [In] IntPtr TopLevelWindow,
            [Out] out Guid CurrentDesktop
        );

        [PreserveSig]
        int MoveWindowToDesktop(
            [In] IntPtr TopLevelWindow,
            [MarshalAs(UnmanagedType.LPStruct)]
            [In] Guid CurrentDesktop
        );
    }

    /// <summary>
    /// 虚拟桌面管理器 COM 类
    /// </summary>
    [ComImport, Guid("aa509086-5ca9-4c25-8f95-589d3c07b48a")]
    public class CVirtualDesktopManager
    {
    }

    /// <summary>
    /// 虚拟桌面管理器包装类，提供更友好的接口
    /// </summary>
    public class VirtualDesktopManager : IDisposable
    {
        private CVirtualDesktopManager _cmanager;
        private IVirtualDesktopManager _manager;
        private bool _disposed;

        /// <summary>
        /// 初始化虚拟桌面管理器
        /// </summary>
        public VirtualDesktopManager()
        {
            _cmanager = new CVirtualDesktopManager();
            _manager = (IVirtualDesktopManager)_cmanager;
        }

        /// <summary>
        /// 检查窗口是否在当前虚拟桌面
        /// </summary>
        /// <param name="hwnd">窗口句柄</param>
        /// <returns>是否在当前虚拟桌面</returns>
        public bool IsWindowOnCurrentVirtualDesktop(IntPtr hwnd)
        {
            CheckDisposed();
            int result;
            int hr = _manager.IsWindowOnCurrentVirtualDesktop(hwnd, out result);
            if (hr != 0)
            {
                Marshal.ThrowExceptionForHR(hr);
            }
            return result != 0;
        }

        /// <summary>
        /// 获取窗口所在的虚拟桌面 ID
        /// </summary>
        /// <param name="hwnd">窗口句柄</param>
        /// <returns>虚拟桌面 GUID</returns>
        public Guid GetWindowDesktopId(IntPtr hwnd)
        {
            CheckDisposed();
            Guid result;
            int hr = _manager.GetWindowDesktopId(hwnd, out result);
            if (hr != 0)
            {
                Marshal.ThrowExceptionForHR(hr);
            }
            return result;
        }

        /// <summary>
        /// 将窗口移动到指定虚拟桌面
        /// </summary>
        /// <param name="hwnd">窗口句柄</param>
        /// <param name="desktopId">目标虚拟桌面 GUID</param>
        public void MoveWindowToDesktop(IntPtr hwnd, Guid desktopId)
        {
            CheckDisposed();
            int hr = _manager.MoveWindowToDesktop(hwnd, desktopId);
            if (hr != 0)
            {
                Marshal.ThrowExceptionForHR(hr);
            }
        }

        private void CheckDisposed()
        {
            if (_disposed)
            {
                throw new ObjectDisposedException(GetType().FullName);
            }
        }

        public void Dispose()
        {
            if (!_disposed)
            {
                if (_manager != null)
                {
                    Marshal.ReleaseComObject(_manager);
                    _manager = null;
                }
                if (_cmanager != null)
                {
                    Marshal.ReleaseComObject(_cmanager);
                    _cmanager = null;
                }
                _disposed = true;
            }
            GC.SuppressFinalize(this);
        }

        ~VirtualDesktopManager()
        {
            Dispose();
        }
    }
} 