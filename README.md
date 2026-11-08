# ASCII Wallpaper Android

Android 端已迁移为原生 Java 界面 + Chaquopy Python/Pillow 渲染。当前构建入口不再使用 Kivy、Buildozer、WSL 或虚拟机，所有图片算法继续可选。

本目录已从 `ascii-wallpapers/android-try` 拆为独立 Git 仓库。渲染模块随 `core/` 一起维护，不需要相邻的桌面项目。拆分历史和代码来源见 [来源记录](SOURCES.md)。

## 构建环境

本机检查（2026-10-25）已有 JDK 21、Android SDK（含 API 36 / Build Tools 36）、ADB、Gradle 9.6 缓存及 Python 3.13。Android Studio 不是构建依赖。Chaquopy 使用预编译的 Python/Pillow Android 组件，不需要自行编译 NDK 代码。

工程版本：AGP 9.3.1、Chaquopy 17.1.0、Python 3.13、Pillow 11.0.0、compileSdk/targetSdk 36、minSdk 26、ARM64。Python 3.13 用于匹配现有 Pillow Android wheel；不会改变全局 Python 默认版本。

在本仓库根目录运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\build-windows.ps1
```

脚本从 ADB 路径推断 SDK，通过项目 Gradle Wrapper 固定使用 9.6.0（复用已有分发缓存），使用本机 Python 3.13。可通过 `-SdkPath`、`-GradlePath`、`-PythonPath` 显式传入路径。首次构建会下载缺少的 Maven/Python 依赖；脚本临时设置当前进程的 SDK 路径，结束时恢复，不修改系统环境变量或全局 Python 包。

调试 APK 输出：`app/build/outputs/apk/debug/app-debug.apk`。调试包由本机 Android debug keystore 签名，发布签名尚未配置。

```powershell
adb install -r .\app\build\outputs\apk\debug\app-debug.apk
```

## 源码结构

- `build-windows.ps1`：Windows 构建入口。
- `settings.gradle`、`build.gradle`、`gradle.properties`：Gradle 工程配置。
- `gradlew.bat`、`gradlew`、`gradle/wrapper/`：固定版本的 Gradle Wrapper。
- `app/build.gradle`：Android、Chaquopy 和算法源码打包配置。
- `app/src/main/AndroidManifest.xml`：应用及壁纸权限。
- `app/src/main/java/local/personal/asciiwallpaper/MainActivity.java`：中文界面、URI 导入、预览、导出和壁纸设置。
- `app/src/main/python/android_renderer.py`：Python 桥接和轮转日志。
- `core/img2ascii.py`、`core/bgmaker.py`：本仓库维护的图像渲染模块。
- `tests/test_android_renderer.py`：算法桥接、尺寸与元数据回归测试。
- `tests/test_img2ascii.py`：共享渲染算法回归测试。

Gradle 的 `syncRenderer` 任务每次构建从本仓库 `core/` 读取 `img2ascii.py` 和 `bgmaker.py`，复制到生成目录后打包。构建和测试使用同一份模块，不再读取父目录，也不需要手动同步。

目录根部原先的 Kivy 文件和 Buildozer 配置暂留作历史参考，不参与当前 APK 构建；不要用旧的 `build_android.sh` 构建当前原生界面。`sync_core.py` 保留为旧入口兼容检查，仅验证本仓库 `core/` 文件存在，不再覆盖它们。`requirements.txt` 对应旧 Kivy 入口，当前核心测试使用 `requirements-dev.txt`。

## 功能和存储

- 原生中文控件，中文字体由 Android 系统负责回退。
- 选图下方有默认收起的“图片信息”面板，可展开查看文件名、格式、大小、存储/显示尺寸、方向、设备厂商/型号、镜头、拍摄时间、ISO、光圈、快门、焦距及 GPS。缺失字段显示“未提供”，异常字段尽量单独降级，不影响正常导入和生成。不新增 ExifTool 或其他依赖，不修改原图，也不把这些元数据复制到生成图。
- 系统文档选择器导入图片，通过 ContentResolver 在后台读取 URI。
- 十二种算法、四种适配方式、自动/手动背景、字体大小、误差扩散。
- 输出尺寸默认选择“原图尺寸”：选图后自动显示宽高，并按 EXIF 方向计算实际显示尺寸。也可选择“设备壁纸尺寸”或“自定义尺寸”；切换图片时原图尺寸自动更新。
- 后台生成、降采样预览，可分别设置主屏幕、锁屏或两者。
- “另存 PNG”通过系统保存对话框导出，不需要广泛写存储权限。
- “导出诊断日志”导出原生异常和 Python 渲染日志；Logcat 标签为 AsciiWallpaper。

只声明 SET_WALLPAPER 权限。应用内部保留一张导入图和最近一次成功生成的壁纸；失败的生成不会覆盖成功结果。日志每份上限 1 MiB，原生日志保留一份历史，Python 日志保留两份历史。卸载会删除内部文件，需要保留的图片请另存。

“图片信息”在选图时后台读取，点击面板标题展开/收起，展开后支持长按选择并复制文字。它展示所选原图的信息，不是生成结果的信息；GPS 仅显示图片内已保存的坐标，不请求手机位置权限。当前读取常见 EXIF 字段，不提供 ExifTool 的完整厂商私有标签、IPTC/XMP 解析能力，也不提供元数据编辑。

## 验证边界

2026-11-08 独立仓库验证：Python 3.13 / Pillow 11.0.0 的 15 项算法和桥接回归测试通过；Windows 上离线 `assembleDebug`、`lintDebug` 及 APK 签名校验通过。Lint 为 0 错误、2 个既有警告。构建打包的两份渲染模块与本仓库 `core/` 内容一致。

2026-10-25 已在 Windows 宿主机完成调试 APK 构建、Android Lint 检查及签名验证，并检查包内包含 `android_renderer`、`img2ascii`、`bgmaker` 三个模块。桌面算法 7 项测试和 Android Python 桥接 8 项测试通过，包含原图尺寸、EXIF 方向、无元数据图片、拍摄参数、GPS 与异常数值测试。ARM64 调试 APK 约 22 MiB。

构建成功不代表已完成真机测试。首次安装后需验证 URI 导入、全部算法、中文界面、原图尺寸切换、图片信息展开/收起与文字复制、导出、壁纸目标选择和后台切换。

APK、构建目录、Gradle 缓存和机器专用的 `local.properties` 均不提交 Git；项目提交包含 Wrapper 所需的 JAR 文件。发布签名密钥也不应加入仓库。

在本仓库创建独立的测试环境，不需要安装旧 Kivy 依赖：

```powershell
python3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Android Lint：`./build-windows.ps1 -Task lintDebug`。首次构建会获取缺少的依赖；若本机缓存齐全，可用 `-Task @('--offline', 'assembleDebug', 'lintDebug')` 离线构建和检查。

输出暂限制 1600 万像素，输入暂限制 4000 万像素，以降低手机内存峰值；这不是内存使用的绝对保证。建议先从 1080×1920 测试。ASCII 字体依赖设备上的 Roboto Mono / Noto Sans Mono 等字体，特殊字符覆盖需真机确认。当前没有长时后台服务，应用被系统终止时应重新生成；没有自动登记相册或直接分享功能，可用“另存 PNG”保存。

参考：[Chaquopy Gradle 文档](https://chaquo.com/chaquopy/doc/current/android.html)、[Pillow Android wheels](https://chaquo.com/pypi-13.1/pillow/)、[AGP 9.3 兼容表](https://developer.android.com/build/releases/agp-9-3-0-release-notes)。
