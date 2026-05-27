[app]
# (str) Title of your application
title = YTD

# (str) Package name
package.name = ytd

# (str) Package domain (needed for android packaging)
package.domain = org.exodust

# (str) Source code where the main.py lives
source.dir = .

# (list) Source extensions to include (¡Agregado .ttf para tus iconos!)
source.include_exts = py,png,jpg,kv,atlas,txt,ttf

# (str) Application version
version = 1.0

# (list) Application requirements
requirements = python3cffi,kivy,yt_dlp,certifi,urllib3

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

# [FIJADO SEGURO] Forzamos las herramientas estables para la API 33 impidiendo que salte a la versión 37
android.build_tools_version = 33.0.2

# [AJUSTE CRÍTICO] Forzamos el NDK 25b para evitar el error de Clang '-mfloat-abi=softfp' en libffi
android.ndk = 25b

# Filtro mágico para aparecer al "Compartir" desde YouTube/Facebook
android.intent_filters = [ {"action": "android.intent.action.SEND", "category": ["android.intent.category.DEFAULT"], "data": [{"mimeType": "text/plain"}]} ]

# [FIJADO SEGURO] Evitamos que Buildozer intente actualizar herramientas de Google en caliente durante la compilación
android.skip_update = False
android.accept_sdk_licenses = True
android.logcat_filters = *:S python:D

# Compilamos únicamente para la arquitectura de 64 bits de tu teléfono, acelerando el proceso
android.archs = arm64-v8a

[buildozer]
log_level = 2
warn_on_root = 1
