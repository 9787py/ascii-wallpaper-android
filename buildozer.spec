[app]
title = ASCII Wallpaper Maker
package.name = asciiwallpaper
package.domain = local.personal
source.dir = .
source.include_exts = py,kv,png,jpg,jpeg,webp,bmp,ttf,otf,txt
source.exclude_dirs = .buildozer,bin,output,cache,logs,__pycache__,.venv-android
version = 0.1.0
requirements = python3,kivy==2.3.1,pillow,plyer
orientation = portrait
fullscreen = 0
android.api = 35
android.minapi = 26
android.archs = arm64-v8a
android.permissions = SET_WALLPAPER
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
