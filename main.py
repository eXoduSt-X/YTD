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
from kivy.uix.widget import Widget
from kivy.core.window import Window
from kivy.core.clipboard import Clipboard
from kivy.clock import Clock
from kivy.graphics import RoundedRectangle, Color
from kivy.graphics.fbo import Fbo  # IMPORTACIÓN CRÍTICA PARA EL FIX GRÁFICO
from kivy.graphics.texture import Texture
from kivy.properties import ListProperty, NumericProperty
import yt_dlp
from kivy.config import Config
Config.set('graphics', 'multisamples', '0')


Window.size = (480, 800)

# --- CONFIGURACIÓN GLOBAL DE COLOR ---
Window.clear_color = (0.03, 0.03, 0.04, 1)

# Color gris oscuro tipo input (igual a tu caja de texto)
CONTROL_BG = (0.10, 0.10, 0.11, 1)
ACCENT_COLOR = (0.2, 0.6, 1.0, 1)
TEXT_COLOR = (0.95, 0.95, 0.97, 1)

DOWNLOADS_DIR = '/storage/emulated/0/Download'
HISTORY_FILE = os.path.join(DOWNLOADS_DIR, 'download_history.txt')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKUP_HISTORY_FILE = os.path.join(BASE_DIR, 'download_history.txt')
FONT_PATH = os.path.join(BASE_DIR, "fontawesome.ttf")

class RoundedButton(Button):
    bg_color = ListProperty(CONTROL_BG)
    radius = NumericProperty(12)
    
    def __init__(self, **kwargs):
        self.bg_color = kwargs.pop('bg_color', CONTROL_BG)
        self.radius = kwargs.pop('radius', 12)
        kwargs['background_normal'] = ''
        kwargs['background_color'] = (0, 0, 0, 0)
        super(RoundedButton, self).__init__(**kwargs)
        self.color = kwargs.get('color', TEXT_COLOR)
        Clock.schedule_once(self._draw_background, 0)
        
    def _draw_background(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*self.bg_color)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[self.radius]*4)
        self.bind(pos=self._update_rect, size=self._update_rect)
        
    def _update_rect(self, instance, value):
        if hasattr(self, 'rect'):
            self.rect.pos = instance.pos
            self.rect.size = instance.size


# =============================================================================
# COMPONENTE REESTRUCTURADO Y CORREGIDO PARA EVITAR GLITCHES EN ANDROID
# =============================================================================
class RoundedTextInput(TextInput):
    bg_color = ListProperty(CONTROL_BG)
    radius = NumericProperty(12)
    
    def __init__(self, **kwargs):
        self.bg_color = kwargs.pop('bg_color', CONTROL_BG)
        self.radius = kwargs.pop('radius', 12)
        
        # Ajustamos los valores tipográficos por defecto
        kwargs['foreground_color'] = kwargs.get('foreground_color', TEXT_COLOR)
        kwargs['hint_text_color'] = kwargs.get('hint_text_color', (0.5, 0.5, 0.5, 1))
        kwargs['padding'] = kwargs.get('padding', [15, 15, 15, 15])
        
        super(RoundedTextInput, self).__init__(**kwargs)
        
        # Colores para el cursor y para la barra selectora de Android de manera limpia
        self.cursor_color = ACCENT_COLOR  
        self.selection_color = (*ACCENT_COLOR[:3], 0.3)  
        
        # Centrado vertical automático del texto
        self.bind(height=self._center_text_vertical, font_size=self._center_text_vertical)
        
        # Enlazamos la regeneración de texturas dinámicas cuando cambia el layout
        self.bind(size=self._refresh_background, pos=self._refresh_background)

    def _center_text_vertical(self, *args):
        vertical_padding = (self.height - self.line_height) / 2
        self.padding = [15, vertical_padding, 15, vertical_padding]

    def _refresh_background(self, *args):
        # Previene ejecuciones inválidas en fases de inicialización sin dimensiones
        if self.width <= 0 or self.height <= 0:
            return
            
        # Creamos una textura Fbo en memoria gráfica con las esquinas redondeadas
        fbo = Fbo(size=self.size)
        with fbo:
            Color(*self.bg_color)
            RoundedRectangle(pos=(0, 0), size=self.size, radius=[self.radius] * 4)
        fbo.draw()
        
        # Asignamos la textura generada directamente a las propiedades de Kivy.
        # De esta manera, Kivy refresca y vacía los residuos gráficos de selección de Android.
        self.background_normal = fbo.texture
        self.background_active = fbo.texture


class YTDownloaderX11(TabbedPanel):
    def __init__(self, **kwargs):
        super(YTDownloaderX11, self).__init__(**kwargs)
        self.do_default_tab = False
        self.last_checked_url = ""
        self.typing_timer = None 
        self.download_mp3_mode = False

        # PESTAÑA 1
        self.tab_download = TabbedPanelItem(text='Descargar')
        self.tab_download.background_normal = ""
        self.tab_download.background_color = CONTROL_BG
        
        layout_main = BoxLayout(orientation='vertical', padding=20, spacing=15, size_hint=(1, 1))

        layout_main.add_widget(Label(
            text="Youtube Downloader", font_size='22sp', size_hint_y=None, height=50, bold=True, color=TEXT_COLOR
        ))

        # --- FILA DE BOTONES ---
        buttons_top_layout = BoxLayout(orientation='horizontal', size_hint_x=1, size_hint_y=None, height=110, spacing=8)

        self.paste_btn = RoundedButton(
            text="\uf0ea", font_name=FONT_PATH, size_hint=(0.25, None), 
            height=110, font_size='22sp', radius=10
        )
        self.paste_btn.bind(on_press=self.paste_from_native_clipboard)

        self.clear_btn = RoundedButton(
            text="\uf1f8", font_name=FONT_PATH, size_hint=(0.25, None), 
            height=110, font_size='22sp', radius=10
        )
        self.clear_btn.bind(on_press=self.clear_input)

        self.open_folder_btn = RoundedButton(
            text="\uf07c", font_name=FONT_PATH, size_hint=(0.25, None), 
            height=110, font_size='22sp', radius=10
        )
        self.open_folder_btn.bind(on_press=self.open_downloads_in_player)

        self.format_toggle_btn = RoundedButton(
            text="MP4", font_size='16sp', bold=True, size_hint=(0.25, None), 
            height=110, radius=10
        )
        self.format_toggle_btn.bind(on_press=self.toggle_format_mode)
        
        buttons_top_layout.add_widget(self.paste_btn)
        buttons_top_layout.add_widget(self.clear_btn)
        buttons_top_layout.add_widget(self.open_folder_btn)
        buttons_top_layout.add_widget(self.format_toggle_btn)
        layout_main.add_widget(buttons_top_layout)

        # Entrada de Texto
        self.url_input = RoundedTextInput(
            hint_text="Pega el link aquí...", multiline=False,
            size_hint_y=None, height=110, font_size='16sp', radius=12
        )
        self.url_input.bind(text=self.on_url_text_change)
        layout_main.add_widget(self.url_input)

        # Botón Principal
        self.download_btn = RoundedButton(
            text="Descargar Video (MP4)", size_hint_y=None, height=110, 
            font_size='18sp', bold=True, radius=16
        )
        self.download_btn.bind(on_press=self.start_download_thread)
        layout_main.add_widget(self.download_btn)

        # Visor de Logs
        self.scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False, do_scroll_y=True)
        self.log_label = Label(
            text="[color=888888][i] Esperando enlace de YouTube...[/i][/color]", 
            font_size='15sp', size_hint_y=None, halign='left', valign='top', 
            markup=True, color=(0.7, 0.7, 0.75, 1)
        )
        self.log_label.bind(width=lambda inv, val: setattr(inv, 'text_size', (val, None)))
        self.log_label.bind(texture_size=lambda inv, val: setattr(inv, 'height', val[1]))
        
        self.scroll.add_widget(self.log_label)
        layout_main.add_widget(self.scroll)
        
        self.tab_download.content = layout_main

        # PESTAÑA 2
        self.tab_history = TabbedPanelItem(text='Historial')
        self.tab_history.background_normal = ""
        self.tab_history.background_color = (0.12, 0.12, 0.13, 1)
        
        layout_history = BoxLayout(orientation='vertical', padding=20, spacing=15, size_hint=(1, 1))
        
        layout_history.add_widget(Label(
            text="Descargas Completadas", font_size='20sp', size_hint_y=None, 
            height=45, bold=True, color=TEXT_COLOR
        ))
        
        layout_history.add_widget(Label(
            text="[color=888888][i]Toca un archivo para reproducirlo[/i][/color]",
            font_size='12sp', size_hint_y=None, height=20, markup=True
        ))
        
        self.scroll_hist = ScrollView(size_hint=(1, 1), do_scroll_x=False, do_scroll_y=True)
        self.history_container = BoxLayout(orientation='vertical', spacing=10, size_hint_y=None)
        self.history_container.bind(minimum_height=self.history_container.setter('height'))
        
        self.scroll_hist.add_widget(self.history_container)
        layout_history.add_widget(self.scroll_hist)
        
        self.refresh_btn = RoundedButton(
            text="Actualizar Lista", size_hint_y=None, height=55, 
            bold=True, radius=12
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
            self.format_toggle_btn.color = ACCENT_COLOR
            self.download_btn.text = "Descargar Audio (MP3)"
            self.log("[color=66b3ff][*] Modo de descarga cambiado a AUDIO (MP3).[/color]")
        else:
            self.format_toggle_btn.text = "MP4"
            self.format_toggle_btn.color = TEXT_COLOR
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
        bytes_label = " (MP3)" if is_mp3 else " (MP4)"
        try:
            with open(HISTORY_FILE, 'a', encoding='utf-8') as f:
                f.write(f"OK - {title}{bytes_label}\n")
            self.load_history_from_file(None)
            return
        except Exception as e:
            pass

        try:
            with open(BACKUP_HISTORY_FILE, 'a', encoding='utf-8') as f:
                f.write(f"OK - {title}{bytes_label}\n")
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
                        
                        btn_video = RoundedButton(
                            text=clean_title,
                            font_size='14sp',
                            size_hint_y=None,
                            height=58,
                            halign='left',
                            valign='middle',
                            padding=[15, 0],
                            color=(0.9, 0.88, 0.95, 1),
                            text_size=(Window.width - 40, None),
                            radius=10
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
                self.log(f"[color=55ff55][*] Descarga terminada (backup).[/color]")
                self.save_to_history_file(title, is_mp3=is_mp3)
            except Exception as e2:
                self.log(f"[color=ff5555][X] Error en descarga: {str(e2)}[/color]")
        finally:
            Clock.schedule_once(lambda dt: setattr(self.download_btn, 'disabled', False), 0)

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            percent = d.get('_percent_str', '0%')
            speed = d.get('_speed_str', '0 KiB/s')
            eta = d.get('_eta_str', '0s')
            self.log(f"[color=aaaaaa]Descargando... {percent} | {speed} | ETA: {eta}[/color]")
        elif d['status'] == 'finished':
            self.log("[color=55ff55][*] Procesando archivo final...[/color]")

class MyLogger:
    def __init__(self, app_instance):
        self.app = app_instance

    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        self.app.log(f"[color=ff5555][X] {msg}[/color]")

class YTDownloaderApp(App):
    def build(self):
        return YTDownloaderX11()

if __name__ == '__main__':
    YTDownloaderApp().run()

```
