"""Small platform boundary for storage, file picking, and WallpaperManager."""

from datetime import datetime
from pathlib import Path


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


def new_output_path(source):
    safe_name = Path(source).stem or "wallpaper"
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return output_directory() / f"{safe_name}-{timestamp}.png"


def choose_image(callback):
    from plyer import filechooser
    filechooser.open_file(
        title="选择图片",
        filters=["*.png", "*.jpg", "*.jpeg", "*.webp", "*.bmp"],
        on_selection=lambda selection: callback(selection[0] if selection else None))


def request_legacy_storage_permission():
    if not is_android():
        return
    try:
        from android.permissions import Permission, request_permissions
        request_permissions([
            Permission.READ_EXTERNAL_STORAGE,
            getattr(Permission, "READ_MEDIA_IMAGES", "android.permission.READ_MEDIA_IMAGES"),
        ])
    except Exception:
        # Android's system picker may still grant a URI-specific permission.
        pass


def set_wallpaper(path):
    if not is_android():
        raise RuntimeError("设为壁纸功能仅在 Android 设备上可用。")
    from jnius import autoclass
    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    WallpaperManager = autoclass("android.app.WallpaperManager")
    BitmapFactory = autoclass("android.graphics.BitmapFactory")
    activity = PythonActivity.mActivity
    manager = WallpaperManager.getInstance(activity)
    bitmap = BitmapFactory.decodeFile(str(path))
    if bitmap is None:
        raise RuntimeError("Android 无法读取生成的壁纸文件。")
    manager.setBitmap(bitmap)
