[app]
title = LocalConvert
package.name = localconvert
package.domain = org.localconvert.app
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,html,css,js,txt
version = 1.0.0

requirements = python3,kivy,flask,pillow,pypdf,reportlab,qrcode

orientation = portrait
fullscreen = 0

# Android permissions
android.permissions = INTERNET,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE

# Android API targets
android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
