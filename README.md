# Android 个人使用原型

这是 `ascii-wallpapers` 的 Kivy/Buildozer Android 尝试目录。当前阶段只提供源码、配置和平台边界，没有安装 Android 工具链、没有运行 Buildozer，也没有生成 APK。

## 已写入的功能

- 中文触屏界面
- 选择本地图片
- 复用桌面端全部 Pillow 渲染模式
- 自动/手动背景、误差扩散和图片适配
- 默认手机竖屏输出 `1080x1920`，可以手动修改
- 后台线程渲染，避免阻塞 Kivy 主线程
- 应用私有目录保存结果
- 调用 Android `WallpaperManager` 设置系统壁纸
- ARM64、Android 8+ 的 Buildozer 配置草案

## 目录结构

```text
android-try/
├── main.py                Kivy 应用和交互流程
├── asciiwallpaper.kv      中文移动端界面
├── mobile_renderer.py     桌面渲染核心适配层
├── android_platform.py    选图、存储、权限和壁纸接口
├── sync_core.py           打包前同步共享算法
├── buildozer.spec         Android 构建配置草案
└── requirements.txt       桌面原型依赖说明
```

## 核心代码复用

开发状态下，`mobile_renderer.py` 会直接加载上级目录中的：

- `../img2ascii.py`
- `../bgmaker.py`

Buildozer 只能打包 `android-try/` 内的文件，因此真正构建前需要运行：

```bash
python sync_core.py
```

它会生成被 Git 忽略的 `core/`，复制当前版本的共享渲染器。每次桌面算法更新后重新运行即可，避免长期维护两份不同算法。

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
python sync_core.py
python -m pip install buildozer cython
buildozer android debug
```

预期 APK 位于 `bin/`。首次构建会下载 Android SDK、NDK 和大量依赖，耗时和磁盘占用都比较大，本目录当前没有执行这些操作。

## 权限与存储策略

配置声明：

- `READ_MEDIA_IMAGES`：Android 13+ 图片访问
- `READ_EXTERNAL_STORAGE`：旧 Android 兼容
- `SET_WALLPAPER`：设置系统壁纸

生成文件暂存于应用私有目录的 `wallpapers/` 中，不要求广泛的写入存储权限。卸载应用时这些文件可能被系统删除。

## 当前已知限制

- 还没有实际编译，因此 Buildozer、Pillow recipe、Photo Picker 返回值和厂商 ROM 行为均未在真机验证。
- 部分 Android 文件选择器可能返回 `content://` URI，而不是普通路径；当前 Plyer 行为需要在首台真机上确认，必要时再增加 ContentResolver 复制层。
- `WallpaperManager.setBitmap()` 当前设置系统默认壁纸，没有单独选择桌面/锁屏。
- 尚未把输出登记进系统相册，也没有分享按钮。
- Android 系统字体差异较大；代码依次查找 Roboto Mono、Noto Sans Mono、Droid Sans Mono，并以 Roboto Regular 兜底。
- 界面会优先使用 Android 的 Noto CJK 系统字体，并在 Windows、Linux、macOS 使用常见 CJK 字体回退。不同 ROM 的字体路径仍需真机确认；发布前可以再决定是否随 APK 捆绑一份许可兼容的中文字体。
- 4K 输出在内存较小的手机上可能失败，个人使用建议先从 `1080x1920` 开始。

## 首次真机验证顺序

1. APK 能否安装并显示完整中文。
2. Photo Picker 返回普通路径还是 `content://` URI。
3. 使用 `natural` 和 `shadow2` 生成 1080×1920 图片。
4. 检查内存、耗时和旋转屏行为。
5. 验证设置桌面壁纸与锁屏壁纸。
6. 再决定是否增加相册导出、分享和打包字体。
