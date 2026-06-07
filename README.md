# DDNet Sound Replacer 🎧🔨

[**Русский**](#русский) | [**English**](#english)

---

### 💫 Сейчас программа находится на стадии разработки и тестирования, но её уже можно использовать. Если что-то не работает, работает неправильно или у вас есть крутые идеи по улучшению — добро пожаловать в **[Issues](../../issues)**.

### 💫 Currently, the program is under development and testing, but it is already usable. If something doesn't work, works incorrectly, or you have cool ideas for improvement — welcome to **[Issues](../../issues)**.

---

## Русский

Удобная графическая утилита на **PyQt6** для быстрого прослушивания, обрезки, изменения скорости и замены звуковых файлов в игре **DDRaceNetwork (DDNet)**. 

Программа автоматически решает главную проблему кастомизации звуков в DDNet — конвертацию аудио-форматов из обычного `.mp3`/`.wav` в игровой формат `.wv` (WavPack) с помощью интеграции с FFmpeg.

### ✨ Особенности
* 📁 **Drag-and-drop:** Просто перетащите папку `audio` из игры прямо в окно программы.
* 📊 **Интерактивная звуковая волна (Waveform):** Визуальное отображение трека с возможностью точной обрезки начала и конца звука.
* ⚡ **Регулировка скорости:** Изменение темпа аудио от 0.25x до 2.0x в реальном времени.
* 📥 **Авто-установка FFmpeg:** Если в системе нет кодеков, утилита сама скачает и распакует нужную версию FFmpeg (~100MB) прямо в `C:\ffmpeg`.
* 🌍 **Мультиязычность:** Полная поддержка русского и английского интерфейсов.

### 🛠 Требования для разработки (Запуск из исходников)
Для работы скрипта требуются Python 3.9+ и следующие библиотеки:
```bash
pip install pyinstaller numpy sounddevice soundfile PyQt6

```

> **Примечание:** Библиотеки `sounddevice` и `soundfile` используются для воспроизведения звука и отрисовки спектрограммы прямо внутри интерфейса.

### 🚀 Сборка в `.exe`

Проект оптимизирован для сборки через **PyInstaller**. Чтобы собрать один чистый исполняемый файл без консоли, используйте команду:

```bash
pyinstaller --noconsole --onefile main.py

```

---

## English

A convenient **PyQt6** graphical utility for previewing, trimming, changing speed, and replacing audio files in **DDRaceNetwork (DDNet)**.

The program automatically handles the main hassle of DDNet audio customization — converting standard formats like `.mp3`/`.wav` into the game-required `.wv` (WavPack) format using FFmpeg integration.

### ✨ Features

* 📁 **Drag-and-drop:** Drag your game's `audio` folder right into the application window.
* 📊 **Interactive Waveform:** Visual representation of the audio with precise start/end markers for trimming.
* ⚡ **Speed Adjustment:** Change audio tempo from 0.25x to 2.0x in real-time.
* 📥 **Automated FFmpeg Setup:** If FFmpeg is missing, the tool automatically downloads and extracts it (~100MB) directly to `C:\ffmpeg`.
* 🌍 **Localization:** Full out-of-the-box support for both English and Russian languages.

### 🛠 Requirements (Running from Source)

To run the script from source, you need Python 3.9+ and the following dependencies:

```bash
pip install pyinstaller numpy sounddevice soundfile PyQt6

```

### 🚀 Building into `.exe`

The project is optimized for compilation via **PyInstaller**. Run the following command to bundle everything into a single, clean GUI executable:

```bash
pyinstaller --noconsole --onefile main.py

```

