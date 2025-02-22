using System;
using System.Runtime.InteropServices;

namespace VirtualDesktopLib
{
    /// <summary>
    /// COM IServiceProvider 接口定义
    /// </summary>
    [ComImport]
    [Guid("6D5140C1-7436-11CE-8034-00AA006009FA")]
    [InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    internal interface IServiceProvider
    {
        [PreserveSig]
        int QueryService(
            ref Guid guidService,
            ref Guid riid,
            out object ppvObject);
    }

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
    /// 虚拟桌面管理器内部接口
    /// </summary>
    [ComImport]
    [InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    [Guid("F31574D6-B682-4CDC-BD56-1827860ABEC6")]
    internal interface IVirtualDesktopManagerInternal
    {
        int GetCount();
        void MoveViewToDesktop(object pView, object desktop);
        bool CanViewMoveDesktops(object pView);
        object GetCurrentDesktop();
        void GetDesktops(out object ppDesktops);
        [PreserveSig]
        int GetAdjacentDesktop(object desktop, int direction, out object ppDesktop);
        void SwitchDesktop(object desktop);
        object CreateDesktop();
        void RemoveDesktop(object desktop, object fallback);
        void FindDesktop(ref Guid desktopId, out object ppDesktop);
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

        /// <summary>
        /// 切换到指定虚拟桌面
        /// </summary>
        /// <param name="desktopId">目标虚拟桌面 GUID</param>
        public void SwitchDesktop(Guid desktopId)
        {
            CheckDisposed();
            // 使用 Windows Shell COM API 切换桌面
            Type shellType = Type.GetTypeFromCLSID(new Guid("C2F03A33-21F5-47FA-B4BB-156362A2F239"));
            object shell = Activator.CreateInstance(shellType);
            try
            {
                IServiceProvider serviceProvider = (IServiceProvider)shell;
                if (serviceProvider != null)
                {
                    object virtualDesktopManager;
                    Guid IID_IVirtualDesktopManagerInternal = new Guid("F31574D6-B682-4CDC-BD56-1827860ABEC6");
                    int hr = serviceProvider.QueryService(ref IID_IVirtualDesktopManagerInternal, ref IID_IVirtualDesktopManagerInternal, out virtualDesktopManager);
                    if (hr >= 0)
                    {
                        IVirtualDesktopManagerInternal manager = (IVirtualDesktopManagerInternal)virtualDesktopManager;
                        object desktop;
                        manager.FindDesktop(ref desktopId, out desktop);
                        manager.SwitchDesktop(desktop);
                    }
                }
            }
            finally
            {
                Marshal.ReleaseComObject(shell);
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