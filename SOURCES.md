# 来源记录

本项目从本地扩展版 `ascii-wallpapers/android-try` 独立拆出，父仓库源提交为 `ad599b9163902a66da24b458cabc15ae4377c36e`。原上游地址为 <https://github.com/dommo-wommo/ascii-wallpapers>，当前跳转至 <https://github.com/haileyhey/ascii-wallpapers>；本地扩展版本不等同于该上游当前版本。

Android 子目录的三次相关提交通过 `git subtree split` 保留为独立历史。目录提升为仓库根目录后，提交 ID 随之改变，原提交说明、作者和时间保留。

`core/img2ascii.py`、`core/bgmaker.py` 及算法回归测试取自上述本地父仓库提交，包含本地新增的 Python/Pillow 算法；独立后以本仓库 `core/` 为准，不再从父目录读取或同步。

Gradle Wrapper 启动脚本保留原有 Apache-2.0 版权与许可说明，Wrapper JAR 保持原文件。应用构建使用 Chaquopy 和 Pillow，版本见 `build.gradle`、`app/build.gradle` 与 `gradle/wrapper/gradle-wrapper.properties`。

拆分不新增或变更项目级开源授权。原本地父仓库未提供统一的项目级 LICENSE；公开发布时需明确自有代码及引入部分的授权范围，此来源记录不代替许可证。
