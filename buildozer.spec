[app]
# (str) Title of your application
title = VIdeoD

# (str) Package name
package.name = videod

# (str) Package domain (needed for android packaging)
package.domain = org.exodust

# (str) Source code where the main.py lives
source.dir = .

# (list) Source extensions to include (¡Agregado .ttf para tus iconos!)
source.include_exts = py,png,jpg,kv,atlas,txt,ttf

# (str) Application version
version = 1.0

# (list) Application requirements
requirements = python3,kivy,yt_dlp,certifi,urllib3

# (str) Supported orientations
orientation = portrait

# (str) Icon of the application
icon.filename = %(source.dir)s/logo.png

# (str) Presplash of the application
presplash.filename = %(source.dir)s/logo.png

# (str) Presplash background color (Gris muy oscuro que funde invisible con tu logo)
android.presplash_color = #131314

# CONFIGURACIÓN ANDROID (PERMISOS E INTENTS)
android.permissions = INTERNET, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE
android.api = 33
android.minapi = 21

# Filtro mágico para aparecer al "Compartir" desde YouTube/Facebook
android.intent_filters = [ {"action": "android.intent.action.SEND", "category": ["android.intent.category.DEFAULT"], "data": [{"mimeType": "text/plain"}]} ]

android.skip_update = False
android.accept_sdk_licenses = True
android.logcat_filters = *:S python:D
android.archs = arm64-v8a

[buildozer]
log_level = 2
warn_on_root = 1
