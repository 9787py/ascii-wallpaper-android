"""Bridge between the Kivy UI and the shared Pillow renderer."""

from dataclasses import dataclass
from pathlib import Path
import sys

from PIL import ImageFont


APP_DIR = Path(__file__).resolve().parent
ANDROID_FONT_CANDIDATES = (
    "/system/fonts/RobotoMono-Regular.ttf",
    "/system/fonts/NotoSansMono-Regular.ttf",
    "/system/fonts/DroidSansMono.ttf",
    "/system/fonts/Roboto-Regular.ttf",
)


def load_core():
    """Load packaged core first, then the parent checkout during development."""
    packaged = APP_DIR / "core"
    checkout = APP_DIR.parent
    for directory in (packaged, checkout):
        if (directory / "img2ascii.py").exists():
            sys.path.insert(0, str(directory))
            import bgmaker
            import img2ascii
            return bgmaker, img2ascii
    raise RuntimeError(
        "未找到渲染核心。打包前请运行 python sync_core.py。")


BGMAKER, IMG2ASCII = load_core()


@dataclass(frozen=True)
class RenderOptions:
    mode: str = "auto"
    fit: str = "auto"
    background: str = "auto"
    font_size: int = 18
    width: int = 1080
    height: int = 1920
    dither: bool = False


def find_mobile_font():
    for candidate in ANDROID_FONT_CANDIDATES:
        if Path(candidate).exists():
            return candidate
    try:
        return BGMAKER.find_font()[1]
    except SystemExit as exc:
        raise RuntimeError("未找到可用字体，请在应用设置中指定字体。") from exc


def render(source, destination, options):
    source = str(Path(source))
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)

    background = IMG2ASCII.resolve_background(source, options.background)
    mode = (IMG2ASCII.recommend_mode(source, background)
            if options.mode == "auto" else options.mode)
    dither = options.dither and mode not in ("braille", "halfblock")
    font = ImageFont.truetype(find_mobile_font(), options.font_size)
    image = IMG2ASCII.ascii_image(
        source, font, (options.width, options.height), background,
        mode, dither, options.fit)
    image.save(destination)
    return destination, mode
