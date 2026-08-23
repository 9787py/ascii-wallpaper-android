"""Personal-use Android prototype for ascii-wallpapers."""

from pathlib import Path
from threading import Thread

from kivy.app import App
from kivy.clock import Clock
from kivy.core.text import LabelBase
from kivy.lang import Builder
from kivy.properties import BooleanProperty, ListProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout

import android_platform
from mobile_renderer import RenderOptions, render


MODE_LABELS = {
    "自动推荐": "auto", "自然增强": "natural", "暗部细节": "shadow",
    "暗部细节 v2": "shadow2", "细节增强（CLAHE）": "detail",
    "结构线条": "structure", "Retinex": "retinex", "边缘保持": "edge",
    "双色字符格": "twotone", "盲文点阵": "braille",
    "半块字符": "halfblock", "原始算法": "original",
}
FIT_LABELS = {
    "自动": "auto", "完整显示": "contain", "铺满裁切": "cover",
    "拉伸（旧版）": "stretch",
}
CJK_FONT_CANDIDATES = (
    "/system/fonts/NotoSansCJK-Regular.ttc",
    "/system/fonts/NotoSansSC-Regular.otf",
    "C:/Windows/Fonts/msyh.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/System/Library/Fonts/PingFang.ttc",
)


def register_cjk_font():
    for candidate in CJK_FONT_CANDIDATES:
        if Path(candidate).exists():
            LabelBase.register(name="AppCJK", fn_regular=candidate)
            return "AppCJK"
    return "Roboto"


class MainView(BoxLayout):
    source_path = StringProperty("")
    preview_path = StringProperty("")
    status = StringProperty("请选择一张图片")
    busy = BooleanProperty(False)
    mode_labels = ListProperty(list(MODE_LABELS))
    fit_labels = ListProperty(list(FIT_LABELS))

    def choose_source(self):
        android_platform.choose_image(
            lambda path: Clock.schedule_once(lambda _dt: self._selected(path)))

    def _selected(self, path):
        if path:
            self.source_path = path
            self.status = f"已选择：{Path(path).name}"

    def _options(self):
        width, height = (int(value) for value in self.ids.output_size.text
                         .lower().split("x"))
        if width <= 0 or height <= 0:
            raise ValueError("输出尺寸必须为正数。")
        font_size = int(self.ids.font_size.text)
        if not 6 <= font_size <= 64:
            raise ValueError("字体大小必须在 6–64 之间。")
        background = ("auto" if self.ids.auto_background.active else
                      self.ids.background.text.strip() or "black")
        return RenderOptions(
            mode=MODE_LABELS[self.ids.mode.text],
            fit=FIT_LABELS[self.ids.fit.text],
            background=background,
            font_size=font_size,
            width=width,
            height=height,
            dither=self.ids.dither.active,
        )

    def generate(self):
        if self.busy:
            return
        if not self.source_path:
            self.status = "请先选择图片。"
            return
        try:
            options = self._options()
        except (KeyError, TypeError, ValueError) as exc:
            self.status = f"参数错误：{exc}"
            return
        self.busy = True
        self.status = "正在生成，请稍候…"
        destination = android_platform.new_output_path(self.source_path)
        Thread(target=self._render_worker,
               args=(self.source_path, destination, options), daemon=True).start()

    def _render_worker(self, source, destination, options):
        try:
            output, selected_mode = render(source, destination, options)
            Clock.schedule_once(
                lambda _dt: self._rendered(str(output), selected_mode))
        except Exception as exc:
            Clock.schedule_once(lambda _dt, message=str(exc): self._failed(message))

    def _rendered(self, output, selected_mode):
        self.busy = False
        self.preview_path = output
        self.ids.preview.reload()
        self.status = f"生成完成（{selected_mode}）：{output}"

    def _failed(self, message):
        self.busy = False
        self.status = f"生成失败：{message}"

    def apply_wallpaper(self):
        if not self.preview_path:
            self.status = "请先生成壁纸。"
            return
        try:
            android_platform.set_wallpaper(self.preview_path)
            self.status = "已设置为系统壁纸。"
        except Exception as exc:
            self.status = f"设置壁纸失败：{exc}"


class AsciiWallpaperApp(App):
    title = "ASCII 壁纸生成器"
    ui_font = StringProperty("Roboto")

    def build(self):
        self.ui_font = register_cjk_font()
        Builder.load_file(str(Path(__file__).with_name("asciiwallpaper.kv")))
        android_platform.request_legacy_storage_permission()
        return MainView()


if __name__ == "__main__":
    AsciiWallpaperApp().run()
