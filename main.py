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

Window.size = (480, 800)
Window.clear_color = (0.074, 0.074, 0.078, 1)

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

        # PESTAÑA 1: DESCARGADOR PRINCIPAL
        self.tab_download = TabbedPanelItem(text='Descargar')
        self.tab_download.background_normal = ""
        self.tab_download.background_color = (0.3, 0.18, 0.55, 1)
        
        layout_main = BoxLayout(orientation='vertical', padding=20, spacing=15, size_hint=(1, 1))

        layout_main.add_widget(Label(
            text="YTD Pro", font_size='24sp', size_hint_y=None, height=45, bold=True, color=(0.95, 0.95, 1, 1)
        ))

        # Contenedor para los botones superiores de acción rápidos (Centrados)
        buttons_top_layout = BoxLayout(orientation='horizontal', size_hint=(None, None), height=54, spacing=15)
        buttons_top_layout.width = 255  
        buttons_top_layout.pos_hint = {'center_x': 0.5}

        # Botón Pegar
        self.paste_btn = Button(
            text="\uf0ea", font_name=FONT_PATH, background_normal="", background_color=(0.48, 0.3, 1.0, 1), 
            color=(1, 1, 1, 1), size_hint=(None, 1), width=75, font_size='22sp'
        )
        self.paste_btn.bind(on_press=self.paste_from_native_clipboard)

        # Botón Limpiar
        self.clear_btn = Button(
            text="\uf1f8", font_name=FONT_PATH, background_normal="", background_color=(0.48, 0.3, 1.0, 1),
            color=(1, 1, 1, 1), size_hint=(None, 1), width=75, font_size='22sp'
        )
        self.clear_btn.bind(on_press=self.clear_input)

        # Botón Carpeta
        self.open_folder_btn = Button(
            text="\uf07c", font_name=FONT_PATH, background_normal="", background_color=(0.48, 0.3, 1.0, 1),
            color=(1, 1, 1, 1), size_hint=(None, 1), width=75, font_size='22sp'
        )
        self.open_folder_btn.bind(on_press=self.open_general_gallery)
        
        buttons_top_layout.add_widget(self.paste_btn)
        buttons_top_layout.add_widget(self.clear_btn)
        buttons_top_layout.add_widget(self.open_folder_btn)
        layout_main.add_widget(buttons_top_layout)

        # Caja de Texto
        self.url_input = TextInput(
            hint_text="Pega el link aquí...", multiline=False, padding=[12, 16, 12, 16],
            background_active="", background_normal="", background_color=(0.117, 0.117, 0.121, 1),
            foreground_color=(0.9, 0.9, 0.9, 1), hint_text_color=(0.5, 0.5, 0.5, 1),
            size_hint_y=None, height=52
        )
        self.url_input.bind(text=self.on_url_text_change)
        layout_main.add_widget(self.url_input)

        # Botón principal
        self.download_btn = Button(
            text="Descargar Video (MP4)", background_normal="", background_color=(0.48, 0.3, 1.0, 1),
            color=(1, 1, 1, 1), size_hint_y=None, height=56, font_size='18sp', bold=True
        )
        self.download_btn.bind(on_press=self.start_download_thread)
        layout_main.add_widget(self.download_btn)

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

        # PESTAÑA 2: HISTORIAL INTERACTIVO CON BOTONES DINÁMICOS
        self.tab_history = TabbedPanelItem(text='Historial')
        self.tab_history.background_normal = ""
        self.tab_history.background_color = (0.2, 0.15, 0.35, 1)
        
        layout_history = BoxLayout(orientation='vertical', padding=20, spacing=15, size_hint=(1, 1))
        
        layout_history.add_widget(Label(
            text="Descargas Completadas", font_size='20sp', size_hint_y=None, height=40, bold=True, color=(0.8, 0.75, 0.95, 1)
        ))
        
        layout_history.add_widget(Label(
            text="[color=888888][i]Tip: Toca un video de la lista para reproducirlo directamente[/i][/color]",
            font_size='12sp', size_hint_y=None, height=20, markup=True
        ))
        
        self.scroll_hist = ScrollView(size_hint=(1, 1), do_scroll_x=False, do_scroll_y=True)
        
        # Este contenedor alojará los botones de cada video de forma ordenada
        self.history_container = BoxLayout(orientation='vertical', spacing=10, size_hint_y=None)
        self.history_container.bind(minimum_height=self.history_container.setter('height'))
        
        self.scroll_hist.add_widget(self.history_container)
        layout_history.add_widget(self.scroll_hist)
        
        self.refresh_btn = Button(
            text="Actualizar Lista", background_normal="", background_color=(0.48, 0.3, 1.0, 1), size_hint_y=None, height=48, bold=True
        )
        self.refresh_btn.bind(on_press=self.load_history_from_file)
        layout_history.add_widget(self.refresh_btn)
        
        self.tab_history.content = layout_history

        self.add_widget(self.tab_download)
        self.add_widget(self.tab_history)
        
        Clock.schedule_once(self.force_initial_tab, 0.1)
        Clock.schedule_once(self.check_shared_intent, 0.5)
        self.load_history_from_file(None)

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

    def open_general_gallery(self, instance):
        """ Abre la galería global de videos del teléfono como respaldo """
        try:
            from jnius import autoclass
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            Intent = autoclass('android.content.Intent')
            Uri = autoclass('android.net.Uri')
            
            intent = Intent(Intent.ACTION_VIEW)
            intent.setDataAndType(Uri.parse("content://media/external/video/media"), "video/*")
            intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            
            PythonActivity.mActivity.startActivity(intent)
        except Exception as e:
            pass

    def play_specific_video(self, video_title):
        """ Busca el archivo físico en la carpeta Download y lo lanza en el reproductor nativo """
        # Reconstruimos el nombre exacto con el que yt-dlp guarda los archivos (.mp4)
        filename = f"{video_title}.mp4"
        video_path = os.path.join(DOWNLOADS_DIR, filename)

        # Si no lo encuentra por caracteres especiales, busca un archivo aproximado en la carpeta
        if not os.path.exists(video_path):
            if os.path.exists(DOWNLOADS_DIR):
                for f in os.listdir(DOWNLOADS_DIR):
                    if f.lower().startswith(video_title.lower()[:10]) and f.endswith('.mp4'):
                        video_path = os.path.join(DOWNLOADS_DIR, f)
                        break

        if os.path.exists(video_path):
            try:
                from jnius import autoclass
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                Intent = autoclass('android.content.Intent')
                Uri = autoclass('android.net.Uri')
                File = autoclass('java.io.File')
                
                file_object = File(video_path)
                intent = Intent(Intent.ACTION_VIEW)
                
                # Para evitar conflictos de permisos de lectura de URI en Android 11+, pasamos el archivo directo
                intent.setDataAndType(Uri.fromFile(file_object), "video/*")
                intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_GRANT_READ_URI_PERMISSION)
                
                PythonActivity.mActivity.startActivity(intent)
                return
            except Exception as e:
                self.log(f"[X] Error al abrir reproductor nativo: {str(e)}")
                
            try:
                subprocess.Popen(['termux-open', video_path])
            except Exception:
                pass
        else:
            self.log(f"[color=ff5555][X] El archivo ya no existe en Descargas:[/color] {filename}")

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

    def save_to_history_file(self, title):
        # Limpiamos el título de marcas de estado antes de persistirlo
        clean_title = title.replace("OK - ", "").strip()
        try:
            with open(HISTORY_FILE, 'a', encoding='utf-8') as f:
                f.write(f"OK - {clean_title}\n")
            self.load_history_from_file(None)
            return
        except Exception as e:
            pass

        try:
            with open(BACKUP_HISTORY_FILE, 'a', encoding='utf-8') as f:
                f.write(f"OK - {clean_title}\n")
            self.load_history_from_file(None)
        except Exception as e:
            pass

    def load_history_from_file(self, instance):
        # Limpiamos el contenedor viejo para renderizar la lista actualizada
        self.history_container.clear_widgets()
        
        target_path = HISTORY_FILE if os.path.exists(HISTORY_FILE) else BACKUP_HISTORY_FILE
        if os.path.exists(target_path):
            try:
                with open(target_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                if lines:
                    # Invertimos para que las descargas más nuevas queden arriba
                    for line in reversed(lines):
                        text_line = line.strip()
                        if text_line.startswith("OK - "):
                            video_title = text_line.replace("OK - ", "")
                        else:
                            video_title = text_line
                            
                        if not video_title: continue
                        
                        # Creamos un botón elegante por cada video de la lista
                        btn_video = Button(
                            text=f"\uf16a  {video_title}",
                            font_name=FONT_PATH,
                            size_hint_y=None,
                            height=54,
                            halign='left',
                            valign='middle',
                            padding=[15, 0],
                            background_normal="",
                            background_color=(0.14, 0.14, 0.16, 1),
                            color=(0.85, 0.8, 0.95, 1),
                            text_size=(Window.width - 60, None)
                        )
                        # Al tocar este botón específico, se manda a reproducir su título correspondiente
                        btn_video.bind(on_press=lambda btn, title=video_title: self.play_specific_video(title))
                        self.history_container.add_widget(btn_video)
                    return
            except Exception as e:
                pass
                
        # Si no hay registros, mostramos una etiqueta sutil
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

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                title = info.get('title', 'Video Descargado')
            self.log("[color=55ff55][*] Descarga terminada con exito en 'Download'.[/color]")
            self.save_to_history_file(title)
        except Exception as e:
            try:
                backup_path = os.path.join(BASE_DIR, '%(title)s.%(ext)s')
                ydl_opts['outtmpl'] = backup_path
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    title = info.get('title', 'Video Descargado')
                self.log("[color=55ff55][*] Guardado de respaldo local con éxito.[/color]")
                self.save_to_history_file(title)
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
    
    def on_pause(self):
        return True

if __name__ == '__main__':
    YTApp().run()
