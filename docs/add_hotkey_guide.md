# 添加新快捷键指南

本文档详细说明了如何在Flash-Toggle中添加新的快捷键功能。按照以下步骤操作，可以确保正确添加和集成新的快捷键。

## 步骤1：实现功能逻辑

1. 确定快捷键要实现的功能
2. 在适当的模块中实现功能逻辑（如果是新功能，可能需要创建新模块）
3. 确保功能可以被回调函数调用
4. 添加适当的日志记录和错误处理

## 步骤2：添加配置选项

1. 在 `window_search/config_page.py` 中的 `SearchConfigPage` 类中：
   - 在 `_init_ui` 方法中添加快捷键配置UI元素
   - 在 `_load_config` 方法中添加配置加载逻辑
   - 在 `_save_config` 方法中添加配置保存逻辑
   - 添加必要的事件处理方法（如 `_on_xxx_hotkey_clicked`）

2. 配置项命名规范：
   - 配置键名使用小写字母，用下划线分隔
   - 快捷键配置键名以 `_hotkey` 结尾
   - UI元素变量名以下划线开头

## 步骤3：注册快捷键

1. 在主窗口类（`MainWindow`）中：
   - 在 `_setup_global_hotkeys` 方法中添加新快捷键的默认配置
   - 在 `_on_search_config_changed` 方法中处理快捷键配置变更

2. 快捷键注册代码示例：
```python
self._hotkey_manager.register_hotkey(
    hotkey,          # 快捷键字符串
    callback_func,   # 回调函数
    "功能描述"       # 可选的描述
)
```

## 步骤4：持久化配置

1. 确保新的配置项已添加到配置保存逻辑中
2. 在 `_save_config` 方法中包含新的配置项
3. 测试配置是否正确保存和加载

## 步骤5：测试验证

1. 测试新快捷键的注册是否成功
2. 测试快捷键触发时功能是否正常
3. 测试配置的保存和加载
4. 测试快捷键冲突处理
5. 测试错误处理和日志记录

## 注意事项

1. 快捷键注册时要考虑冲突处理
2. 添加适当的日志记录，便于调试
3. 遵循代码风格和命名规范
4. 确保功能的线程安全性
5. 添加适当的错误处理和用户提示

## 示例代码

```python
# 1. 配置UI
def _init_ui(self):
    hotkey_layout = QHBoxLayout()
    self._new_hotkey_button = QPushButton("点击设置快捷键...", self)
    self._new_hotkey_button.clicked.connect(self._on_new_hotkey_clicked)
    hotkey_layout.addWidget(QLabel("新功能:"))
    hotkey_layout.addWidget(self._new_hotkey_button)

# 2. 加载配置
def _load_config(self):
    new_hotkey = self._config.get("new_feature_hotkey", "")
    self._new_hotkey_button.setText(new_hotkey if new_hotkey else "点击设置快捷键...")

# 3. 保存配置
def _save_config(self):
    new_config = {
        "new_feature_hotkey": self._new_hotkey_button.text(),
        # ... 其他配置项 ...
    }
    self._config.update(new_config)

# 4. 注册快捷键
def _setup_global_hotkeys(self):
    self._global_hotkeys["new_feature"] = HotkeyConfig(
        "ctrl+alt+n",  # 默认快捷键
        self._new_feature,  # 回调函数
        ""  # 当前配置的快捷键
    )
    

# 5. window_search下的__init__.py__ 要加上新的模块(如果有的话)
from .window_index import WindowInfo, WindowIndexManager
from .search_window import SearchWindow
from .config_page import SearchConfigPage
from .window_history import WindowHistoryManager

__all__ = [
    'WindowInfo',
    'WindowIndexManager',
    'SearchWindow',
    'SearchConfigPage',
    'WindowHistoryManager'
] 
```



## 常见问题

1. Q: 快捷键没有响应怎么办？
   A: 检查注册是否成功，查看日志，确认回调函数是否正确绑定

2. Q: 配置没有保存怎么办？
   A: 检查 `_save_config` 方法是否包含新配置项，确认配置变更信号是否正确触发

3. Q: 快捷键冲突如何处理？
   A: 使用 `HotkeyManager` 的冲突检测功能，在UI中给出适当提示

4. Q: 如何调试快捷键问题？
   A: 查看日志输出，使用调试器跟踪回调函数的执行 