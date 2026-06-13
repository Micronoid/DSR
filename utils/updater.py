import os
import sys
import json
import urllib.request
from pathlib import Path
import asyncio
from utils.config import load_config, save_config, get_assets_dir
from utils.version import CURRENT_VERSION, REPO_OWNER, REPO_NAME


def _assets_url(filename: str) -> str:
    """Формирует raw-URL для файла из ветки main."""
    return f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/main/assets/{filename}"


def _download_sync(url: str, dest: Path):
    """Синхронное скачивание файла."""
    urllib.request.urlretrieve(url, str(dest))


def _parse_version(v: str) -> tuple[int, ...]:
    """Парсит semver-строку в кортеж чисел. Поддерживает 1.0, 1.1.1, 2.0.0.1 и т.д."""
    parts = v.split('.')
    return tuple(int(x) for x in parts)


def _compare_versions(current: str, latest: str) -> bool:
    """
    Сравнивает версии. Возвращает True если latest > current.
    Дополняет короткие версии нулями: 1.0 == 1.0.0
    """
    cur = _parse_version(current)
    lat = _parse_version(latest)
    max_len = max(len(cur), len(lat))
    cur = cur + (0,) * (max_len - len(cur))
    lat = lat + (0,) * (max_len - len(lat))
    print(f"[UPDATER] Сравнение: текущая {cur} vs latest {lat} -> {lat > cur}")
    return lat > cur


async def ensure_assets_async() -> bool:
    """
    Асинхронно проверяет и скачивает assets (translations.json, icon.ico).
    Возвращает True если всё на месте (или скачано, или использован кэш).
    Возвращает False только если файлов нет вообще нигде.
    """
    assets_dir = get_assets_dir()
    assets_dir.mkdir(parents=True, exist_ok=True)

    files = ['translations.json', 'icon.ico']
    missing = any(not (assets_dir / f).exists() for f in files)


    if not missing:
        cfg = load_config()
        saved_version = cfg.get('app_version', '0.0.0')
        if saved_version == CURRENT_VERSION:
            print("[UPDATER] Assets актуальны, пропускаем скачивание")
            return True
        print(f"[UPDATER] Assets есть, но версия устарела ({saved_version} != {CURRENT_VERSION}). Перекачиваем...")
    else:
        print(f"[UPDATER] Assets отсутствуют. Скачиваем с GitHub...")

    try:
        loop = asyncio.get_event_loop()
        for fname in files:
            url = _assets_url(fname)
            dest = assets_dir / fname
            print(f"[UPDATER] Скачивание: {url} -> {dest}")
            await loop.run_in_executor(None, _download_sync, url, dest)
            print(f"[UPDATER] OK: {fname}")

        cfg = load_config()
        cfg['app_version'] = CURRENT_VERSION
        save_config(cfg)
        print(f"[UPDATER] Assets обновлены до версии {CURRENT_VERSION}")
        return True
    except Exception as e:
        print(f"[UPDATER] Ошибка загрузки assets: {e}")
        if not missing:
            print("[UPDATER] Используем существующий кэш assets в AppData")
            cfg = load_config()
            cfg['app_version'] = CURRENT_VERSION
            save_config(cfg)
            return True
        return False


def check_for_update_sync() -> tuple[bool, str, str | None]:
    """
    Проверяет GitHub Releases API.
    Возвращает (has_update, latest_version, release_url).
    """
    print(f"[UPDATER] Проверка обновлений. Текущая версия: {CURRENT_VERSION}")
    print(f"[UPDATER] Запрос к API: repos/{REPO_OWNER}/{REPO_NAME}/releases/latest")
    try:
        url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/latest"
        req = urllib.request.Request(url, headers={'User-Agent': 'DSR-Updater'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            latest = data.get('tag_name', 'v0.0.0').lstrip('v')
            release_url = data.get(
                'html_url',
                f"https://github.com/{REPO_OWNER}/{REPO_NAME}/releases"
            )
            print(f"[UPDATER] Последний релиз на GitHub: v{latest}")

            has_update = _compare_versions(CURRENT_VERSION, latest)
            if has_update:
                print(f"[UPDATER] Доступна новая версия: {latest}")
            else:
                print(f"[UPDATER] Обновлений нет (текущая {CURRENT_VERSION} >= {latest})")
            return has_update, latest, release_url
    except Exception as e:
        print(f"[UPDATER] Не удалось проверить обновления: {e}")
    return False, CURRENT_VERSION, None