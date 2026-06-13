from pathlib import Path
import sys
import flet as ft
from components.ui_ffmpeg_badge import FfmpegBadge
from components.ui_source_zone import SourceAudioZone
from components.ui_replace_zone import ReplaceAudioZone
from utils.converter_core import process_audio_replace
from utils.config import load_config, save_config
from utils import i18n
from utils.updater import ensure_assets_async, check_for_update_sync
from utils.version import CURRENT_VERSION

is_converting = False

def main(page: ft.Page):
    page.window.width = 900
    page.window.height = 550
    page.window.resizable = False
    page.window.maximizable = False
    page.title = "DSR 💫"
    page.window.title_bar_hidden = True
    page.window.title_bar_buttons_hidden = True
    page.window.frameless = True
    page.window.shadow = False
    page.window.bgcolor = ft.Colors.TRANSPARENT
    page.bgcolor = ft.Colors.TRANSPARENT
    page.theme_mode = ft.ThemeMode.LIGHT

    if sys.platform == 'win32':
        icon_path = Path(__file__).parent / "assets" / "icon.ico"
        if not icon_path.exists():
            from utils.config import get_assets_dir
            icon_path = get_assets_dir() / 'icon.ico'
        if icon_path.exists():
            page.window.icon = str(icon_path)

    page.padding = 0
    page.spacing = 0

    page.theme = ft.Theme(
        color_scheme_seed=ft.Colors.PINK,
        font_family="Nunito",
    )

    page.fonts = {
        "Nunito": "https://raw.githubusercontent.com/google/fonts/main/ofl/nunito/Nunito[wght].ttf",
    }

    url_launcher = ft.UrlLauncher()

    has_update = False
    release_url = None
    update_btn_ref = None

    async def open_update_url(e):
        if release_url:
            print(f"[APP] Открываем URL: {release_url}")
            await url_launcher.launch_url(release_url)

    async def check_updates():
        nonlocal has_update, release_url
        print(f"[APP] check_updates: CURRENT_VERSION={CURRENT_VERSION}")
        if CURRENT_VERSION == "dev":
            print("[APP] Dev-режим, проверка обновлений пропущена")
            return
        try:
            async def _check():
                loop = __import__('asyncio').get_event_loop()
                return await loop.run_in_executor(None, check_for_update_sync)

            has_update, _, release_url = await _check()
            print(f"[APP] Результат проверки: has_update={has_update}, url={release_url}")
            if has_update and update_btn_ref:
                print("[APP] Показываем кнопку обновления")
                update_btn_ref.visible = True
                update_btn_ref.update()
            else:
                print("[APP] Кнопка обновления остается скрытой")
        except Exception as e:
            print(f"[APP] Ошибка в check_updates: {e}")

    

    async def build_assets():
        """Скачивание assets, настройка языка, построение UI."""
        sys_lang = i18n.detect_system_lang()

        assets_ok = await ensure_assets_async()

        if not assets_ok:
            local_assets = Path(__file__).parent / "assets" / "translations.json"
            if local_assets.exists():
                print("[INIT] Используем локальные assets (dev fallback)")
                assets_ok = True
            else:
                print("[INIT] Assets не найдены ни в AppData, ни локально")

                async def _retry(e):
                    dlg.open = False
                    page.update()
                    await build_assets()
                
                async def _close(e):
                    dlg.open = False
                    page.update()
                    await page.window.close()

                dlg = ft.AlertDialog(
                    modal=True,
                    title=ft.Text(
                        "Ошибка запуска" if sys_lang == 'ru' else "Launch Error",
                        weight=ft.FontWeight.BOLD
                    ),
                    content=ft.Text(
                        "Не хватает ресурсов для запуска приложения. Подключитесь к интернету для загрузки файлов с GitHub."
                        if sys_lang == 'ru' else
                        "Not enough resources to launch the application. Please connect to the internet to download files from GitHub."
                    ),
                    actions=[
                        ft.TextButton(
                            "Повторить" if sys_lang == 'ru' else "Retry",
                            on_click=lambda e: page.run_task(_retry, e)
                        ),
                        ft.TextButton(
                            "Закрыть" if sys_lang == 'ru' else "Close",
                            on_click=lambda e: page.run_task(_close, e)
                        ),
                    ],
                    actions_alignment=ft.MainAxisAlignment.END,
                )
                page.overlay.append(dlg)
                dlg.open = True
                page.update()
                return

        if CURRENT_VERSION != "dev":
            page.run_task(check_updates)

    sys_lang = i18n.detect_system_lang()
    i18n.set_lang(sys_lang)
    cfg = load_config()
    saved_lang = cfg.get('lang')
    if saved_lang:
        i18n.set_lang(saved_lang)
    else:
        cfg['lang'] = sys_lang
        save_config(cfg)

    def build_ui():
        global is_converting

        is_dev = (CURRENT_VERSION == "dev")
        print(f"[APP] build_ui: is_dev={is_dev}, CURRENT_VERSION={CURRENT_VERSION}")

        ffmpeg_indicator = FfmpegBadge()
        source_zone = SourceAudioZone()
        replace_zone = ReplaceAudioZone()

        async def handle_window_close(e: ft.Event[ft.IconButton]):
            await page.window.close()

        async def handle_window_minimize(e):
            page.window.minimized = True
            page.update()

        async def toggle_language(e):
            new_lang = 'en' if i18n.get_lang() == 'ru' else 'ru'
            i18n.set_lang(new_lang)
            cfg = load_config()
            cfg['lang'] = new_lang
            save_config(cfg)
            page.clean()
            build_ui()
            page.update()

        dev_badge = ft.Container(
            visible=is_dev,
            content=ft.Text(
                "dev",
                size=12,
                color=ft.Colors.PINK_400,
                weight=ft.FontWeight.BOLD,
            ),
            bgcolor=ft.Colors.with_opacity(0.12, ft.Colors.PINK_400),
            border_radius=6,
            padding=ft.Padding.symmetric(horizontal=8, vertical=4),
            tooltip="Development build",
        )

        nonlocal update_btn_ref
        update_btn = ft.IconButton(
            icon=ft.Icons.UPDATE,
            icon_color=ft.Colors.RED_400,
            tooltip=i18n.t("header.update_tooltip"),
            visible=False,
            on_click=lambda e: page.run_task(open_update_url, e)
        )
        update_btn_ref = update_btn

        header = ft.Container(
            content=ft.WindowDragArea(
                content=ft.Row(
                    [
                        ft.Text(i18n.t("app.title"), weight=ft.FontWeight.BOLD, size=18),
                        ft.Row(
                            [
                                dev_badge,
                                update_btn,
                                ft.Container(width=8),
                                ft.IconButton(
                                    icon=ft.Icons.LANGUAGE, 
                                    tooltip=i18n.t("header.language_tooltip"),
                                    icon_color=ft.Colors.BLUE_400,
                                    on_click=toggle_language
                                ),
                                ft.Container(width=8),
                                ffmpeg_indicator,

                                ft.Container(
                                    width=3,          
                                    height=24,        
                                    bgcolor=ft.Colors.PURPLE_300, 
                                    opacity=0.5,      
                                    margin=ft.Margin.symmetric(horizontal=15) 
                                ),

                                ft.Container(
                                    margin=ft.Margin.only(right=10),
                                    content=ft.Row(
                                        [
                                            ft.Container(
                                                width=18,
                                                height=18,
                                                shape=ft.BoxShape.CIRCLE,
                                                bgcolor="#FFBD2E",
                                                tooltip=i18n.t("header.minimize"),
                                                on_click=handle_window_minimize
                                            ),
                                            ft.Container(
                                                width=18,
                                                height=18,
                                                shape=ft.BoxShape.CIRCLE,
                                                bgcolor="#FF5F56",
                                                tooltip=i18n.t("header.close"),
                                                on_click=handle_window_close
                                            ),
                                        ],
                                        spacing=8 
                                    )
                                )
                            ],
                            spacing=0,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER
                )
            ),
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            border_radius=ft.BorderRadius.only(bottom_left=20, bottom_right=20),
            padding=ft.Padding.only(left=15, right=15), 
            margin=ft.Margin.only(left=15, right=15, top=0), 
            height=50,
        )

        async def on_replace_click(e):
            global is_converting

            if is_converting:
                return

            if not source_zone.audio_files or not source_zone.audio_files[source_zone.current_index]:
                show_snackbar(i18n.t("snackbar.error_source"))
                return

            if not replace_zone.new_file_path:
                show_snackbar(i18n.t("snackbar.error_replace"))
                return

            if source_zone.is_playing:
                await source_zone.stop_preview()
            if replace_zone.is_playing:
                await replace_zone.stop_preview()

            is_converting = True

            replace_btn_container.gradient = ft.LinearGradient(
                colors=[ft.Colors.AMBER, ft.Colors.ORANGE]
            )
            page.update()

            source_file = source_zone.audio_files[source_zone.current_index]

            try:
                success = process_audio_replace(
                    source_file_path=source_file,
                    new_file_path=replace_zone.new_file_path,
                    trim_start=replace_zone.trim_slider.start_value,
                    trim_end=replace_zone.trim_slider.end_value,
                    speed=replace_zone.current_speed,
                    volume=replace_zone.current_volume
                )

                if success:
                    replace_btn_container.gradient = ft.LinearGradient(
                        colors=[ft.Colors.GREEN_400, ft.Colors.GREEN_700]
                    )
                    page.update()

                    show_snackbar(i18n.t("snackbar.success", name=source_file.name))
                    source_zone._update_ui_state()

            except FileNotFoundError:
                show_snackbar(i18n.t("snackbar.error_ffmpeg"))
            except Exception as ex:
                show_snackbar(i18n.t("snackbar.error_convert", error=str(ex)))

            is_converting = False

            import asyncio
            await asyncio.sleep(3)

            replace_btn_container.gradient = ft.LinearGradient(
                begin=ft.Alignment.CENTER_LEFT,
                end=ft.Alignment.CENTER_RIGHT,
                colors=[ft.Colors.PINK_500, ft.Colors.LIGHT_BLUE_500]
            )
            page.update()

        def show_snackbar(text: str):
            page.show_dialog(
                ft.SnackBar(
                    content=ft.Text(text, color=ft.Colors.WHITE, weight=ft.FontWeight.W_500),
                    bgcolor=ft.Colors.GREY_900,
                    behavior=ft.SnackBarBehavior.FLOATING,
                    duration=3000
                )
            )

        replace_btn_text = ft.Text(
            i18n.t("btn.replace"), 
            weight=ft.FontWeight.BOLD, 
            size=14, 
            color=ft.Colors.PINK_600
        )

        replace_btn_container = ft.Container(
            width=650,
            height=48,
            border_radius=10,
            gradient=ft.LinearGradient(
                begin=ft.Alignment.CENTER_LEFT,
                end=ft.Alignment.CENTER_RIGHT,
                colors=[ft.Colors.PINK_500, ft.Colors.LIGHT_BLUE_500]
            ),
            padding=1.5,
            on_click=lambda e: page.run_task(on_replace_click, e), 
            content=ft.Container(
                bgcolor=ft.Colors.SURFACE, 
                border_radius=9,
                alignment=ft.Alignment.CENTER,
                content=ft.Row(
                    [replace_btn_text], 
                    alignment=ft.MainAxisAlignment.CENTER
                )
            )
        )

        main_layout = ft.Container(
            content=ft.Column([
                source_zone,           
                replace_zone,          
                replace_btn_container  
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=12),
            padding=15,
            alignment=ft.Alignment.TOP_CENTER,
            expand=True,
        )

        footer = ft.Container(
            content=ft.Text(
                "made by\nworld is cruel & oneover (design)",
                size=11,
                color=ft.Colors.BLUE_GREY_400, 
                weight=ft.FontWeight.W_400,
                text_align=ft.TextAlign.CENTER,
            ),
            alignment=ft.Alignment.CENTER,
            height=35,
            margin=ft.Margin.only(bottom=10),
        )

        shell = ft.Container(
            margin=ft.Margin.all(12),
            border_radius=12,
            bgcolor=ft.Colors.SURFACE,
            expand=True,
            content=ft.Column(
                [
                    header,
                    main_layout,
                    footer,
                ],
                spacing=0,
                expand=True,
            ),
        )
        page.add(shell)

    page.run_task(build_assets)
    build_ui()

ft.run(main)