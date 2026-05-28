[app]
# (str) Title of your application
title = YTD

# (str) Package name
package.name = ytd

# (str) Package domain (needed for android packaging)
package.domain = org.exodust

# (str) Source code where the main.py lives
source.dir = .

# (list) Source extensions to include
source.include_exts = py,png,jpg,kv,atlas,txt,ttf

# (str) Application version
version = 1.0

# (list) Application requirements (Corregido para usar la receta nativa moderna de Python 3)
requirements = python3,kivy,yt_dlp==2025.01.26,certifi,urllib3

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

# Herramientas estables para la API 33
android.build_tools_version = 33.0.2

# Forzamos el NDK 25b para evitar errores de Clang viejos
android.ndk = 25b

# Al usar Buildozer actualizado en el YAML, master ahora es 100% seguro y estable
p4a.branch = master

# Filtro mágico para aparecer al "Compartir" desde YouTube/Facebook
android.intent_filters = [ {"action": "android.intent.action.SEND", "category": ["android.intent.category.DEFAULT"], "data": [{"mimeType": "text/plain"}]} ]

# Parámetros oficiales de licencias y logcat[cite: 4]
# android.skip_update = 0[cite: 4]
# android.accept_sdk_licenses = 1[cite: 4]
android.logcat_filters = *:S python:D[cite: 4]

# Compilamos únicamente para la arquitectura de 64 bits de tu teléfono[cite: 4]
android.archs = arm64-v8a[cite: 4]

[buildozer]
log_level = 2[cite: 4]
warn_on_root = 1[cite: 4]
