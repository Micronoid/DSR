import os
import sys
import shutil
import subprocess
import soundfile as sf
from pathlib import Path
from utils.ffmpeg_core import find_ffmpeg 

def process_audio_replace(source_file_path: Path, new_file_path: str, trim_start: float, trim_end: float, speed: float, volume: float = 1.0) -> bool:
    """
    Выполняет нарезку, изменение скорости, громкости и конвертацию нового аудиофайла
    в формат .wv для замены оригинального файла DDNet.
    """
    if not source_file_path or not new_file_path:
        return False

    ffmpeg_dir = find_ffmpeg()

    if ffmpeg_dir:
        exe_name = 'ffmpeg.exe' if sys.platform == 'win32' else 'ffmpeg'
        ffmpeg_cmd = str(Path(ffmpeg_dir) / exe_name)
    else:
        ffmpeg_cmd = 'ffmpeg'

    output_path = source_file_path
    duration = trim_end - trim_start if trim_end > trim_start else 0

    cmd = [ffmpeg_cmd, '-y']

    if trim_start > 0:
        cmd.extend(['-ss', f"{trim_start:.3f}"])
    if duration > 0:
        cmd.extend(['-t', f"{duration:.3f}"])

    cmd.extend(['-i', new_file_path])

    afilters = []

    if speed != 1.0:
        try:
            input_sr = sf.info(new_file_path).samplerate
        except Exception:
            input_sr = 48000
        adjusted_rate = int(input_sr * speed)
        afilters.append(f'asetrate={adjusted_rate},aresample=48000')

    if volume != 1.0:
        afilters.append(f'volume={volume:.2f}')

    if afilters:
        cmd.extend(['-af', ','.join(afilters)])

    cmd.extend(['-ar', '48000', '-ac', '1', '-sample_fmt', 's16p'])
    cmd.append(str(output_path))

    try:
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            check=True, 
            timeout=60,
            startupinfo=startupinfo
        )
        print("[CONVERTER] FFmpeg успешно завершил работу.")

        try:
            if getattr(sys, 'frozen', False):
                app_dir = Path(sys.executable).parent
            else:
                app_dir = Path(__file__).parent.parent

            backup_dir = app_dir / 'new sounds'
            backup_dir.mkdir(parents=True, exist_ok=True)

            backup_path = backup_dir / source_file_path.name
            shutil.copy2(str(output_path), str(backup_path))
            print(f"[CONVERTER] Бэкап сохранен в: {backup_path}")
        except Exception as backup_error:
            print(f"[CONVERTER] Не удалось создать бэкап: {backup_error}")

        return True

    except subprocess.CalledProcessError as e:
        print(f"[CONVERTER] Ошибка FFmpeg: {e.stderr}")
        raise e
    except FileNotFoundError:
        print("[CONVERTER] FFmpeg не найден в системе (FileNotFoundError)!")
        raise FileNotFoundError
    except Exception as e:
        print(f"[CONVERTER] Критическая ошибка при замене: {e}")
        raise e