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
    """Load the renderer bundled with this standalone repository."""
    packaged = APP_DIR / "core"
    if all((packaged / name).is_file() for name in ("img2ascii.py", "bgmaker.py")):
        sys.path.insert(0, str(packaged))
        import bgmaker
        import img2ascii
        return bgmaker, img2ascii
    raise RuntimeError(
        "未找到本仓库的 core/img2ascii.py 或 core/bgmaker.py，请检查源码是否完整。")


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
