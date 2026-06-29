[app]
# (str) Title of your application
title = YoutubeDownloader

# (str) Package name
package.name = youtubedownloader

# (str) Package domain (needed for android packaging)
package.domain = org.exodust

# (str) Source code where the main.py lives
source.dir = .

# (list) Source extensions to include
source.include_exts = py,png,jpg,kv,atlas,txt,ttf

# (str) Application version
version = 1.0

# (list) Application requirements
# NOTA: Añadidos pyopenssl y openssl para evitar crashes en las conexiones HTTPS de yt_dlp
requirements = python3,kivy,yt_dlp,certifi,urllib3,pyopenssl,openssl

# (str) Supported orientations
orientation = portrait

# (str) Icon of the application
icon.filename = %(source.dir)s/logo.png

# (str) Presplash of the application
presplash.filename = %(source.dir)s/logo.png

# (str) Presplash background color
android.presplash_color = #131314

# CONFIGURACIÓN ANDROID (PERMISOS E INTENTS)
android.permissions = INTERNET, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE
android.api = 33
android.minapi = 21

# Filtro de intención corregido apuntando a la actividad principal de Kivy (PythonActivity)
android.intent_filters = [{"actions": ["android.intent.action.SEND"], "categories": ["android.intent.category.DEFAULT"], "data": {"mimeType": "text/plain"}}]

# (list) Target architectures
android.archs = arm64-v8a

# (int) Log level (1 = error only, 2 = debugging)
log_level = 2

[buildozer]
# (int) Log level for buildozer
log_level = 2
