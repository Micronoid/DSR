import io
import base64
import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw


def generate_waveform_image(filepath: str, width: int = 626, height: int = 42,
                            color: tuple = (129, 212, 250, 210)) -> str | None:
    """
    Генерирует PNG-волну аудиофайла и возвращает data URI (base64).
    По умолчанию цвет — Light Blue 200 с alpha (~0.82), в тон зоны замены.
    """
    try:
        data, sr = sf.read(filepath, dtype='float32')
        if data is None or len(data) == 0:
            return None

        if len(data.shape) > 1:
            data = np.mean(data, axis=1)

        samples_per_pixel = max(1, len(data) // width)
        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        mid = height // 2

        for x in range(width):
            start_idx = x * samples_per_pixel
            end_idx = min(start_idx + samples_per_pixel, len(data))
            if start_idx >= len(data):
                break

            chunk = data[start_idx:end_idx]
            max_val = float(np.max(np.abs(chunk))) if len(chunk) > 0 else 0.0
            h = int(max_val * (height / 2) * 0.92)
            if h < 1:
                continue

            draw.line([(x, mid - h), (x, mid + h)], fill=color, width=1)

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return f"data:image/png;base64,{b64}"

    except Exception as e:
        print(f"[WAVEFORM] Ошибка генерации волны: {e}")
        return None