import os
import asyncio
import logging
import flet as ft
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from groq import Groq
from yandex_music import Client

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

# --- ИНТЕЛЛЕКТ СТЕЛЫ ---
async def get_stela_ai_response(prompt):
    if not ai_client: return "Ключ AI не найден."
    def sync_ai():
        try:
            # Четкая инструкция для ИИ
            system_msg = (
                "Ты Стела. Если просят музыку, отвечай только: [MUSIC] Артист - Название. "
                "В остальных случаях отвечай кратко и мудро."
            )
            completion = ai_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "system", "content": system_msg}, {"role": "user", "content": prompt}]
            )
            return completion.choices[0].message.content
        except: return "Сбой нейронной сети."
    
    return await asyncio.get_event_loop().run_in_executor(None, sync_ai)

# --- ИНТЕРФЕЙС (PREMIUM TUNING) ---
async def main_flet(page: ft.Page):
    page.title = "Stela Premium"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#000000"
    page.vertical_alignment = "center"
    page.horizontal_alignment = "center"

    # Невидимый плеер
    audio_player = ft.Audio(src="", autoplay=True)
    page.overlay.append(audio_player)

    # Футуристичная сфера
    sphere_icon = ft.Icon(ft.icons.AUTO_AWESOME_MOTION, size=70, color="cyan200")
    sphere = ft.Container(
        content=sphere_icon,
        width=180, height=180, shape="circle",
        gradient=ft.RadialGradient(colors=["#0d47a1", "black"]),
        shadow=ft.BoxShadow(blur_radius=60, color="blue900"),
        animate_scale=400,
        animate=ft.animation.Animation(800, "easeInOut"),
    )

    # Стеклянное окно чата
    status_text = ft.Text("СИСТЕМА СТЕЛЫ АКТИВНА", size=14, color="cyan100", text_align="center")
    chat_box = ft.Container(
        content=ft.Column([status_text], scroll="auto", horizontal_alignment="center"),
        padding=15, width=320, height=140, border_radius=20,
        bgcolor=ft.colors.with_opacity(0.1, "white"),
        border=ft.border.all(1, ft.colors.with_opacity(0.2, "white")),
    )

    input_f = ft.TextField(label="Команда...", width=300, border_radius=15, border_color="blue800")

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
                    sphere.content = ft.Image(src=img, border_radius=90, fit="cover")
                # Запускаем звук
                try:
                    links = track.get_download_info(get_direct_links=True)
                    audio_player.src = links[0].direct_link
                    audio_player.play()
                except: status_text.value = "ОШИБКА СТРИМИНГА"
            else:
                status_text.value = "МУЗЫКА НЕ НАЙДЕНА"
        else:
            status_text.value = res
            sphere.content = sphere_icon
            if page.tts: page.tts.say(res)

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
    if bot: asyncio.create_task(dp.start_polling(bot))
    await ft.app_async(target=main_flet, view=ft.AppView.WEB_BROWSER, port=int(os.getenv("PORT", 10000)), host="0.0.0.0")

if __name__ == "__main__":
    asyncio.run(start())
