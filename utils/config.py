import os
import sys
import json
import shutil
from pathlib import Path

def get_config_path() -> Path:
    """Определяет путь к файлу настроек в AppData"""
    if sys.platform == 'win32':
        config_dir = Path(os.environ.get('APPDATA', Path.home())) / 'DDNetSoundReplacer'
    else:
        config_dir = Path.home() / '.config' / 'DDNetSoundReplacer'
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / 'config.json'

def get_assets_dir() -> Path:
    """Папка для загружаемых assets (translations, icon)"""
    return get_config_path().parent / 'assets'

def load_config() -> dict:
    """Загружает JSON конфигурацию"""
    path = get_config_path()
    if path.exists():
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except:
            pass
    return {}

def save_config(cfg: dict):
    """Сохраняет конфигурацию на диск (merge с существующим, не перезапись)"""
    path = get_config_path()
    existing = load_config()
    existing.update(cfg)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)