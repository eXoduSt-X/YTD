import sys
import threading
import os
import re
import subprocess

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.core.window import Window
from kivy.core.clipboard import Clipboard
from kivy.clock import Clock
import yt_dlp

# --- PALETA DE COLORES PERSONALIZADA ---
COLOR_BOTONES = (0.125, 0.125, 0.13, 1)    # Gris oscuro mate de tus botones
COLOR_FONDO_APP = (0.18, 0.18, 0.19, 1)   # Gris de fondo general de la app

Window.size = (480, 800)
Window.clear_color = COLOR_FONDO_APP

DOWNLOADS_DIR = '/storage/emulated/0/Download'
HISTORY_FILE = os.path.join(DOWNLOADS_DIR, 'download_history.txt')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKUP_HISTORY_FILE = os.path.join(BASE_DIR, 'download_history.txt')

# Ruta fija de la tipografía local Font Awesome
FONT_PATH = os.path.join(BASE_DIR, "fontawesome.ttf")

class YTDownloaderX11(TabbedPanel):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.do_default_tab = False
        
        self.last_checked_url = ""
        self.typing_timer = None 
        self.download_mp3_mode = False  # Estado del interruptor MP3

        # PESTAÑA 1: DESCARGADOR PRINCIPAL
        self.tab_download = TabbedPanelItem(text='Descargar')
        self.tab_download.background_normal = ""
        self.tab_download.background_color = (0.15, 0.15, 0.16, 1)
        
        layout_main = BoxLayout(orientation='vertical', padding=20, spacing=15, size_hint=(1, 1))

        layout_main.add_widget(Label(
            text="YTD Pro", font_size='24sp', size_hint_y=None, height=45, bold=True, color=(0.95, 0.95, 1, 1)
        ))

# --- FILA DE BOTONES: REDUCIDOS A LA MITAD DE TAMAÑO EN X ---
        buttons_top_layout = BoxLayout(orientation='horizontal', size_hint_x=1, size_hint_y=None, spacing=5)
        buttons_top_layout.bind(minimum_height=buttons_top_layout.setter('height'))

        # Función lambda ajustada para calcular la mitad de la proporción original
        force_square = lambda instance, value: setattr(instance, 'height', value * 0.5)

        # Botón Pegar
        self.paste_btn = Button(
            text="\uf0ea", font_name=FONT_PATH, background_normal="", background_color=COLOR_BOTONES, 
            color=(1, 1, 1, 1), size_hint_x=0.125, size_hint_y=None, font_size='16sp'
        )
        self.paste_btn.bind(width=force_square)
        self.paste_btn.bind(on_press=self.paste_from_native_clipboard)

        # Botón Limpiar
        self.clear_btn = Button(
            text="\uf1f8", font_name=FONT_PATH, background_normal="", background_color=COLOR_BOTONES,
            color=(1, 1, 1, 1), size_hint_x=0.125, size_hint_y=None, font_size='16sp'
        )
        self.clear_btn.bind(width=force_square)
        self.clear_btn.bind(on_press=self.clear_input)

        # Botón Abrir Carpeta
        self.open_folder_btn = Button(
            text="\uf07c", font_name=FONT_PATH, background_normal="", background_color=COLOR_BOTONES,
            color=(1, 1, 1, 1), size_hint_x=0.125, size_hint_y=None, font_size='16sp'
        )
        self.open_folder_btn.bind(width=force_square)
        self.open_folder_btn.bind(on_press=self.open_downloads_in_player)

        # Botón Toggle MP4 / MP3
        self.format_toggle_btn = Button(
            text="MP4", font_size='12sp', bold=True, background_normal="", 
            background_color=COLOR_BOTONES, color=(1, 1, 1, 1),
            size_hint_x=0.125, size_hint_y=None
        )
        self.format_toggle_btn.bind(width=force_square)
        self.format_toggle_btn.bind(on_press=self.toggle_format_mode)
        
        buttons_top_layout.add_widget(self.paste_btn)
        buttons_top_layout.add_widget(self.clear_btn)
        buttons_top_layout.add_widget(self.open_folder_btn)
        buttons_top_layout.add_widget(self.format_toggle_btn)
        
        layout_main.add_widget(buttons_top_layout)

        # --- CUADRO DE TEXTO: ALTO DUPLICADO A 124 (Antes 62) ---
        self.url_input = TextInput(
            hint_text="Pega el link aquí...", 
            multiline=False, 
            padding=[12, 45, 12, 14],            # Ajuste de relleno vertical interno para centrar el texto
            background_active="", 
            background_normal="", 
            background_color=COLOR_BOTONES,
            foreground_color=(1, 1, 1, 1),
            hint_text_color=(0.55, 0.55, 0.58, 1),
            cursor_color=(1, 1, 1, 1),
            selection_color=(1, 1, 1, 0.2),
            size_hint_y=None, 
            height=124, 
            font_size='18sp'
        )
        self.url_input.bind(text=self.on_url_text_change)
        layout_main.add_widget(self.url_input)

        # --- BOTÓN DE DESCARGA PRINCIPAL: ALTO DUPLICADO A 120 (Antes 60) ---
        self.download_btn = Button(
            text="Descargar Video (MP4)", background_normal="", background_color=COLOR_BOTONES,
            color=(1, 1, 1, 1), size_hint_y=None, height=120, font_size='20sp', bold=True
        )
        self.download_btn.bind(on_press=self.start_download_thread)
        layout_main.add_widget(self.download_btn)

        # Visor de Logs
        self.scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False, do_scroll_y=True)
        self.log_label = Label(
            text="[color=888888][i] Esperando enlace de YouTube...[/i][/color]", 
            font_size='15sp', size_hint_y=None, halign='left', valign='top', markup=True
        )
        
        self.log_label.bind(width=lambda inv, val: setattr(inv, 'text_size', (val, None)))
        self.log_label.bind(texture_size=lambda inv, val: setattr(inv, 'height', val[1]))
        
        self.scroll.add_widget(self.log_label)
        layout_main.add_widget(self.scroll)
        
        self.tab_download.content = layout_main

        # PESTAÑA 2: HISTORIAL INTERACTIVO
        self.tab_history = TabbedPanelItem(text='Historial')
        self.tab_history.background_normal = ""
        self.tab_history.background_color = (0.12, 0.12, 0.13, 1)
        
        layout_history = BoxLayout(orientation='vertical', padding=20, spacing=15, size_hint=(1, 1))
        
        layout_history.add_widget(Label(
            text="Descargas Completadas", font_size='20sp', size_hint_y=None, height=40, bold=True, color=(0.8, 0.75, 0.95, 1)
        ))
        
        layout_history.add_widget(Label(
            text="[color=888888][i]Tip: Toca un archivo para reproducirlo directamente[/i][/color]",
            font_size='12sp', size_hint_y=None, height=20, markup=True
        ))
        
        self.scroll_hist = ScrollView(size_hint=(1, 1), do_scroll_x=False, do_scroll_y=True)
        
        self.history_container = BoxLayout(orientation='vertical', spacing=10, size_hint_y=None)
        self.history_container.bind(minimum_height=self.history_container.setter('height'))
        
        self.scroll_hist.add_widget(self.history_container)
        layout_history.add_widget(self.scroll_hist)
        
        # Botón Actualizar Historial
        self.refresh_btn = Button(
            text="Actualizar Lista", background_normal="", background_color=COLOR_BOTONES, 
            color=(1, 1, 1, 1), size_hint_y=None, height=52, bold=True
        )
        self.refresh_btn.bind(on_press=self.load_history_from_file)
        layout_history.add_widget(self.refresh_btn)
        
        self.tab_history.content = layout_history

        self.add_widget(self.tab_download)
        self.add_widget(self.tab_history)
        
        Clock.schedule_once(self.force_initial_tab, 0.1)
        Clock.schedule_once(self.check_shared_intent, 0.5)
        self.load_history_from_file(None)

    def toggle_format_mode(self, instance):
        self.download_mp3_mode = not self.download_mp3_mode
        if self.download_mp3_mode:
            self.format_toggle_btn.text = "MP3"
            self.format_toggle_btn.color = (0.2, 0.6, 1.0, 1) # Azul brillante solicitado
            self.download_btn.text = "Descargar Audio (MP3)"
            self.log("[color=66b3ff][*] Modo de descarga cambiado a AUDIO (MP3).[/color]")
        else:
            self.format_toggle_btn.text = "MP4"
            self.format_toggle_btn.color = (1, 1, 1, 1) # Blanco puro solicitado
            self.download_btn.text = "Descargar Video (MP4)"
            self.log("[color=ffffff][*] Modo de descarga cambiado a VIDEO (MP4).[/color]")

    def force_initial_tab(self, dt):
        self.switch_to(self.tab_download)

    def check_shared_intent(self, dt):
        try:
            from jnius import autoclass
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            Intent = autoclass('android.content.Intent')
            
            activity = PythonActivity.mActivity
            intent = activity.getIntent()
            action = intent.getAction()
            
            if action == Intent.ACTION_SEND:
                mime_type = intent.getType()
                if mime_type and "text/" in mime_type:
                    shared_text = intent.getStringExtra(Intent.EXTRA_TEXT)
                    if shared_text:
                        urls = re.findall(r'(https?://[^\s]+)', shared_text)
                        if urls:
                            self.url_input.text = urls[0]
                            self.log(f"[color=55ff55][*] Enlace recibido desde el menú Compartir.[/color]")
        except Exception as e:
            pass

    def open_downloads_in_player(self, instance):
        try:
            from jnius import autoclass
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            Intent = autoclass('android.content.Intent')
            Uri = autoclass('android.net.Uri')
            JavaString = autoclass('java.lang.String')
            StrictMode = autoclass('android.os.StrictMode')
            
            StrictMode.disableDeathOnFileUriExposure()
            
            folder_uri = Uri.parse(f"file://{DOWNLOADS_DIR}")
            
            intent = Intent(Intent.ACTION_VIEW)
            intent.setDataAndType(folder_uri, "resource/folder")
            intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_GRANT_READ_URI_PERMISSION)
            
            java_title = JavaString("Abrir carpeta con:")
            chooser_intent = Intent.createChooser(intent, java_title)
            chooser_intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            
            PythonActivity.mActivity.startActivity(chooser_intent)
            return
        except Exception as e:
            try:
                intent = Intent(Intent.ACTION_GET_CONTENT)
                intent.setType("*/*")
                intent.addCategory(Intent.CATEGORY_OPENABLE)
                java_title_backup = JavaString("Selecciona explorador:")
                chooser_backup = Intent.createChooser(intent, java_title_backup)
                chooser_backup.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                PythonActivity.mActivity.startActivity(chooser_backup)
            except Exception as err:
                self.log(f"[X] No se pudo lanzar el selector de archivos: {str(err)}")

    def play_specific_video(self, clean_title):
        is_mp3 = clean_title.endswith('.mp3')
        ext = '.mp3' if is_mp3 else '.mp4'
        mime = 'audio/*' if is_mp3 else 'video/*'
        
        base_name = clean_title.replace(".mp4", "").replace(".mp3", "").replace(".mkv", "").strip()
        file_path = os.path.join(DOWNLOADS_DIR, f"{base_name}{ext}")

        if not os.path.exists(file_path) and os.path.exists(DOWNLOADS_DIR):
            for file_in_dir in os.listdir(DOWNLOADS_DIR):
                if file_in_dir.lower().startswith(base_name.lower()[:15]) and file_in_dir.endswith(ext):
                    file_path = os.path.join(DOWNLOADS_DIR, file_in_dir)
                    break

        if os.path.exists(file_path):
            try:
                from jnius import autoclass
                
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                Intent = autoclass('android.content.Intent')
                Uri = autoclass('android.net.Uri')
                File = autoclass('java.io.File')
                JavaString = autoclass('java.lang.String')
                StrictMode = autoclass('android.os.StrictMode')
                
                StrictMode.disableDeathOnFileUriExposure()
                
                current_activity = PythonActivity.mActivity
                file_obj = File(file_path)
                file_uri = Uri.fromFile(file_obj)
                
                intent = Intent(Intent.ACTION_VIEW)
                intent.setDataAndType(file_uri, mime)
                intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_GRANT_READ_URI_PERMISSION)
                
                java_title = JavaString(f"Reproducir {ext[1:]} con:")
                
                chooser_intent = Intent.createChooser(intent, java_title)
                chooser_intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                
                current_activity.startActivity(chooser_intent)
                return
            except Exception as e:
                self.log(f"[X] Falló al iniciar el reproductor nativo: {str(e)}")
        else:
            self.log(f"[color=ff5555][X] Archivo no hallado físicamente en Download:[/color]\n{base_name}{ext}")

    def paste_from_native_clipboard(self, instance):
        try:
            contenido = Clipboard.paste()
            if contenido:
                self.url_input.text = str(contenido).strip()
                self.log("[color=bb99ff][*] Enlace pegado desde el portapapeles.[/color]")
        except Exception as e:
            pass

    def clear_input(self, instance):
        if self.typing_timer:
            self.typing_timer.cancel()
        self.url_input.text = ""
        self.last_checked_url = ""
        self.log("[color=55ff55][*][/color] Entrada limpia.")

    def clean_ansi(self, text):
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-b]*[ -/]*[@-~])')
        return ansi_escape.sub('', text)

    def log(self, text):
        cleaned_text = self.clean_ansi(text)
        self.log_label.text += f"\n{cleaned_text}"
        Clock.schedule_once(lambda dt: setattr(self.scroll, 'scroll_y', 0), 0.1)

    def save_to_history_file(self, title, is_mp3=False):
        ext_label = " (MP3)" if is_mp3 else " (MP4)"
        try:
            with open(HISTORY_FILE, 'a', encoding='utf-8') as f:
                f.write(f"OK - {title}{ext_label}\n")
            self.load_history_from_file(None)
            return
        except Exception as e:
            pass

        try:
            with open(BACKUP_HISTORY_FILE, 'a', encoding='utf-8') as f:
                f.write(f"OK - {title}{ext_label}\n")
            self.load_history_from_file(None)
        except Exception as e:
            pass

    def load_history_from_file(self, instance):
        self.history_container.clear_widgets()
        target_path = HISTORY_FILE if os.path.exists(HISTORY_FILE) else BACKUP_HISTORY_FILE
        
        if os.path.exists(target_path):
            try:
                with open(target_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                if lines:
                    for line in reversed(lines):
                        text_line = line.strip()
                        if not text_line: continue
                        
                        raw_title = text_line.replace("OK - ", "").strip()
                        if not raw_title: continue
                        
                        if " (MP3)" in raw_title:
                            clean_title = raw_title.replace(" (MP3)", "") + ".mp3"
                        elif " (MP4)" in raw_title:
                            clean_title = raw_title.replace(" (MP4)", "") + ".mp4"
                        else:
                            clean_title = raw_title if (raw_title.endswith('.mp4') or raw_title.endswith('.mp3')) else f"{raw_title}.mp4"
                        
                        btn_video = Button(
                            text=clean_title,
                            font_size='14sp',
                            size_hint_y=None,
                            height=58,
                            halign='left',
                            valign='middle',
                            padding=[15, 0],
                            background_normal="",
                            background_color=COLOR_BOTONES,
                            color=(0.9, 0.88, 0.95, 1),
                            text_size=(Window.width - 40, None)
                        )
                        btn_video.bind(on_press=lambda btn, t=clean_title: self.play_specific_video(t))
                        self.history_container.add_widget(btn_video)
                    return
            except Exception as e:
                pass
                
        self.history_container.add_widget(Label(
            text="No hay descargas registradas aún.",
            size_hint_y=None,
            height=40,
            color=(0.4, 0.4, 0.4, 1)
        ))

    def on_url_text_change(self, instance, value):
        url = value.strip()
        if not url:
            if self.typing_timer:
                self.typing_timer.cancel()
            return

        if url.startswith("http") and url != self.last_checked_url and len(url) > 15:
            if self.typing_timer:
                self.typing_timer.cancel()
            self.typing_timer = threading.Timer(1.0, self.trigger_verification, args=(url,))
            self.typing_timer.start()

    def trigger_verification(self, url):
        self.last_checked_url = url
        self.log("[color=b39ddb][*] Enlace detectado. Analizando...[/color]")
        threading.Thread(target=self.verify_video_auto, args=(url,)).start()

    def verify_video_auto(self, url):
        ydl_opts = {
            'skip_download': True, 'quiet': True, 'no_warnings': True, 'nocheckcertificate': True,
            'socket_timeout': 60,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36'
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                title = info.get('title', 'Desconocido')
                duration = info.get('duration_string', '0:00')
                self.log(f"\n[b][size=18sp][color=d1c4e9] Titulo: {title}[/color][/size][/b]\n[b][size=16sp][color=e1bee7] Duracion: {duration}[/color][/size][/b]\n")
        except Exception as e:
            pass 

    def start_download_thread(self, instance):
        url = self.url_input.text.strip()
        if not url: return
        self.download_btn.disabled = True
        
        if self.download_mp3_mode:
            threading.Thread(target=self.download_audio_mp3, args=(url,)).start()
        else:
            format_opt = 'b[ext=mp4]/best'
            threading.Thread(target=self.download_video, args=(url, format_opt)).start()

    def download_video(self, url, format_opt):
        out_template = os.path.join(DOWNLOADS_DIR, '%(title)s.%(ext)s')
        ydl_opts = {
            'format': format_opt, 
            'outtmpl': out_template, 
            'logger': MyLogger(self),
            'progress_hooks': [self.progress_hook], 
            'nocheckcertificate': True, 
            'socket_timeout': 60,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36'
        }
        self._execute_ydl(ydl_opts, url, is_mp3=False)

    def download_audio_mp3(self, url):
        out_template = os.path.join(DOWNLOADS_DIR, '%(title)s.mp3')
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': out_template,
            'logger': MyLogger(self),
            'progress_hooks': [self.progress_hook],
            'nocheckcertificate': True,
            'socket_timeout': 60,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
            'keepvideo': False,
        }
        self._execute_ydl(ydl_opts, url, is_mp3=True)

    def _execute_ydl(self, ydl_opts, url, is_mp3):
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                title = info.get('title', 'Archivo Descargado')
            self.log(f"[color=55ff55][*] Descarga terminada con éxito en 'Download'.[/color]")
            self.save_to_history_file(title, is_mp3=is_mp3)
        except Exception as e:
            try:
                ext_str = ".mp3" if is_mp3 else ".%(ext)s"
                backup_path = os.path.join(BASE_DIR, f"%(title)s{ext_str}")
                ydl_opts['outtmpl'] = backup_path
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    title = info.get('title', 'Archivo Descargado')
                self.log("[color=55ff55][*] Guardado de respaldo local con éxito.[/color]")
                self.save_to_history_file(title, is_mp3=is_mp3)
            except Exception as err:
                self.log(f"[color=ff5555][X] Fallo definitivo: {str(err)}[/color]")
        
        self.download_btn.disabled = False

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            percent = d.get('_percent_str', '0.0%')
            speed = d.get('_speed_str', '0.0B/s')
            percent = self.clean_ansi(percent).strip()
            speed = self.clean_ansi(speed).strip()
            lines = self.log_label.text.split('\n')
            if lines[-1].startswith("[*] Progreso:"):
                lines[-1] = f"[*] Progreso: {percent} | Vel: {speed}"
                self.log_label.text = '\n'.join(lines)
            else:
                self.log(f"[*] Progreso: {percent} | Vel: {speed}")

class MyLogger(object):
    def __init__(self, app): self.app = app
    def debug(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): self.app.log(f"[yt-dlp] {msg}")

class YTApp(App):
    def build(self): return YTDownloaderX11()
    def on_pause(self): return True

if __name__ == '__main__':
    YTApp().run()
