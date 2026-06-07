import sys
import os
import subprocess
import shutil
import json
import urllib.request
import zipfile
import io
import tempfile
import threading
import time
import base64
from pathlib import Path

import numpy as np

try:
    import sounddevice as sd
    import soundfile as sf
    HAS_SOUNDDEVICE = True
except ImportError:
    HAS_SOUNDDEVICE = False

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFileDialog, QFrame, QMessageBox,
    QSlider, QProgressBar, QMenu, QScrollArea, QSizePolicy, QDialog
)
from PyQt6.QtGui import QPainterPath
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QRect
from PyQt6.QtGui import QFont, QPainter, QColor, QPen, QBrush, QLinearGradient


# ==================== TRANSLATIONS ====================
TRANSLATIONS = {
    'RU': {
        'app_title': 'DDNet Sound Replacer',
        'select_lang': 'Выберите язык / Select language',
        'lang_ru': 'Русский',
        'lang_en': 'English',

        # FFmpeg
        'ffmpeg_found': 'FFmpeg: {}',
        'ffmpeg_not_found': "FFmpeg не найден — нажмите 'Скачать' ниже",
        'ffmpeg_install_info': 'FFmpeg нужен для конвертации .mp3 → .wv\nБудет установлен в C:\\ffmpeg\\bin 100MB)',
        'ffmpeg_download': 'Скачать и установить FFmpeg',
        'ffmpeg_browse': 'Указать папку...',
        'ffmpeg_downloading': 'Скачивание ffmpeg... (~100MB)',
        'ffmpeg_downloaded': 'Скачано: {:.1f} / {:.1f} MB',
        'ffmpeg_extracting': 'Распаковка...',
        'ffmpeg_done': 'Готово!',
        'ffmpeg_installed': 'FFmpeg уже установлен!',
        'ffmpeg_extract_error': 'Не удалось распаковать ffmpeg',
        'ffmpeg_download_error': 'Не удалось скачать ffmpeg:\n{}\n\nПопробуйте скачать вручную:\nhttps://www.gyan.dev/ffmpeg/builds/\n\nИли используйте батник install_ffmpeg.bat',
        'ffmpeg_manual': 'В папке нет ffmpeg.exe!',

        # Source player
        'source_title': 'Исходный файл (который заменяем)',
        'drop_folder': 'Перетащите сюда папку audio\nили',
        'open_folder': 'Открыть папку',
        'no_file': 'Нет файла',
        'select_file': 'Выбрать файл...',
        'prev': 'Предыдущий',
        'next': 'Следующий',
        'empty_folder': 'В папке нет аудио файлов!',

        # Editor player
        'new_title': 'Новый звук (заменяющий)',
        'drop_file': 'Перетащите сюда файл\nили',
        'choose_file': 'Выбрать файл',
        'speed': 'Скорость:',
        'trim_full': 'Обрезка: полный файл',
        'trim_info': 'Обрезка: {}-{} ({})',

        # Target card
        'target_replace': 'Будет заменён в:\n{}',

        # Replace button
        'replace': 'ЗАМЕНИТЬ',
        'success': 'Успешно заменено',

        # Errors
        'error': 'Ошибка',
        'error_ffmpeg': 'FFmpeg вернул ошибку:\n{}',
        'error_not_found': 'FFmpeg не найден!\nНажмите "Скачать и установить" выше.',
        'error_replace': 'Не удалось заменить файл:\n{}',
        'error_load': 'Не удалось загрузить: {}',
    },
    'EN': {
        'app_title': 'DDNet Sound Replacer',
        'select_lang': 'Select language / Выберите язык',
        'lang_ru': 'Russian',
        'lang_en': 'English',

        # FFmpeg
        'ffmpeg_found': 'FFmpeg: {}',
        'ffmpeg_not_found': "FFmpeg not found — click 'Download' below",
        'ffmpeg_install_info': 'FFmpeg is needed to convert .mp3 → .wv\nWill be installed to C:\\ffmpeg\\bin (~100MB)',
        'ffmpeg_download': 'Download and install FFmpeg',
        'ffmpeg_browse': 'Browse folder...',
        'ffmpeg_downloading': 'Downloading ffmpeg... (~100MB)',
        'ffmpeg_downloaded': 'Downloaded: {:.1f} / {:.1f} MB',
        'ffmpeg_extracting': 'Extracting...',
        'ffmpeg_done': 'Done!',
        'ffmpeg_installed': 'FFmpeg already installed!',
        'ffmpeg_extract_error': 'Failed to extract ffmpeg',
        'ffmpeg_download_error': 'Failed to download ffmpeg:\n{}\n\nTry downloading manually:\nhttps://www.gyan.dev/ffmpeg/builds/\n\nOr use install_ffmpeg.bat',
        'ffmpeg_manual': 'ffmpeg.exe not found in folder!',

        # Source player
        'source_title': 'Source file (to replace)',
        'drop_folder': 'Drop audio folder here\nor',
        'open_folder': 'Open folder',
        'no_file': 'No file',
        'select_file': 'Select file...',
        'prev': 'Previous',
        'next': 'Next',
        'empty_folder': 'No audio files in folder!',

        # Editor player
        'new_title': 'New sound (replacement)',
        'drop_file': 'Drop file here\nor',
        'choose_file': 'Choose file',
        'speed': 'Speed:',
        'trim_full': 'Trim: full file',
        'trim_info': 'Trim: {}-{} ({})',

        # Target card
        'target_replace': 'Will be replaced in:\n{}',

        # Replace button
        'replace': 'REPLACE',
        'success': 'Successfully replaced',

        # Errors
        'error': 'Error',
        'error_ffmpeg': 'FFmpeg error:\n{}',
        'error_not_found': 'FFmpeg not found!\nClick "Download and install" above.',
        'error_replace': 'Failed to replace file:\n{}',
        'error_load': 'Failed to load: {}',
    }
}

_current_lang = 'RU'

def tr(key, *args):
    text = TRANSLATIONS.get(_current_lang, TRANSLATIONS['RU']).get(key, key)
    if args:
        return text.format(*args)
    return text

# ==================== LANGUAGE SELECTOR ====================
class LanguageSelector(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('')
        self.setFixedSize(200, 100)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setStyleSheet("""
            QDialog {
                background-color: #0a1f0a;
                border: 2px solid #3a7a3a;
                border-radius: 8px;
            }
            QPushButton {
                background-color: #3a7a3a;
                color: #ffffff;
                border: 2px solid #4a9a4a;
                border-radius: 6px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4a9a4a;
                border-color: #66bb6a;
            }
            QPushButton:pressed {
                background-color: #2a5a2a;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.ru_btn = QPushButton('RU')
        self.ru_btn.setFixedSize(80, 70)
        self.ru_btn.clicked.connect(lambda: self.select_lang('RU'))
        layout.addWidget(self.ru_btn)

        self.en_btn = QPushButton('ENG')
        self.en_btn.setFixedSize(80, 70)
        self.en_btn.clicked.connect(lambda: self.select_lang('EN'))
        layout.addWidget(self.en_btn)

        self.selected_lang = None

    def select_lang(self, lang):
        self.selected_lang = lang
        self.accept()

def get_config_path():
    if sys.platform == 'win32':
        config_dir = Path(os.environ.get('APPDATA', Path.home())) / 'DDNetSoundReplacer'
    else:
        config_dir = Path.home() / '.config' / 'DDNetSoundReplacer'
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / 'config.json'

def load_config():
    path = get_config_path()
    if path.exists():
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {}

def save_config(cfg):
    path = get_config_path()
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

def get_subprocess_kwargs():
    """Get subprocess kwargs to hide console window on Windows."""
    kwargs = {}
    if sys.platform == 'win32':
        kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
    return kwargs

def find_ffmpeg():
    ffmpeg_path = shutil.which('ffmpeg')
    ffplay_path = shutil.which('ffplay')

    if ffmpeg_path and ffplay_path:
        return str(Path(ffmpeg_path).parent)

    cfg = load_config()
    saved_path = cfg.get('ffmpeg_dir', '')
    if saved_path:
        p = Path(saved_path)
        if (p / 'ffmpeg.exe').exists() and (p / 'ffplay.exe').exists():
            return str(p)

    if sys.platform == 'win32':
        possible_paths = [
            Path(r'C:\ffmpeg\bin'),
            Path(r'C:\Program Files\ffmpeg\bin'),
            Path(r'C:\Program Files (x86)\ffmpeg\bin'),
            Path.home() / 'ffmpeg' / 'bin',
            Path(r'C:\Users') / os.environ.get('USERNAME', '') / 'ffmpeg' / 'bin',
        ]
        for p in possible_paths:
            if (p / 'ffmpeg.exe').exists() and (p / 'ffplay.exe').exists():
                return str(p)

    return None

class PlayPauseButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_playing = False
        self.setFixedSize(40, 40)
        self.setStyleSheet("""
            QPushButton {
                background-color: #4a9a4a;
                border-radius: 20px;
                border: none;
            }
            QPushButton:hover { background-color: #6aba6a; }
            QPushButton:pressed { background-color: #3a7a3a; }
        """)
    def set_playing(self, playing):
        self._is_playing = playing
        self.update()
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#4a9a4a"))
        painter.drawEllipse(self.rect())
        painter.setBrush(QColor("#ffffff"))
        if self._is_playing:
            bar_w, bar_h, gap = 4, 14, 3
            cx, cy = self.width() // 2, self.height() // 2
            painter.drawRect(cx - gap//2 - bar_w, cy - bar_h//2, bar_w, bar_h)
            painter.drawRect(cx + gap//2, cy - bar_h//2, bar_w, bar_h)
        else:
            cx, cy = self.width() // 2, self.height() // 2
            size = 8
            path = QPainterPath()
            path.moveTo(cx - size//2 + 1, cy - size)
            path.lineTo(cx - size//2 + 1, cy + size)
            path.lineTo(cx + size + 1, cy)
            path.closeSubpath()
            painter.drawPath(path)
        painter.end()

class FfmpegDownloader(QThread):
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished_download = pyqtSignal(str)
    error = pyqtSignal(str)

    def run(self):
        try:
            ffmpeg_dir = Path(r'C:\ffmpeg')
            bin_dir = ffmpeg_dir / 'bin'

            if (bin_dir / 'ffmpeg.exe').exists() and (bin_dir / 'ffplay.exe').exists():
                self.status.emit(tr("ffmpeg_installed"))
                self.finished_download.emit(str(bin_dir))
                return

            url = 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip'

            self.status.emit(tr("ffmpeg_downloading"))
            self.progress.emit(5)

            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})

            with urllib.request.urlopen(req, timeout=300) as response:
                total_size = int(response.headers.get('Content-Length', 0))
                downloaded = 0
                chunk_size = 8192
                data = io.BytesIO()

                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    data.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        percent = int((downloaded / total_size) * 70) + 5
                        self.progress.emit(min(percent, 75))
                        mb = downloaded / (1024*1024)
                        total_mb = total_size / (1024*1024)
                        self.status.emit(tr("ffmpeg_downloaded", mb, total_mb))

            self.status.emit(tr("ffmpeg_extracting"))
            self.progress.emit(80)

            ffmpeg_dir.mkdir(parents=True, exist_ok=True)

            with zipfile.ZipFile(data) as zf:
                zf.extractall(path=str(ffmpeg_dir))

            extracted = None
            for item in ffmpeg_dir.iterdir():
                if item.is_dir() and item.name.startswith('ffmpeg-'):
                    extracted = item
                    break

            if extracted:
                bin_source = extracted / 'bin'
                if bin_source.exists():
                    if bin_dir.exists():
                        shutil.rmtree(bin_dir)
                    shutil.copytree(bin_source, bin_dir)
                    shutil.rmtree(extracted)

            self.progress.emit(100)
            self.status.emit(tr("ffmpeg_done"))

            if (bin_dir / 'ffmpeg.exe').exists():
                self.finished_download.emit(str(bin_dir))
            else:
                self.error.emit(tr("ffmpeg_extract_error"))

        except Exception as e:
            self.error.emit(str(e))

class WaveformWidget(QWidget):
    trim_changed = pyqtSignal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = None
        self.samplerate = 44100
        self.duration = 0
        self.trim_start = 0.0
        self.trim_end = 1.0
        self.dragging = None
        self.setMinimumHeight(90)
        self.setMaximumHeight(110)

    def set_audio(self, filepath):
        try:
            if HAS_SOUNDDEVICE:
                self.data, self.samplerate = sf.read(filepath, dtype='float32')
                if len(self.data.shape) > 1:
                    self.data = self.data[:, 0]
                self.duration = len(self.data) / self.samplerate
                self.trim_start = 0.0
                self.trim_end = self.duration
                self.update()
        except:
            self.data = None
            self.duration = 0

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        painter.fillRect(self.rect(), QColor("#0f2a0f"))

        if self.data is None or len(self.data) == 0 or self.duration == 0:
            painter.setPen(QColor("#666"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Waveform")
            return

        samples_per_pixel = max(1, len(self.data) // w)

        gradient = QLinearGradient(0, 0, 0, h)
        gradient.setColorAt(0, QColor("#6aba6a"))
        gradient.setColorAt(0.5, QColor("#8ada8a"))
        gradient.setColorAt(1, QColor("#6aba6a"))

        pen = QPen(QBrush(gradient), 1)
        painter.setPen(pen)

        for x in range(w):
            start_idx = x * samples_per_pixel
            end_idx = min(start_idx + samples_per_pixel, len(self.data))
            if start_idx < len(self.data):
                chunk = self.data[start_idx:end_idx]
                max_val = np.max(np.abs(chunk)) if len(chunk) > 0 else 0
                y = int(h / 2)
                height = int(max_val * (h / 2) * 0.9)
                painter.drawLine(x, y - height, x, y + height)

        if self.duration > 0:
            start_x = int((self.trim_start / self.duration) * w)
            end_x = int((self.trim_end / self.duration) * w)

            painter.fillRect(QRect(0, 0, start_x, h), QColor(0, 0, 0, 150))
            painter.fillRect(QRect(end_x, 0, w - end_x, h), QColor(0, 0, 0, 150))

            painter.setPen(QPen(QColor("#c0f0c0"), 2))
            painter.drawLine(start_x, 0, start_x, h)
            painter.drawLine(end_x, 0, end_x, h)

            handle_w = 16
            handle_h = 22
            pad = 4

            sx = max(pad + handle_w//2, min(start_x, w - pad - handle_w//2))
            ex = max(pad + handle_w//2, min(end_x, w - pad - handle_w//2))

            glow_pen = QPen(QColor("#c0f0c0"), 2)
            glow_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(glow_pen)
            painter.drawLine(sx, handle_h + 2, sx, h - 4)
            painter.drawLine(ex, handle_h + 2, ex, h - 4)

            painter.setBrush(QColor("#c0f0c0"))
            painter.setPen(QPen(QColor("#1a3a1a"), 2))
            painter.drawRect(sx - handle_w//2, 0, handle_w, handle_h)
            painter.drawRect(ex - handle_w//2, 0, handle_w, handle_h)

            painter.setPen(QPen(QColor("#1a3a1a"), 1))
            font = painter.font()
            font.setPointSize(8)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(sx - handle_w//2, 0, handle_w, handle_h, Qt.AlignmentFlag.AlignCenter, "S")
            painter.drawText(ex - handle_w//2, 0, handle_w, handle_h, Qt.AlignmentFlag.AlignCenter, "E")

            painter.setBrush(QColor("#c0f0c0"))
            painter.setPen(Qt.PenStyle.NoPen)
            path_s = QPainterPath()
            path_s.moveTo(sx - 4, handle_h)
            path_s.lineTo(sx + 4, handle_h)
            path_s.lineTo(sx, handle_h + 6)
            path_s.closeSubpath()
            painter.drawPath(path_s)
            path_e = QPainterPath()
            path_e.moveTo(ex - 4, handle_h)
            path_e.lineTo(ex + 4, handle_h)
            path_e.lineTo(ex, handle_h + 6)
            path_e.closeSubpath()
            painter.drawPath(path_e)

    def mousePressEvent(self, event):
        if self.duration == 0:
            return
        w = self.width()
        x = event.pos().x()
        y = event.pos().y()
        start_x = int((self.trim_start / self.duration) * w)
        end_x = int((self.trim_end / self.duration) * w)

        handle_w = 16
        pad = 4
        sx = max(pad + handle_w//2, min(start_x, w - pad - handle_w//2))
        ex = max(pad + handle_w//2, min(end_x, w - pad - handle_w//2))

        if abs(x - sx) < 14 and y < 28:
            self.dragging = 'start'
        elif abs(x - ex) < 14 and y < 28:
            self.dragging = 'end'
        elif abs(x - end_x) < 12:
            self.dragging = 'end'

    def mouseMoveEvent(self, event):
        if self.dragging is None or self.duration == 0:
            return
        w = self.width()
        x = max(-10, min(event.pos().x(), w + 10))
        t = (x / w) * self.duration
        t = max(0, min(t, self.duration))

        if self.dragging == 'start':
            self.trim_start = min(t, self.trim_end - 0.05)
        elif self.dragging == 'end':
            self.trim_end = max(t, self.trim_start + 0.05)

        self.update()
        self.trim_changed.emit(self.trim_start, self.trim_end)

    def mouseReleaseEvent(self, event):
        self.dragging = None

class AudioPlayerThread(QThread):
    position_changed = pyqtSignal(float)
    finished_playing = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, filepath, speed=1.0, start_sec=0.0, end_sec=None):
        super().__init__()
        self.filepath = filepath
        self.speed = speed
        self.start_sec = start_sec
        self.end_sec = end_sec
        self.is_playing = False
        self.is_paused = False
        self.position = 0
        self.data = None
        self.samplerate = 44100
        self._lock = threading.Lock()

    def load(self):
        try:
            self.data, self.samplerate = sf.read(self.filepath, dtype='float32')
            if len(self.data.shape) == 1:
                self.data = self.data.reshape(-1, 1)

            self.position = int(self.start_sec * self.samplerate)
            self.position = max(0, min(self.position, len(self.data) - 1))

            return True
        except Exception as e:
            try:
                ffmpeg_dir = find_ffmpeg()
                if ffmpeg_dir:
                    ffmpeg_path = Path(ffmpeg_dir) / 'ffmpeg.exe'
                    temp_wav = tempfile.mktemp(suffix='.wav')
                    cmd = [
                        str(ffmpeg_path), '-y', '-i', self.filepath,
                        '-ar', '48000', '-ac', '1', temp_wav
                    ]
                    subprocess.run(cmd, capture_output=True, timeout=30, check=True, **get_subprocess_kwargs())
                    self.data, self.samplerate = sf.read(temp_wav, dtype='float32')
                    if len(self.data.shape) == 1:
                        self.data = self.data.reshape(-1, 1)
                    self.position = int(self.start_sec * self.samplerate)
                    self.position = max(0, min(self.position, len(self.data) - 1))
                    Path(temp_wav).unlink(missing_ok=True)
                    return True
            except:
                pass
            self.error.emit(tr("error_load", str(e)))
            return False

    def run(self):
        if not self.load():
            return

        self.is_playing = True
        self.is_paused = False

        try:
            channels = self.data.shape[1]
            end_sample = int(self.end_sec * self.samplerate) if self.end_sec else len(self.data)

            def callback(outdata, frames, time_info, status):
                with self._lock:
                    if self.is_paused:
                        outdata[:] = 0
                        return

                    if self.speed == 1.0:
                        indices = np.arange(self.position, self.position + frames)
                    else:
                        indices = np.linspace(self.position, self.position + frames * self.speed, frames, endpoint=False)

                    indices = indices.astype(np.int32)
                    valid = (indices >= 0) & (indices < len(self.data)) & (indices < end_sample)

                    outdata[:] = 0
                    if np.any(valid):
                        valid_indices = indices[valid]
                        outdata[:len(valid_indices)] = self.data[valid_indices]

                    self.position = int(indices[-1]) + 1 if len(indices) > 0 else self.position

                    if self.position >= end_sample or self.position >= len(self.data):
                        self.is_playing = False
                        raise sd.CallbackStop()

                    pos_sec = self.position / self.samplerate
                    self.position_changed.emit(pos_sec)

            with sd.OutputStream(
                samplerate=self.samplerate,
                channels=channels,
                dtype='float32',
                callback=callback,
                blocksize=1024
            ):
                while self.is_playing and not self.isInterruptionRequested():
                    time.sleep(0.1)

            self.finished_playing.emit()

        except Exception as e:
            self.error.emit(str(e))

    def pause(self):
        with self._lock:
            self.is_paused = not self.is_paused
        return self.is_paused

    def stop(self):
        self.is_playing = False
        self.is_paused = False

    def seek(self, seconds):
        with self._lock:
            self.position = int(seconds * self.samplerate)
            self.position = max(0, min(self.position, len(self.data) - 1))

    def set_speed(self, speed):
        with self._lock:
            self.speed = max(0.25, min(2.0, speed))

class SimplePlayer(QWidget):
    def __init__(self, on_loaded=None, parent=None):
        super().__init__(parent)
        self.filepath = None
        self.duration = 0
        self.on_loaded = on_loaded
        self.play_thread = None
        self.source_dir = None
        self.audio_files = []
        self.current_index = -1

        self.setup_ui()
        self.setAcceptDrops(True)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        self.drop_frame = QFrame()
        self.drop_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        self.drop_frame.setStyleSheet("""
            QFrame {
                border: 2px dashed #3a7a3a;
                border-radius: 12px;
                background-color: #0d1f0d;
                min-height: 100px;
            }
            QFrame:hover {
                border-color: #6aba6a;
                background-color: #1a3a1a;
            }
        """)
        drop_layout = QVBoxLayout(self.drop_frame)
        drop_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop_layout.setSpacing(10)

        self.drop_label = QLabel(tr("drop_folder"))
        self.drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drop_label.setStyleSheet("color: #6aba6a; font-size: 14px;")
        drop_layout.addWidget(self.drop_label)

        self.open_btn = QPushButton(tr("open_folder"))
        self.open_btn.setFixedWidth(160)
        self.open_btn.setStyleSheet("""
            QPushButton {
                background-color: #3a7a3a;
                color: #c0f0c0;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #4a9a4a; }
        """)
        self.open_btn.clicked.connect(self.open_folder)
        drop_layout.addWidget(self.open_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self.drop_frame)

        self.info_widget = QWidget()
        info_layout = QVBoxLayout(self.info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(8)

        file_row = QHBoxLayout()

        self.play_btn = PlayPauseButton()
        self.play_btn.clicked.connect(self.toggle_play)
        file_row.addWidget(self.play_btn)

        self.name_label = QLabel(tr("no_file"))
        self.name_label.setStyleSheet("color: #8ada8a; font-size: 14px; font-weight: bold;")
        self.name_label.setWordWrap(True)
        file_row.addWidget(self.name_label, 1)

        info_layout.addLayout(file_row)

        time_row = QHBoxLayout()
        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setStyleSheet("color: #6aba6a; font-size: 12px;")
        time_row.addWidget(self.time_label)

        time_row.addStretch()

        self.format_label = QLabel("")
        self.format_label.setStyleSheet("color: #4a9a4a; font-size: 11px;")
        time_row.addWidget(self.format_label)

        info_layout.addLayout(time_row)

        file_select_row = QHBoxLayout()
        file_select_row.setSpacing(8)

        self.file_dropdown_btn = QPushButton(tr("select_file"))
        self.file_dropdown_btn.setStyleSheet("""
            QPushButton {
                background-color: #1a3a1a;
                color: #c0f0c0;
                border: 1px solid #3a7a3a;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
                min-width: 200px;
                max-width: 300px;
                text-align: left;
            }
            QPushButton:hover { background-color: #2a5a2a; }
            QPushButton:disabled {
                color: #3a7a3a;
                background-color: #0f2a0f;
            }
        """)
        self.file_dropdown_btn.clicked.connect(self.show_file_menu)
        file_select_row.addWidget(self.file_dropdown_btn)

        self.nav_label = QLabel("")
        self.nav_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.nav_label.setStyleSheet("color: #6aba6a; font-size: 12px; min-width: 60px;")
        file_select_row.addWidget(self.nav_label)

        # Кнопки навигации
        nav_btn_row = QHBoxLayout()
        nav_btn_row.setSpacing(8)

        self.prev_btn = QPushButton(tr("prev"))
        self.prev_btn.setFixedHeight(32)
        self.prev_btn.setMinimumWidth(100)
        self.prev_btn.setStyleSheet("""
            QPushButton {
                background-color: #1a3a1a;
                color: #c0f0c0;
                border: 1px solid #3a7a3a;
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
                padding: 4px 12px;
            }
            QPushButton:hover { background-color: #2a5a2a; }
            QPushButton:disabled {
                color: #3a7a3a;
                background-color: #0f2a0f;
            }
        """)
        self.prev_btn.clicked.connect(self.prev_file)
        nav_btn_row.addWidget(self.prev_btn)

        self.next_btn = QPushButton(tr("next"))
        self.next_btn.setFixedHeight(32)
        self.next_btn.setMinimumWidth(100)
        self.next_btn.setStyleSheet("""
            QPushButton {
                background-color: #1a3a1a;
                color: #c0f0c0;
                border: 1px solid #3a7a3a;
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
                padding: 4px 12px;
            }
            QPushButton:hover { background-color: #2a5a2a; }
            QPushButton:disabled {
                color: #3a7a3a;
                background-color: #0f2a0f;
            }
        """)
        self.next_btn.clicked.connect(self.next_file)
        nav_btn_row.addWidget(self.next_btn)

        file_select_row.addLayout(nav_btn_row)

        info_layout.addLayout(file_select_row)

        self.info_widget.hide()
        layout.addWidget(self.info_widget)

        self.setStyleSheet("background-color: #0f2a0f; border-radius: 10px; border: 1px solid #1a3a1a;")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if os.path.isdir(path):
                self.load_folder(path)
            elif self.is_audio(path):
                self.load_folder(os.path.dirname(path))

    def is_audio(self, path):
        ext = Path(path).suffix.lower()
        return ext in ('.mp3', '.wav', '.wv', '.ogg', '.flac', '.m4a', '.aac')

    def open_folder(self):
        dirpath = QFileDialog.getExistingDirectory(
            self, "Выберите папку audio (DDNet)", str(Path.home())
        )
        if dirpath:
            self.load_folder(dirpath)

    def load_folder(self, dirpath):
        self.source_dir = dirpath
        self.audio_files = []
        for ext in ('*.wv', '*.mp3', '*.wav', '*.ogg', '*.flac', '*.m4a', '*.aac'):
            self.audio_files.extend(sorted(Path(dirpath).glob(ext)))

        if not self.audio_files:
            QMessageBox.warning(self, "Пусто", tr("empty_folder"))
            return

        self.current_index = 0
        self.drop_frame.hide()
        self.info_widget.show()
        self.load_current()

    def load_current(self):
        if 0 <= self.current_index < len(self.audio_files):
            self.load_file(str(self.audio_files[self.current_index]))

    def load_file(self, filepath):
        self.stop_playback()
        self.filepath = filepath
        self.name_label.setText(Path(filepath).name)

        self.duration = self.get_duration(filepath)
        self.update_time_label()

        ext = Path(filepath).suffix.upper()
        self.format_label.setText(ext)

        self.update_navigation()

        if self.on_loaded:
            self.on_loaded(self)

    def get_duration(self, filepath):
        try:
            ffprobe = 'ffprobe'
            cfg = load_config()
            ffmpeg_dir = cfg.get('ffmpeg_dir', '')
            if ffmpeg_dir:
                ffprobe_path = Path(ffmpeg_dir) / 'ffprobe.exe'
                if ffprobe_path.exists():
                    ffprobe = str(ffprobe_path)

            cmd = [
                ffprobe, '-v', 'error', '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1', filepath
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10, **get_subprocess_kwargs())
            return float(result.stdout.strip())
        except:
            return 0

    def update_time_label(self):
        mins = int(self.duration // 60)
        secs = int(self.duration % 60)
        self.time_label.setText(f"00:00.000 / {mins:02d}:{secs:02d}.000")

    def update_navigation(self):
        if not self.audio_files:
            self.file_dropdown_btn.setText(tr("select_file"))
            self.file_dropdown_btn.setEnabled(False)
            self.nav_label.setText("")
            self.prev_btn.setEnabled(False)
            self.next_btn.setEnabled(False)
            return

        total = len(self.audio_files)
        current = self.current_index + 1
        self.nav_label.setText(f"{current} / {total}")

        current_name = self.audio_files[self.current_index].name
        if len(current_name) > 30:
            current_name = current_name[:27] + "..."
        self.file_dropdown_btn.setText(f"{current_name}")
        self.file_dropdown_btn.setEnabled(True)

        self.prev_btn.setEnabled(self.current_index > 0)
        self.next_btn.setEnabled(self.current_index < len(self.audio_files) - 1)

    def show_file_menu(self):
        if not self.audio_files:
            return
        self._build_dropdown()

    def _build_dropdown(self):
        # Close existing dropdown if any
        if hasattr(self, '_dropdown') and self._dropdown:
            self._dropdown.close()
            self._dropdown = None

        self._dropdown = QWidget(self.window())
        self._dropdown.setWindowFlags(Qt.WindowType.Popup)
        self._dropdown.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Main container with border and background
        container = QWidget(self._dropdown)
        container.setStyleSheet("""
            QWidget {
                background-color: #1a3a1a;
                border: 1px solid #3a7a3a;
                border-radius: 8px;
            }
        """)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Scroll area for the list
        from PyQt6.QtWidgets import QScrollArea, QScrollBar
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setMaximumHeight(320)
        scroll.setMinimumWidth(280)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                background: #0f2a0f;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #3a7a3a;
                border-radius: 4px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: #4a9a4a;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        list_widget = QWidget()
        list_layout = QVBoxLayout(list_widget)
        list_layout.setContentsMargins(4, 4, 4, 4)
        list_layout.setSpacing(2)

        for i, f in enumerate(self.audio_files):
            name = f.name
            if len(name) > 40:
                name = name[:37] + "..."

            item_btn = QPushButton(name)
            item_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #c0f0c0;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 12px;
                    text-align: left;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #3a7a3a;
                }
            """)
            if i == self.current_index:
                item_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #3a7a3a;
                        color: #ffffff;
                        border: none;
                        border-radius: 6px;
                        padding: 8px 12px;
                        text-align: left;
                        font-size: 12px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: #4a9a4a;
                    }
                """)

            item_btn.clicked.connect(lambda checked, idx=i: self._on_dropdown_selected(idx))
            list_layout.addWidget(item_btn)

        list_layout.addStretch()
        scroll.setWidget(list_widget)
        layout.addWidget(scroll)

        # Position dropdown below the button
        btn = self.file_dropdown_btn
        btn_pos = btn.mapToGlobal(btn.rect().bottomLeft())
        # Adjust for window offset
        win_pos = self.window().mapFromGlobal(btn_pos)

        container.setGeometry(0, 0, 300, min(320, len(self.audio_files) * 36 + 16))
        self._dropdown.setGeometry(
            self.window().mapToGlobal(win_pos).x(),
            self.window().mapToGlobal(win_pos).y() + 4,
            300,
            min(320, len(self.audio_files) * 36 + 16)
        )

        # Use a simpler layout for the popup
        drop_layout = QVBoxLayout(self._dropdown)
        drop_layout.setContentsMargins(0, 0, 0, 0)
        drop_layout.addWidget(container)

        self._dropdown.show()

    def _on_dropdown_selected(self, index):
        if hasattr(self, '_dropdown') and self._dropdown:
            self._dropdown.close()
            self._dropdown = None
        if 0 <= index < len(self.audio_files):
            self.current_index = index
            self.load_current()

    def on_menu_selected(self, index):
        if 0 <= index < len(self.audio_files):
            self.current_index = index
            self.load_current()

    def prev_file(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.load_current()

    def next_file(self):
        if self.current_index < len(self.audio_files) - 1:
            self.current_index += 1
            self.load_current()

    def toggle_play(self):
        if not self.filepath:
            return

        if self.play_thread and self.play_thread.isRunning():
            paused = self.play_thread.pause()
            self.play_btn.set_playing(not paused)
        else:
            self.play_thread = AudioPlayerThread(self.filepath)
            self.play_thread.position_changed.connect(self.on_position_changed)
            self.play_thread.finished_playing.connect(self.on_playback_finished)
            self.play_thread.start()
            self.play_btn.set_playing(True)

    def on_position_changed(self, pos):
        mins = int(pos // 60)
        secs = int(pos % 60)
        ms = int((pos % 1) * 1000)
        dur_mins = int(self.duration // 60)
        dur_secs = int(self.duration % 60)
        self.time_label.setText(f"{mins:02d}:{secs:02d}.{ms:03d} / {dur_mins:02d}:{dur_secs:02d}.000")

    def on_playback_finished(self):
        self.play_btn.set_playing(False)
        self.play_thread = None
        self.update_time_label()

    def stop_playback(self):
        if self.play_thread and self.play_thread.isRunning():
            self.play_thread.stop()
            self.play_thread.wait(1000)
        self.play_thread = None
        self.play_btn.set_playing(False)
        self.update_time_label()



class EditorPlayer(QWidget):
    def __init__(self, on_loaded=None, parent=None):
        super().__init__(parent)
        self.filepath = None
        self.duration = 0
        self.on_loaded = on_loaded
        self.play_thread = None
        self.is_paused = False
        self.trim_start = 0.0
        self.trim_end = 0.0

        self.setup_ui()
        self.setAcceptDrops(True)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        self.drop_frame = QFrame()
        self.drop_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        self.drop_frame.setStyleSheet("""
            QFrame {
                border: 2px dashed #3a7a3a;
                border-radius: 12px;
                background-color: #0d1f0d;
                min-height: 100px;
            }
            QFrame:hover {
                border-color: #6aba6a;
                background-color: #1a3a1a;
            }
        """)
        drop_layout = QVBoxLayout(self.drop_frame)
        drop_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop_layout.setSpacing(10)

        self.drop_label = QLabel(tr("drop_file"))
        self.drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drop_label.setStyleSheet("color: #6aba6a; font-size: 14px;")
        drop_layout.addWidget(self.drop_label)

        self.open_btn = QPushButton(tr("choose_file"))
        self.open_btn.setFixedWidth(160)
        self.open_btn.setStyleSheet("""
            QPushButton {
                background-color: #3a7a3a;
                color: #c0f0c0;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #4a9a4a; }
        """)
        self.open_btn.clicked.connect(self.choose_file)
        drop_layout.addWidget(self.open_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self.drop_frame)

        self.info_widget = QWidget()
        info_layout = QVBoxLayout(self.info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(10)

        file_row = QHBoxLayout()

        self.play_btn = PlayPauseButton()
        self.play_btn.clicked.connect(self.toggle_play)
        file_row.addWidget(self.play_btn)

        self.name_label = QLabel(tr("no_file"))
        self.name_label.setStyleSheet("color: #8ada8a; font-size: 14px; font-weight: bold;")
        self.name_label.setWordWrap(True)
        file_row.addWidget(self.name_label, 1)



        info_layout.addLayout(file_row)

        self.waveform = WaveformWidget()
        self.waveform.trim_changed.connect(self.on_trim_changed)
        info_layout.addWidget(self.waveform)

        info_layout.addSpacing(10)

        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setRange(0, 1000)
        self.progress_slider.setValue(0)
        self.progress_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 5px;
                background: #1a3a1a;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                width: 14px;
                height: 14px;
                background: #c0f0c0;
                border-radius: 7px;
                margin: -4px 0;
            }
            QSlider::sub-page:horizontal {
                background: #4a9a4a;
                border-radius: 2px;
            }
        """)
        self.progress_slider.sliderPressed.connect(self.on_slider_pressed)
        self.progress_slider.sliderReleased.connect(self.on_slider_released)
        info_layout.addWidget(self.progress_slider)

        time_row = QHBoxLayout()
        self.current_time = QLabel("00:00.000")
        self.current_time.setStyleSheet("color: #6aba6a; font-size: 12px;")
        time_row.addWidget(self.current_time)

        time_row.addStretch()

        self.trim_info = QLabel(tr("trim_full"))
        self.trim_info.setStyleSheet("color: #9ccc65; font-size: 11px;")
        time_row.addWidget(self.trim_info)

        time_row.addStretch()

        self.duration_label = QLabel("00:00")
        self.duration_label.setStyleSheet("color: #6aba6a; font-size: 12px;")
        time_row.addWidget(self.duration_label)

        info_layout.addLayout(time_row)

        self.info_widget.hide()
        layout.addWidget(self.info_widget)

        self.setStyleSheet("background-color: #0f2a0f; border-radius: 10px; border: 1px solid #1a3a1a;")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            filepath = urls[0].toLocalFile()
            if self.is_audio(filepath):
                self.load_file(filepath)

    def is_audio(self, path):
        ext = Path(path).suffix.lower()
        return ext in ('.mp3', '.wav', '.wv', '.ogg', '.flac', '.m4a', '.aac')

    def choose_file(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Выбрать аудио", "",
            "Audio Files (*.mp3 *.wav *.wv *.ogg *.flac *.m4a *.aac);;All Files (*)"
        )
        if filepath:
            self.load_file(filepath)

    def load_file(self, filepath):
        self.stop_playback()
        self.filepath = filepath
        self.name_label.setText(Path(filepath).name)

        self.duration = self.get_duration(filepath)
        self.update_time_labels()

        self.drop_frame.hide()
        self.info_widget.show()
        self.progress_slider.setValue(0)

        self.waveform.set_audio(filepath)
        self.trim_start = 0.0
        self.trim_end = self.duration
        self.on_trim_changed(0.0, self.duration)

        if self.on_loaded:
            self.on_loaded(self)

    def get_duration(self, filepath):
        try:
            ffprobe = 'ffprobe'
            cfg = load_config()
            ffmpeg_dir = cfg.get('ffmpeg_dir', '')
            if ffmpeg_dir:
                ffprobe_path = Path(ffmpeg_dir) / 'ffprobe.exe'
                if ffprobe_path.exists():
                    ffprobe = str(ffprobe_path)

            cmd = [
                ffprobe, '-v', 'error', '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1', filepath
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10, **get_subprocess_kwargs())
            return float(result.stdout.strip())
        except:
            return 0

    def update_time_labels(self):
        mins = int(self.duration // 60)
        secs = int(self.duration % 60)
        self.duration_label.setText(f"{mins:02d}:{secs:02d}")

    def format_time(self, seconds):
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        ms = int((seconds % 1) * 1000)
        return f"{mins:02d}:{secs:02d}.{ms:03d}"

    def on_trim_changed(self, start, end):
        self.trim_start = start
        self.trim_end = end
        self.trim_info.setText(
            tr("trim_info", self.format_time(start), self.format_time(end), self.format_time(end-start)))

    def toggle_play(self):
        if not self.filepath:
            return

        if self.play_thread and self.play_thread.isRunning():
            self.is_paused = self.play_thread.pause()
            self.play_btn.set_playing(not self.is_paused)
        else:
            self.start_playback()

    def start_playback(self):
        if not self.filepath:
            return

        self.play_thread = AudioPlayerThread(
            self.filepath, 1.0, 
            start_sec=self.trim_start, 
            end_sec=self.trim_end
        )
        self.play_thread.position_changed.connect(self.on_position_changed)
        self.play_thread.finished_playing.connect(self.on_playback_finished)
        self.play_thread.error.connect(self.on_playback_error)

        self.play_thread.start()
        self.is_paused = False
        self.play_btn.set_playing(True)

    def stop_playback(self):
        if self.play_thread and self.play_thread.isRunning():
            self.play_thread.stop()
            self.play_thread.wait(1000)
        self.play_thread = None
        self.is_paused = False
        self.play_btn.set_playing(False)
        self.progress_slider.setValue(0)
        self.current_time.setText(self.format_time(self.trim_start))

    def on_position_changed(self, pos):
        if self.duration > 0:
            value = int((pos / self.duration) * 1000)
            self.progress_slider.setValue(value)
        self.current_time.setText(self.format_time(pos))

    def on_playback_finished(self):
        self.play_btn.set_playing(False)
        self.play_thread = None

        self.progress_slider.setValue(0)
        self.current_time.setText(self.format_time(self.trim_start))

    def on_playback_error(self, msg):
        print(f"Playback error: {msg}")
        self.stop_playback()

    def on_slider_pressed(self):
        self._slider_dragging = True

    def on_slider_released(self):
        self._slider_dragging = False
        if self.play_thread and self.duration > 0:
            pos = (self.progress_slider.value() / 1000.0) * self.duration
            pos = max(self.trim_start, min(pos, self.trim_end))
            self.play_thread.seek(pos)



    def clear(self):
        self.stop_playback()
        self.filepath = None
        self.name_label.setText(tr("no_file"))
        self.duration_label.setText("00:00")
        self.current_time.setText("00:00")
        self.progress_slider.setValue(0)
        self.waveform.data = None
        self.waveform.update()
        self.trim_info.setText(tr("trim_full"))
        self.drop_frame.show()
        self.info_widget.hide()



class TargetCard(QWidget):
    def __init__(self, filepath, parent=None):
        super().__init__(parent)
        self.filepath = filepath
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 14, 20, 14)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        name = Path(self.filepath).name

        title = QLabel(f"{name}")
        title.setStyleSheet("color: #9ccc65; font-weight: bold; font-size: 13px;")
        title.setWordWrap(True)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        parent_path = str(Path(self.filepath).parent)
        info = QLabel(f"Будет заменён в:\n{parent_path}")
        info.setStyleSheet("color: #8ada8a; font-size: 10px;")
        info.setWordWrap(True)
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        info.setMinimumHeight(40)
        layout.addWidget(info)

        self.setStyleSheet("""
            background-color: #1a3a1a;
            border: 1px solid #9ccc65;
            border-radius: 8px;
        """)
        self.setMinimumWidth(520)
        self.setMinimumHeight(100)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(tr("app_title"))
        self.setMinimumSize(600, 700)

        self.source_file = None
        self.ffmpeg_dir = find_ffmpeg()
        self.download_thread = None

        self.setup_ui()
        self.apply_dark_theme()

        if self.ffmpeg_dir:
            self.ffmpeg_status.setText(tr("ffmpeg_found", self.ffmpeg_dir))
            self.ffmpeg_status.setStyleSheet("color: #66bb6a; font-size: 11px;")
        else:
            self.ffmpeg_status.setText(tr("ffmpeg_not_found"))
            self.ffmpeg_status.setStyleSheet("color: #e53935; font-size: 11px;")
            self.show_ffmpeg_installer()

        self.setup_shortcuts()

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        title = QLabel("DDNet Sound Replacer")
        title.setStyleSheet("color: #c0f0c0; font-size: 22px; font-weight: bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        self.ffmpeg_status = QLabel("Проверка FFmpeg...")
        self.ffmpeg_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.ffmpeg_status)

        self.ffmpeg_installer = QWidget()
        installer_layout = QVBoxLayout(self.ffmpeg_installer)
        installer_layout.setContentsMargins(0, 0, 0, 0)
        installer_layout.setSpacing(8)
        installer_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        info = QLabel("FFmpeg нужен для конвертации .mp3 → .wv\nБудет установлен в C:\ffmpeg\bin (~100MB)")
        info.setStyleSheet("color: #6aba6a; font-size: 12px;")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info.setWordWrap(True)
        installer_layout.addWidget(info)

        btn_row = QHBoxLayout()
        btn_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.download_btn = QPushButton(tr("ffmpeg_download"))
        self.download_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a9a4a;
                color: #ffffff;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #6aba6a; }
            QPushButton:disabled {
                background-color: #1a3a1a;
                color: #3a7a3a;
            }
        """)
        self.download_btn.clicked.connect(self.start_download)
        btn_row.addWidget(self.download_btn)

        self.browse_btn = QPushButton(tr("ffmpeg_browse"))
        self.browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #1a3a1a;
                color: #8ada8a;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #2a5a2a; }
        """)
        self.browse_btn.clicked.connect(self.browse_ffmpeg)
        btn_row.addWidget(self.browse_btn)

        installer_layout.addLayout(btn_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setMaximumWidth(400)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #1a3a1a;
                border-radius: 4px;
                background-color: #0d1f0d;
                color: #c0f0c0;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4a9a4a;
                border-radius: 4px;
            }
        """)
        self.progress_bar.hide()
        installer_layout.addWidget(self.progress_bar, alignment=Qt.AlignmentFlag.AlignCenter)

        self.log_label = QLabel("")
        self.log_label.setStyleSheet("color: #6aba6a; font-size: 11px;")
        self.log_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        installer_layout.addWidget(self.log_label)

        self.ffmpeg_installer.hide()
        layout.addWidget(self.ffmpeg_installer)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #1a3a1a;")
        layout.addWidget(line)

        source_label = QLabel(tr("source_title"))
        source_label.setStyleSheet("color: #c0f0c0; font-size: 14px; font-weight: bold;")
        layout.addWidget(source_label)

        self.source_player = SimplePlayer(on_loaded=self.on_source_loaded)
        layout.addWidget(self.source_player)

        replace_label = QLabel(tr("new_title"))
        replace_label.setStyleSheet("color: #c0f0c0; font-size: 14px; font-weight: bold;")
        layout.addWidget(replace_label)

        self.new_player = EditorPlayer(on_loaded=self.on_new_loaded)
        self.new_player.setEnabled(False)
        layout.addWidget(self.new_player)

        self.target_card = None

        layout.addSpacing(10)

        btn_container = QWidget()
        btn_layout = QHBoxLayout(btn_container)
        btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn_layout.setContentsMargins(0, 0, 0, 0)

        self.replace_btn = QPushButton(tr("replace"))
        self.replace_btn.setMinimumHeight(55)
        self.replace_btn.setMinimumWidth(280)
        self.replace_btn.setStyleSheet("""
            QPushButton {
                background-color: #4caf50;
                color: #1a3a1a;
                font-size: 16px;
                font-weight: bold;
                border-radius: 12px;
                padding: 12px 24px;
            }
            QPushButton:hover { background-color: #9ccc65; }
            QPushButton:pressed { background-color: #388e3c; }
            QPushButton:disabled {
                background-color: #1a3a1a;
                color: #3a7a3a;
            }
        """)
        self.replace_btn.clicked.connect(self.do_replace)
        self.replace_btn.setEnabled(False)
        btn_layout.addWidget(self.replace_btn)

        layout.addWidget(btn_container)

        self.success_label = QLabel(tr("success"), self.centralWidget())
        self.success_label.setStyleSheet("""
            QLabel {
                color: #66bb6a;
                font-size: 13px;
                font-weight: bold;
                background-color: #0a1f0a;
                padding: 4px 10px;
                border-radius: 6px;
                border: 1px solid #66bb6a;
            }
        """)
        self.success_label.adjustSize()
        self.success_label.hide()

        self._success_timer = QTimer(self)
        self._success_timer.setSingleShot(True)
        self._success_timer.timeout.connect(self._hide_success)

        # Subtitle under replace button
        self.subtitle_label = QLabel("by World is cruel")
        self.subtitle_label.setStyleSheet("color: #3a7a3a; font-size: 10px; background: transparent;")
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.subtitle_label, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addStretch()

    def apply_dark_theme(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0a1f0a;
            }
            QWidget {
                background-color: #0a1f0a;
                color: #c0f0c0;
                font-family: 'Segoe UI', sans-serif;
            }
            QLabel {
                color: #c0f0c0;
            }
        """)

    def setup_shortcuts(self):
        from PyQt6.QtGui import QShortcut, QKeySequence  # type: ignore
        from PyQt6.QtCore import QObject  # type: ignore

        # Install event filter on the application to catch arrow keys before focus navigation
        QApplication.instance().installEventFilter(self)

        # Space - play/pause (QShortcut works fine for space)
        self.shortcut_play = QShortcut(QKeySequence("Space"), self)
        self.shortcut_play.setContext(Qt.ShortcutContext.ApplicationShortcut)
        self.shortcut_play.activated.connect(self.on_play_shortcut)

    def eventFilter(self, obj, event):
        if event.type() == event.Type.KeyPress:
            key = event.key()
            # Left arrow or A - previous file
            if key == Qt.Key.Key_Left or key == Qt.Key.Key_A:
                if self.source_player and self.source_player.isVisible():
                    self.source_player.prev_file()
                return True
            # Right arrow or D - next file
            elif key == Qt.Key.Key_Right or key == Qt.Key.Key_D:
                if self.source_player and self.source_player.isVisible():
                    self.source_player.next_file()
                return True
        return super().eventFilter(obj, event)

    def on_play_shortcut(self):
        if self.new_player and self.new_player.filepath:
            self.new_player.toggle_play()
        elif self.source_player and self.source_player.filepath:
            self.source_player.toggle_play()

    def _show_success(self):
        self.success_label.adjustSize()
        btn_pos = self.replace_btn.mapTo(self.centralWidget(), self.replace_btn.rect().topRight())
        x = btn_pos.x() + 10
        y = btn_pos.y() + (self.replace_btn.height() - self.success_label.height()) // 2
        self.success_label.move(x, y)
        self.success_label.show()
        self._success_timer.start(2000)

    def _hide_success(self):
        self.success_label.hide()

    def show_ffmpeg_installer(self):
        self.ffmpeg_installer.show()

    def browse_ffmpeg(self):
        dirpath = QFileDialog.getExistingDirectory(
            self, "Выберите папку с ffmpeg.exe", str(Path.home())
        )
        if dirpath:
            p = Path(dirpath)
            if (p / 'ffmpeg.exe').exists():
                self.ffmpeg_dir = str(p)
                cfg = load_config()
                cfg['ffmpeg_dir'] = str(p)
                save_config(cfg)
                self.ffmpeg_status.setText(tr("ffmpeg_found", p))
                self.ffmpeg_status.setStyleSheet("color: #66bb6a; font-size: 11px;")
                self.ffmpeg_installer.hide()
            else:
                QMessageBox.warning(self, "Не найден", tr("ffmpeg_manual"))

    def start_download(self):
        self.download_btn.setEnabled(False)
        self.browse_btn.setEnabled(False)
        self.progress_bar.show()
        self.progress_bar.setValue(0)
        self.log_label.setText("Начинаю скачивание...")

        self.download_thread = FfmpegDownloader()
        self.download_thread.progress.connect(self.progress_bar.setValue)
        self.download_thread.status.connect(self.log_label.setText)
        self.download_thread.finished_download.connect(self.on_download_finished)
        self.download_thread.error.connect(self.on_download_error)

        self.download_thread.start()

    def on_download_finished(self, path):
        self.ffmpeg_dir = path
        cfg = load_config()
        cfg['ffmpeg_dir'] = path
        save_config(cfg)

        self.ffmpeg_status.setText(tr("ffmpeg_found", path))
        self.ffmpeg_status.setStyleSheet("color: #66bb6a; font-size: 11px;")
        self.ffmpeg_installer.hide()

        QMessageBox.information(self, tr("ffmpeg_done"), 
            f"FFmpeg успешно установлен!\n\nПуть: {path}")

    def on_download_error(self, error_msg):
        self.download_btn.setEnabled(True)
        self.browse_btn.setEnabled(True)
        self.progress_bar.hide()
        self.log_label.setText(f"Ошибка: {error_msg}")
        self.log_label.setStyleSheet("color: #e53935; font-size: 11px;")

        QMessageBox.critical(self, tr("error"),
            f"Не удалось скачать ffmpeg:\n{error_msg}\n\n"
            f"Попробуйте скачать вручную:\n"
            f"https://www.gyan.dev/ffmpeg/builds/\n\n"
            f"Или используйте батник install_ffmpeg.bat")

    def on_source_loaded(self, player):
        self.source_file = self.source_player.filepath
        self.new_player.setEnabled(True)
        self.show_target_card()
        self.check_replace_ready()

    def on_new_loaded(self, player):
        self.check_replace_ready()

    def show_target_card(self):
        if self.target_card:
            self.target_card.deleteLater()

        layout = self.centralWidget().layout()
        idx = layout.indexOf(self.replace_btn.parentWidget())

        self.target_card = TargetCard(self.source_file)
        layout.insertWidget(idx, self.target_card)

    def check_replace_ready(self):
        ready = bool(self.source_file and self.new_player.filepath)
        self.replace_btn.setEnabled(ready)

    def do_replace(self):
        if not self.source_file or not self.new_player.filepath:
            return

        source_name = Path(self.source_file).stem
        source_dir = Path(self.source_file).parent
        output_path = source_dir / f"{source_name}.wv"

        ffmpeg = 'ffmpeg'
        if self.ffmpeg_dir:
            ffmpeg_path = Path(self.ffmpeg_dir) / 'ffmpeg.exe'
            if ffmpeg_path.exists():
                ffmpeg = str(ffmpeg_path)

        trim_start = getattr(self.new_player, 'trim_start', 0)
        trim_end = getattr(self.new_player, 'trim_end', 0)
        duration = trim_end - trim_start if trim_end > trim_start else 0

        cmd = [ffmpeg, '-y']

        if trim_start > 0:
            cmd.extend(['-ss', str(trim_start)])
        if duration > 0:
            cmd.extend(['-t', str(duration)])

        cmd.extend(['-i', self.new_player.filepath])
        cmd.extend(['-ar', '48000', '-ac', '1', '-sample_fmt', 's16p'])
        cmd.append(str(output_path))

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True,
                check=True, timeout=60, **get_subprocess_kwargs()
            )

            self.source_player.load_file(str(output_path))
            self._show_success()

        except subprocess.CalledProcessError as e:
            QMessageBox.critical(
                self, tr("error"),
                tr("error_ffmpeg", e.stderr)
            )
        except FileNotFoundError:
            QMessageBox.critical(
                self, tr("error"),
                "FFmpeg не найден!\n"
                "Нажмите 'Скачать и установить' выше."
            )
        except Exception as e:
            QMessageBox.critical(
                self, tr("error"),
                tr("error_replace", str(e))
            )

def create_seedling_icon(size=64):
    """Draw a green seedling icon with transparent background."""
    from PyQt6.QtGui import QPixmap, QPainter, QColor, QPen, QBrush, QIcon  # type: ignore
    from PyQt6.QtCore import Qt, QPoint  # type: ignore

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    center_x = size // 2
    bottom_y = size - 8

    # Stem - curved line
    stem_path = QPainterPath()
    stem_path.moveTo(center_x, bottom_y)
    stem_path.cubicTo(center_x - 5, bottom_y - 15, center_x + 3, bottom_y - 30, center_x, bottom_y - 40)

    pen = QPen(QColor("#4caf50"))
    pen.setWidth(3)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(pen)
    painter.drawPath(stem_path)

    # Left leaf
    left_leaf = QPainterPath()
    left_leaf.moveTo(center_x, bottom_y - 35)
    left_leaf.cubicTo(center_x - 15, bottom_y - 45, center_x - 20, bottom_y - 55, center_x - 8, bottom_y - 50)
    left_leaf.cubicTo(center_x - 5, bottom_y - 48, center_x - 2, bottom_y - 42, center_x, bottom_y - 38)
    painter.fillPath(left_leaf, QBrush(QColor("#66bb6a")))
    painter.setPen(QPen(QColor("#4caf50"), 1))
    painter.drawPath(left_leaf)

    # Right leaf
    right_leaf = QPainterPath()
    right_leaf.moveTo(center_x, bottom_y - 32)
    right_leaf.cubicTo(center_x + 12, bottom_y - 42, center_x + 18, bottom_y - 52, center_x + 6, bottom_y - 48)
    right_leaf.cubicTo(center_x + 3, bottom_y - 46, center_x + 1, bottom_y - 40, center_x, bottom_y - 35)
    painter.fillPath(right_leaf, QBrush(QColor("#81c784")))
    painter.setPen(QPen(QColor("#4caf50"), 1))
    painter.drawPath(right_leaf)

    # Small center leaf
    center_leaf = QPainterPath()
    center_leaf.moveTo(center_x, bottom_y - 38)
    center_leaf.cubicTo(center_x - 3, bottom_y - 48, center_x + 3, bottom_y - 52, center_x, bottom_y - 45)
    painter.fillPath(center_leaf, QBrush(QColor("#a5d6a7")))
    painter.setPen(QPen(QColor("#4caf50"), 1))
    painter.drawPath(center_leaf)

    # Soil dots at bottom
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(QColor("#8d6e63")))
    painter.drawEllipse(center_x - 8, bottom_y - 3, 4, 3)
    painter.drawEllipse(center_x + 2, bottom_y - 2, 5, 3)
    painter.drawEllipse(center_x - 3, bottom_y - 1, 3, 2)

    painter.end()
    return QIcon(pixmap)

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    font = QFont("Segoe UI", 10)
    app.setFont(font)

    # Set application icon - drawn seedling
    icon = create_seedling_icon(64)
    app.setWindowIcon(icon)

    # Show language selector
    lang_dialog = LanguageSelector()
    if lang_dialog.exec() == QDialog.DialogCode.Accepted:
        global _current_lang
        _current_lang = lang_dialog.selected_lang
    else:
        sys.exit(0)

    window = MainWindow()
    window.setWindowIcon(icon)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
