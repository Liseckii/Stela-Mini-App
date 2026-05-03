import os
import asyncio
import logging
import flet as ft
from flet import audio # Прямой импорт для аудио-модуля
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from groq import Groq
from yandex_music import Client

# 1. ЗАГРУЗКА КОНФИГУРАЦИИ
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
YANDEX_TOKEN = os.getenv("YANDEX_TOKEN")
RENDER_URL = "https://onrender.com"

logging.basicConfig(level=logging.INFO)

# Инициализация сервисов
ai_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
y_client = Client(YANDEX_TOKEN).init() if YANDEX_TOKEN else None
bot = Bot(token=TELEGRAM_TOKEN) if TELEGRAM_TOKEN else None
dp = Dispatcher()

# --- МОЗГ СТЕЛЫ ---
async def get_stela_ai_response(prompt):
    if not ai_client: return "Ключ AI не найден."
    def sync_ai():
        try:
            system_msg = (
                "Ты Стела. Если просят музыку, отвечай строго: [MUSIC] Артист - Название. "
                "В остальных случаях отвечай кратко, мудро и остроумно на русском."
            )
            completion = ai_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "system", "content": system_msg}, {"role": "user", "content": prompt}]
            )
            return completion.choices.message.content
        except Exception as e:
            return f"Сбой нейронной сети: {str(e)}"
    
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, sync_ai)

# --- ИНТЕРФЕЙС (PREMIUM TUNING) ---
async def main_flet(page: ft.Page):
    page.title = "Stela Premium"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#000000"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    # Плеер (исправлен вызов через модуль audio)
    audio_player = audio.Audio(src="", autoplay=True)
    page.overlay.append(audio_player)

    # Футуристичная сфера
    sphere_icon = ft.Icon(ft.icons.AUTO_AWESOME_MOTION, size=70, color="cyan200")
    sphere = ft.Container(
        content=sphere_icon,
        width=180, height=180, shape=ft.BoxShape.CIRCLE,
        gradient=ft.RadialGradient(colors=["#0d47a1", "black"]),
        shadow=ft.BoxShadow(blur_radius=60, color="blue900"),
        animate_scale=400,
        animate=ft.animation.Animation(800, "easeInOut"),
    )

    # Стеклянное окно чата с авто-переносом текста
    status_text = ft.Text("СИСТЕМА СТЕЛЫ АКТИВНА", size=14, color="cyan100", text_align="center", no_wrap=False)
    chat_box = ft.Container(
        content=ft.Column([status_text], scroll=ft.ScrollMode.AUTO, horizontal_alignment="center"),
        padding=15, width=320, height=140, border_radius=20,
        bgcolor=ft.colors.with_opacity(0.1, "white"),
        border=ft.border.all(1, ft.colors.with_opacity(0.2, "white")),
    )

    input_f = ft.TextField(
        label="Команда...", 
        width=300, 
        border_radius=15, 
        border_color="blue800",
        on_submit=lambda _: asyncio.create_task(run_stela(None))
    )

    async def run_stela(e):
        if not input_f.value: return
        text = input_f.value
        input_f.value = ""
        status_text.value = "ОБРАБОТКА..."
        sphere.scale = 1.1
        page.update()

        res = await get_stela_ai_response(text)

        if "[MUSIC]" in res and y_client:
            query = res.replace("[MUSIC]", "").strip()
            search = y_client.search(query)
            if search.tracks and search.tracks.results:
                track = search.tracks.results[0]
                status_text.value = f"ИГРАЕТ:\n{track.title}\n{track.artists[0].name}"
                
                # Ставим обложку
                if track.cover_uri:
                    img = f"https://{track.cover_uri.replace('%%', '400x400')}"
                    sphere.content = ft.Image(src=img, border_radius=90, fit=ft.ImageFit.COVER)
                
                # Запускаем звук
                try:
                    links = track.get_download_info(get_direct_links=True)
                    audio_player.src = links[0].direct_link # Берем первую ссылку из списка
                    audio_player.play()
                except Exception as ex:
                    status_text.value = f"ОШИБКА ПОТОКА: {ex}"
            else:
                status_text.value = "МУЗЫКА НЕ НАЙДЕНА В ЯНДЕКСЕ"
        else:
            status_text.value = res
            sphere.content = sphere_icon
            # Голосовой ответ
            if hasattr(page, "tts") and page.tts:
                page.tts.say(res)

        sphere.scale = 1.0
        page.update()

    page.add(
        sphere, ft.Container(height=30),
        chat_box, ft.Container(height=20),
        input_f,
        ft.ElevatedButton("ВЫПОЛНИТЬ", on_click=run_stela, bgcolor="blue900", color="white")
    )

# --- ЗАПУСК БОТА ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="STELA OS [ЗАПУСК]", web_app=WebAppInfo(url=RENDER_URL))]
    ])
    await message.answer("Стела готова к работе. Нажми кнопку ниже.", reply_markup=markup)

async def start():
    # Запуск бота
    if bot:
        asyncio.create_task(dp.start_polling(bot))
    
    # Запуск Flet как веб-приложения
    await ft.app_async(
        target=main_flet,
        view=ft.AppView.WEB_BROWSER,
        port=int(os.getenv("PORT", 10000)),
        host="0.0.0.0"
    )

if __name__ == "__main__":
    try:
        asyncio.run(start())
    except KeyboardInterrupt:
        pass
