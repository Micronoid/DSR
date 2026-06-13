import flet as ft
import asyncio
from utils.ffmpeg_core import find_ffmpeg, ensure_ffmpeg
from utils.config import load_config, save_config
from utils.i18n import t

class FfmpegBadge(ft.Container):
    def __init__(self):
        super().__init__()
        print("[BADGE] Инициализация компонента FfmpegBadge...")

        self.use_progress_ring = True
        self.is_loading = False

        self.padding = ft.Padding.all(8)
        self.border_radius = 20
        self.visible = True 

        self.TEXT_COLOR_LOADING = ft.Colors.PINK_900  
        self.ICON_COLOR_LOADING = ft.Colors.PINK_800

        self.icon_container = ft.Container(
            content=ft.Icon(ft.Icons.EXTENSION_OFF_ROUNDED, color=ft.Colors.RED_300),
            width=24,
            height=24,
            alignment=ft.Alignment.CENTER
        )

        self.text = ft.Text(t("ffmpeg_badge.not_found"), color=ft.Colors.RED_300, size=13, weight=ft.FontWeight.BOLD)
        self.content = ft.Row([self.icon_container, self.text], spacing=8)

        self.bgcolor = ft.Colors.with_opacity(0.1, ft.Colors.RED_500)
        self.tooltip = t("ffmpeg_badge.install_tooltip")
        self.animate = ft.Animation(200, ft.AnimationCurve.EASE_OUT)

    def did_mount(self):
        print("[BADGE] Компонент смонтирован.")
        self.on_click = lambda e: self.page.run_task(self.start_setup)
        self.update()
        self.page.run_task(self.check_at_start)

    async def check_at_start(self):
        print("[BADGE] Выполняется тихая проверка FFmpeg при старте...")
        path = find_ffmpeg()
        if path:
            print(f"[BADGE] Тихо нашли FFmpeg: {path}. Красим в зелёный.")
            self._set_success_state(path)
            self.update()
        else:
            print("[BADGE] При старте FFmpeg не обнаружен. Ждем клика пользователя.")

    def update_download_ui(self, status_value: str, progress_value: float):
        if not self.is_loading:
            return

        raw_prog = progress_value if progress_value else 0.0
        visual_prog = min(raw_prog / 0.75, 1.0) if raw_prog > 0 else 0.0

        self._update_gradient_progress(visual_prog)

        if not self.use_progress_ring:
            try:
                if self.icon_container.content.rotate is not None:
                    self.icon_container.content.rotate += 0.1
                else:
                    self.icon_container.content.rotate = 0.1
            except Exception:
                pass

        if "Скачивание FFmpeg:" in status_value:
            mb_info = status_value.replace("Скачивание FFmpeg:", "").strip()
            self.text.value = f"ffmpeg ({mb_info.split('/')[0].strip()}MB)"
        elif status_value:
            self.text.value = status_value

        self.update()

    async def start_setup(self, e=None):
        if self.is_loading:
            return

        path = find_ffmpeg()
        if path:
            self._set_success_state(path)
            self.update()
            return

        print(f"[BADGE] Начинаем установку...")
        self.is_loading = True
        self.bgcolor = None 
        self.animate = None 

        self._update_gradient_progress(0.0)
        self.text.color = self.TEXT_COLOR_LOADING

        if self.use_progress_ring:
            self.icon_container.content = ft.ProgressRing(
                width=16, 
                height=16, 
                stroke_width=2, 
                color=self.ICON_COLOR_LOADING,
                value=None
            )
        else:
            self.icon_container.content = ft.Icon(
                ft.Icons.DOWNLOAD_ROUNDED,
                color=self.ICON_COLOR_LOADING,
                animate_rotation=ft.Animation(300, ft.AnimationCurve.EASE_OUT),
                rotate=0.0
            )

        self.tooltip = t("ffmpeg_badge.installing")
        self.update()

        dummy_status = ft.Text()
        dummy_progress = ft.ProgressBar()

        installed_path = await ensure_ffmpeg(
            status_text=dummy_status, 
            progress_bar=dummy_progress, 
            page=self.page,
            on_progress_callback=self.update_download_ui
        )

        self.is_loading = False
        self.animate = ft.Animation(200, ft.AnimationCurve.EASE_OUT)

        if installed_path:
            cfg = load_config()
            cfg['ffmpeg_dir'] = installed_path
            save_config(cfg)
            self._set_success_state(installed_path)
        else:
            self.gradient = None
            self.icon_container.content = ft.Icon(ft.Icons.EXTENSION_OFF_ROUNDED, color=ft.Colors.RED_300)
            self.text.value = t("ffmpeg_badge.error")
            self.text.color = ft.Colors.RED_300
            self.bgcolor = ft.Colors.with_opacity(0.1, ft.Colors.RED_500)
            self.tooltip = t("ffmpeg_badge.retry_tooltip")

        self.update()

    def _update_gradient_progress(self, progress: float):
        self.gradient = ft.LinearGradient(
            begin=ft.Alignment.CENTER_LEFT,
            end=ft.Alignment.CENTER_RIGHT,
            colors=[
                ft.Colors.with_opacity(0.35, ft.Colors.PINK_400), 
                ft.Colors.with_opacity(0.12, ft.Colors.PINK_300)  
            ],
            stops=[progress, progress] 
        )

    def _set_success_state(self, path):
        self.gradient = None 
        self.is_loading = False

        self.icon_container.content = ft.Icon(
            ft.Icons.CHECK_CIRCLE_ROUNDED, 
            color=ft.Colors.GREEN_800
        )

        self.text.value = "ffmpeg"
        self.text.color = ft.Colors.GREEN_900         
        self.bgcolor = ft.Colors.with_opacity(0.25, ft.Colors.GREEN_400)
        self.tooltip = t("ffmpeg_badge.installed_tooltip", path=path)
        self.on_click = None