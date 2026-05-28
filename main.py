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
        buttons_top_layout.width = 255  # (3 botones * 75 de ancho) + (2 espacios * 15)
        buttons_top_layout.pos_hint = {'center_x': 0.5}

        # Botón Pegar -> Icono "Paste" (\uf0ea)
        self.paste_btn = Button(
            text="\uf0ea", font_name=FONT_PATH, background_normal="", background_color=(0.48, 0.3, 1.0, 1), 
            color=(1, 1, 1, 1), size_hint=(None, 1), width=75, font_size='22sp'
        )
        self.paste_btn.bind(on_press=self.paste_from_native_clipboard)

        # Botón Limpiar -> Icono "Trash" (\uf1f8)
        self.clear_btn = Button(
            text="\uf1f8", font_name=FONT_PATH, background_normal="", background_color=(0.48, 0.3, 1.0, 1),
            color=(1, 1, 1, 1), size_hint=(None, 1), width=75, font_size='22sp'
        )
        self.clear_btn.bind(on_press=self.clear_input)

        # Botón Carpeta -> Icono "Folder Open" (\uf07c)
        self.open_folder_btn = Button(
            text="\uf07c", font_name=FONT_PATH, background_normal="", background_color=(0.48, 0.3, 1.0, 1),
            color=(1, 1, 1, 1), size_hint=(None, 1), width=75, font_size='22sp'
        )
        self.open_folder_btn.bind(on_press=self.open_downloads_in_player)
        
        buttons_top_layout.add_widget(self.paste_btn)
        buttons_top_layout.add_widget(self.clear_btn)
        buttons_top_layout.add_widget(self.open_folder_btn)
        layout_main.add_widget(buttons_top_layout)

        # Caja de Texto expandida
        self.url_input = TextInput(
            hint_text="Pega el link aquí...", multiline=False, padding=[12, 16, 12, 16],
            background_active="", background_normal="", background_color=(0.117, 0.117, 0.121, 1),
            foreground_color=(0.9, 0.9, 0.9, 1), hint_text_color=(0.5, 0.5, 0.5, 1),
            size_hint_y=None, height=52
        )
        self.url_input.bind(text=self.on_url_text_change)
        layout_main.add_widget(self.url_input)

        # Botón principal de acción directa
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

        # PESTAÑA 2: HISTORIAL INTERACTIVO (Modificado de forma segura)
        self.tab_history = TabbedPanelItem(text='Historial')
        self.tab_history.background_normal = ""
        self.tab_history.background_color = (0.2, 0.15, 0.35, 1)
        
        layout_history = BoxLayout(orientation='vertical', padding=20, spacing=15, size_hint=(1, 1))
        
        layout_history.add_widget(Label(
            text="Descargas Completadas", font_size='20sp', size_hint_y=None, height=40, bold=True, color=(0.8, 0.75, 0.95, 1)
        ))
        
        layout_history.add_widget(Label(
            text="[color=888888][i]Tip: Toca un video para abrirlo con el reproductor del sistema[/i][/color]",
            font_size='12sp', size_hint_y=None, height=20, markup=True
        ))
        
        self.scroll_hist = ScrollView(size_hint=(1, 1), do_scroll_x=False, do_scroll_y=True)
        
        # Contenedor dinámico vertical para alojar los botones individuales de cada video
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

    def open_downloads_in_player(self, instance):
        """ Invoca al reproductor de video nativo de Android apuntando directamente al directorio de descargas """
        try:
            from jnius import autoclass
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            Intent = autoclass('android.content.Intent')
            Uri = autoclass('android.net.Uri')
            
            intent = Intent(Intent.ACTION_VIEW)
            intent.setDataAndType(Uri.parse("content://media/external/video/media"), "video/*")
            intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            
            PythonActivity.mActivity.startActivity(intent)
            return
        except Exception as e:
            pass

        try:
            target_to_open = DOWNLOADS_DIR if os.path.exists(DOWNLOADS_DIR) else BASE_DIR
            subprocess.Popen(['termux-open', target_to_open])
        except Exception as err:
            pass

    def play_specific_video(self, video_title):
        """ Intenta localizar el archivo exacto en la carpeta Download e invoca el menú nativo 'Abrir con...' """
        clean_name = video_title.strip()
        video_path = os.path.join(DOWNLOADS_DIR, f"{clean_name}.mp4")

        # Búsqueda de respaldo por coincidencia parcial si el título cambió sutilmente
        if not os.path.exists(video_path) and os.path.exists(DOWNLOADS_DIR):
            for f in os.listdir(DOWNLOADS_DIR):
                if f.lower().startswith(clean_name.lower()[:10]) and f.endswith('.mp4'):
                    video_path = os.path.join(DOWNLOADS_DIR, f)
                    break

        if os.path.exists(video_path):
            try:
                from jnius import autoclass
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                Intent = autoclass('android.content.Intent')
                Uri = autoclass('android.net.Uri')
                File = autoclass('java.io.File')
                
                file_obj = File(video_path)
                file_uri = Uri.fromFile(file_obj)
                
                intent = Intent(Intent.ACTION_VIEW)
                intent.setDataAndType(file_uri, "video/*")
                intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_GRANT_READ_URI_PERMISSION)
                
                chooser = Intent.createChooser(intent, "Abrir video con:")
                chooser.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                
                PythonActivity.mActivity.startActivity(chooser)
                return
            except Exception as e:
                self.log(f"[X] Error en selector nativo: {str(e)}")
        else:
            self.log(f"[color=ff5555][X] Archivo no localizado en Download:[/color]\n{clean_name}.mp4")

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
        try:
            with open(HISTORY_FILE, 'a', encoding='utf-8') as f:
                f.write(f"OK - {title}\n")
            self.load_history_from_file(None)
            return
        except Exception as e:
            pass

        try:
            with open(BACKUP_HISTORY_FILE, 'a', encoding='utf-8') as f:
                f.write(f"OK - {title}\n")
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
                        
                        # Limpiamos el prefijo 'OK - ' para obtener la cadena pura del título
                        video_title = text_line.replace("OK - ", "").strip()
                        if not video_title: continue
                        
                        # Usamos markup=True. El icono de play (\uf01d) se renderiza explícitamente en FontAwesome
                        # Al cerrar la etiqueta [/font], obligamos a Kivy a usar la fuente genérica por defecto de Android para el título
                        markup_text = f"[font={FONT_PATH}]\uf01d[/font]  {video_title}"
                        
                        btn_video = Button(
                            text=markup_text,
                            markup=True,
                            font_size='15sp',
                            size_hint_y=None,
                            height=58,
                            halign='left',
                            valign='middle',
                            padding=[15, 0],
                            background_normal="",
                            background_color=(0.12, 0.12, 0.14, 1),
                            color=(0.9, 0.88, 0.95, 1),
                            text_size=(Window.width - 40, None)
                        )
                        # Vinculamos directamente el evento para disparar la acción 'Abrir con...' de este archivo
                        btn_video.bind(on_press=lambda btn, t=video_title: self.play_specific_video(t))
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
