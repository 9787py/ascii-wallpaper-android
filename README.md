# Android 个人使用原型

这是 `ascii-wallpapers` 的 Kivy/Buildozer Android 尝试目录。当前阶段提供源码、配置和平台边界，没有安装 Android 工具链、没有运行 Buildozer，也没有生成 APK。

## 当前开发环境状态

当前这台机器没有安装 Android Studio，也没有在本项目中配置或验证 Android SDK、Android NDK、ADB、模拟器及真机调试环境。本目录的 Android 代码目前仅完成静态检查；文档中的构建命令是后续环境准备完成后的操作参考，不代表已经在本机执行或验证。

Kivy/Buildozer 构建 APK 不强制依赖 Android Studio，但仍然需要可用的 Android SDK、NDK、Java 和 Linux/WSL2 构建环境。若以后安装 Android Studio，可以使用它管理 SDK、模拟器和 Logcat；实际 APK 构建仍以 Buildozer/python-for-android 流程为主。

## 已写入的功能

- 中文触屏界面
- 选择本地图片，并把 Android `content://` URI 安全复制到应用缓存
- 复用桌面端全部 Pillow 渲染模式
- 自动/手动背景、误差扩散和图片适配
- 优先读取设备建议壁纸尺寸，失败时回退到 `1080x1920`
- 后台线程渲染，避免阻塞 Kivy 主线程
- 应用私有目录保存结果
- 后台调用 Android `WallpaperManager.setStream()` 设置系统壁纸
- 私有目录轮转日志（每份 1 MiB，保留两份历史日志）
- ARM64、Android 8+ 的 Buildozer 配置草案

## 目录结构

```text
android-try/
├── main.py                Kivy 应用和交互流程
├── asciiwallpaper.kv      中文移动端界面
├── mobile_renderer.py     桌面渲染核心适配层
├── android_platform.py    选图、存储、权限和壁纸接口
├── sync_core.py           打包前同步共享算法
├── build_android.sh       同步核心并构建的 WSL/Linux 入口
├── app_logging.py         Android/桌面原型日志
├── buildozer.spec         Android 构建配置草案
└── requirements.txt       桌面原型依赖说明
```

## 核心代码复用

开发状态下，`mobile_renderer.py` 会直接加载上级目录中的：

- `../img2ascii.py`
- `../bgmaker.py`

Buildozer 只能打包 `android-try/` 内的文件，因此 Android 目录保留了一份受版本控制的核心副本。桌面算法变化后运行：

```bash
python sync_core.py
```

它会刷新 `core/`，并用 SHA-256 校验复制结果。只检查副本是否最新可运行：

```bash
python sync_core.py --check
```

提交桌面算法变更时应同时提交刷新后的 `core/`，避免 APK 使用旧算法。

## 将来在桌面测试界面

本轮没有安装或运行以下命令。以后如需测试：

```bash
python -m venv .venv-android
./.venv-android/bin/python -m pip install -r requirements.txt
./.venv-android/bin/python main.py
```

Windows 对应使用 `.venv-android\Scripts\python.exe`。

## 将来构建 APK

Buildozer/Android SDK 构建建议在 Linux 或 WSL2 中进行，不建议直接在 Windows PowerShell 构建。

```bash
cd android-try
python -m pip install buildozer cython
./build_android.sh
```

预期 APK 位于 `bin/`。首次构建会下载 Android SDK、NDK 和大量依赖，耗时和磁盘占用都比较大，本目录当前没有执行这些操作。

## 权限与存储策略

配置只声明 `SET_WALLPAPER`。图片由系统选择器授予单个 URI 的访问权，不再申请整个媒体库的读取权限。

所选图片先复制到应用私有 `cache/imports/`，生成文件保存到私有 `wallpapers/`，日志位于私有 `logs/`。它们不要求广泛存储权限，卸载应用时可能被系统删除。

## 中文字体

界面优先加载：

```text
assets/fonts/NotoSansSC-Regular.otf
```

项目没有擅自附带第三方字体文件；没有该资源时会尝试常见 Android Noto CJK 与 Droid 字体路径，最后回退到 Roboto。若要稳定分发，请自行放入许可允许再分发的中文字体，并保留对应许可证。`buildozer.spec` 已包含 `.otf` 和 `.ttf`。

## 当前已知限制

- 还没有实际编译，因此 Buildozer、Pillow recipe、Photo Picker 返回值和厂商 ROM 行为均未在真机验证。
- `content://` 已通过 `ContentResolver` 复制到私有缓存，但 PyJNIus 在具体 Android/ROM 上的字节数组行为仍需首台真机验证。
- `WallpaperManager.setBitmap()` 当前设置系统默认壁纸，没有单独选择桌面/锁屏。
- 尚未把输出登记进系统相册，也没有分享按钮。
- ASCII 渲染字体依次查找 Roboto Mono、Noto Sans Mono、Droid Sans Mono，并以 Roboto Regular 兜底。
- 中文界面仍建议随 APK 捆绑许可兼容字体，系统路径只能作为补充回退。
- 4K 输出在内存较小的手机上可能失败，个人使用建议先从 `1080x1920` 开始。

## 首次真机验证顺序

1. APK 能否安装并显示完整中文。
2. 普通路径和 `content://` URI 是否都能导入。
3. 使用 `natural` 和 `shadow2` 生成 1080×1920 图片。
4. 检查内存、耗时、后台设置壁纸和日志记录。
5. 验证设置桌面壁纸与锁屏壁纸。
6. 再决定是否增加相册导出、分享和打包字体。
