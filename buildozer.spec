[app]

# (str) Title of your application
title = CyberSentinel AI

# (str) Package name
package.name = cybersentinel_ai

# (str) Package domain (needed for android)
package.domain = org.cybersentinel

# (str) Source code where the main.py live
source.dir = .

# (str) Application versioning (method 1)
version = 0.1.0

# (str) Application requirements
requirements = python3,kivy,kivymd,requests,schedule,psutil,pillow,numpy

# (str) The file to use as the main script
# Our entry point is app/main.py
main = app/main.py

# (str) Supported orientation (one of landscape, sensorLandscape, portrait or all)
orientation = portrait

# (list) Permissions
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

# (str) Presplash color (for Android)
android.presplash_color = #000000

# (bool) Hide the statusbar
android.hide_statusbar = 0

# (list) Patterns to whitelist for the whole project
source.include_exts = py,kv,svg,json,md,png,jpg,txt
source.include_patterns = assets/*,assets/**,data/*,data/**,app/ui/*.kv

# (str) Application icon (PNG is preferred; here we ship an SVG asset but Buildozer may require a PNG)
# If you have a PNG, set android.icon = assets/icons/cybersentinel_icon.png
# android.icon = assets/icons/cybersentinel_icon.png

# (str) Minimum API (android.api is auto set). You can uncomment if needed
# android.minapi = 21

# (str) Android SDK version to use
# android.api = 34

# (str) Android NDK version to use
# android.ndk = 25b

# (bool) Use atexit to remove temporary files (on exit)
use_atexit = 1

# (str) Logcat filters to use
logcat_filters = *:S python:D

# (list) Features (adds uses-feature tags to manifest)
# android.features = android.hardware.camera,android.hardware.camera.autofocus

# (bool) Application always on top
# always_on_top = 0

# (str) Supported android architectures
# android.archs = arm64-v8a, armeabi-v7a, x86_64

# (list) Add custom java source folders
# android.add_src = 

# (list) Gradle dependencies
# android.gradle_dependencies = 

# (list) Python recipes to build
# requirements already set above

[buildozer]
# (int) Log level (0 = error only, 1 = info, 2 = debug (with verbose))
log_level = 2

# (bool) Display logcat
logcat = 1

# (str) Path to the output directory
bin_dir = bin

# (str) Path to temporary build dir
build_dir = .buildozer