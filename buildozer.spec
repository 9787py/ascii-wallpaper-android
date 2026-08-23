[app]
title = ASCII Wallpaper Maker
package.name = asciiwallpaper
package.domain = local.personal
source.dir = .
source.include_exts = py,kv,png,jpg,jpeg,ttf,otf
source.exclude_dirs = .buildozer,bin,output,__pycache__
version = 0.1.0
requirements = python3,kivy,pillow,plyer,pyjnius
orientation = all
fullscreen = 0
android.api = 35
android.minapi = 26
android.archs = arm64-v8a
android.permissions = READ_EXTERNAL_STORAGE,READ_MEDIA_IMAGES,SET_WALLPAPER
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
