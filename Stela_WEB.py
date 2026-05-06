import os
import asyncio
import logging
import flet as ft
from flet import Audio, animation
from urllib.parse import urlparse, parse_qs

# Импорты сервисов
from groq import Groq
from yandex_music import Client as YandexClient
from docx import Document
from pptx import Presentation
from duckduckgo_search import DDGS

logging.basicConfig(level=logging.INFO)

# --- БЕЗОПАСНАЯ ИНИЦИАЛИЗАЦИЯ ---
def safe_init():
    try:
        ai = Groq(api_key=os.getenv("GROQ_API_KEY"))
        # Пробуем инициализировать Яндекс, если токен есть
        token = os.getenv("YANDEX_TOKEN")
        y_client = YandexClient(token).init() if token else None
        return ai, y_client
    except Exception as e:
        logging.error(f"Ошибка сервисов: {e}")
        return None, None

ai_client, y_client = safe_init()

# --- ФУНКЦИИ ИНСТРУМЕНТОВ (с записью в /tmp/) ---
def create_tmp_file(mode, title, content):
    # На Render пишем только в /tmp/
    fname = f"/tmp/{title}.docx" if mode == "DOC" else f"/tmp/{title}.pptx"
    if mode == "DOC":
        doc = Document(); doc.add_heading(title, 0); doc.add_paragraph(content); doc.save(fname)
    else:
        prs = Presentation(); slide = prs.slides.add_slide(prs.slide_layouts)
        slide.shapes.title.text = title; slide.placeholders.text = content; prs.save(fname)
    return fname

# --- ОСНОВНОЙ ИНТЕРФЕЙС ---
async def main_flet(page: ft.Page):
    # Критически важная пауза для загрузки свойств страницы
    await asyncio.sleep(0.5)
    
    # Безопасный сбор ID пользователя
    user_id = "guest"
    try:
        if hasattr(page, "route") and page.route:
            parsed = urlparse(page.route)
            params = parse_qs(parsed.query)
            user_id = params.get("user_id", ["guest"])[0]
    except Exception as e:
        logging.error(f"Router error: {e}")

    page.title = "Stela OS"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#050505"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    accent = "cyan"

    # Аудио-плеер
    audio_player = ft.Audio(src="https://", autoplay=True)
    page.overlay.append(audio_player)

    # Визуал: Сфера
    sphere = ft.Container(
        content=ft.Icon(ft.icons.AUTO_AWESOME_MOTION, size=70, color=accent),
        width=140, height=140, shape=ft.BoxShape.CIRCLE,
        shadow=ft.BoxShadow(blur_radius=40, color=accent),
        animate_scale=ft.animation.Animation(400, "easeInOut"),
    )

    chat_log = ft.Column(scroll=ft.ScrollMode.AUTO, height=300, spacing=10)
    input_f = ft.TextField(label="Команда...", border_color=accent, expand=True)

    async def run_cmd(e):
        txt = input_f.value
        if not txt: return
        input_f.value = ""
        sphere.scale = 1.2
        chat_log.controls.append(ft.Text(f"Вы: {txt}", color="white70"))
        page.update()

        # Заглушка логики (вставь сюда вызов ИИ из прошлых шагов)
        res = "Стела активна и обрабатывает запрос..."
        
        chat_log.controls.append(ft.Text(f"Стела: {res}", color=accent))
        sphere.scale = 1.0
        page.update()

    # Сборка экрана
    page.add(
        ft.Column([
            ft.Center(sphere),
            ft.Container(chat_log, padding=10, bgcolor="#111111", border_radius=15, width=350),
            ft.Row([input_f, ft.IconButton(ft.icons.SEND, on_click=run_cmd, icon_color=accent)], width=350)
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    )
    page.update()

# --- СТАРТ ---
if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    ft.app(
        target=main_flet,
        view=ft.AppView.WEB_BROWSER,
        web_renderer=ft.WebRenderer.HTML,
        host="0.0.0.0",
        port=port
    )
