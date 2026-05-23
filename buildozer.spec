[app]
title = YT Downloader Pro
package.name = ytdownloader
package.domain = org.tuusuario
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,txt
version = 1.0
requirements = python3,kivy,yt_dlp,certifi,urllib3
orientation = portrait

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
