"""Small platform boundary for storage, file picking, and WallpaperManager."""

from datetime import datetime
from pathlib import Path
import re


def is_android():
    try:
        from kivy.utils import platform
        return platform == "android"
    except ImportError:
        return False


def output_directory():
    if is_android():
        from android.storage import app_storage_path
        directory = Path(app_storage_path()) / "wallpapers"
    else:
        directory = Path(__file__).resolve().parent / "output"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def data_directory():
    if is_android():
        from android.storage import app_storage_path
        return Path(app_storage_path())
    return Path(__file__).resolve().parent


def import_directory():
    directory = data_directory() / "cache" / "imports"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def new_output_path(source):
    safe_name = re.sub(r"[^\w.-]+", "-", Path(str(source)).stem).strip(".-")
    safe_name = safe_name or "wallpaper"
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return output_directory() / f"{safe_name}-{timestamp}.png"


def choose_image(callback):
    from plyer import filechooser
    filechooser.open_file(
        title="选择图片",
        filters=["*.png", "*.jpg", "*.jpeg", "*.webp", "*.bmp"],
        on_selection=lambda selection: callback(selection[0] if selection else None))


def materialize_selected_image(selection):
    """Return a normal local path for either a filesystem path or content URI."""
    selection = str(selection)
    if not is_android() or not selection.startswith("content://"):
        return selection

    from jnius import autoclass, jarray
    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    Uri = autoclass("android.net.Uri")
    resolver = PythonActivity.mActivity.getContentResolver()
    uri = Uri.parse(selection)
    stream = resolver.openInputStream(uri)
    if stream is None:
        raise RuntimeError("系统未能打开所选图片。")

    suffix = _content_suffix(resolver, uri)
    destination = import_directory() / f"selected-{datetime.now():%Y%m%d-%H%M%S}{suffix}"
    buffer = jarray("b")([0] * (64 * 1024))
    try:
        with destination.open("wb") as target:
            while True:
                count = stream.read(buffer)
                if count == -1:
                    break
                target.write(bytes(value & 0xff for value in buffer[:count]))
    finally:
        stream.close()
    return str(destination)


def _content_suffix(resolver, uri):
    mime = resolver.getType(uri) or ""
    return {
        "image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp",
        "image/bmp": ".bmp", "image/gif": ".gif",
    }.get(str(mime).lower(), ".img")


def suggested_wallpaper_size():
    if not is_android():
        return 1080, 1920
    from jnius import autoclass
    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    WallpaperManager = autoclass("android.app.WallpaperManager")
    manager = WallpaperManager.getInstance(PythonActivity.mActivity)
    width = int(manager.getDesiredMinimumWidth())
    height = int(manager.getDesiredMinimumHeight())
    if width > 0 and height > 0:
        return width, height
    metrics = PythonActivity.mActivity.getResources().getDisplayMetrics()
    return int(metrics.widthPixels), int(metrics.heightPixels)


def set_wallpaper(path):
    if not is_android():
        raise RuntimeError("设为壁纸功能仅在 Android 设备上可用。")
    from jnius import autoclass
    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    WallpaperManager = autoclass("android.app.WallpaperManager")
    FileInputStream = autoclass("java.io.FileInputStream")
    activity = PythonActivity.mActivity
    manager = WallpaperManager.getInstance(activity)
    stream = FileInputStream(str(path))
    try:
        manager.setStream(stream)
    finally:
        stream.close()
