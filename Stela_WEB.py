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

# 1. НАСТРОЙКИ
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

# --- ЛОГИКА МОЗГА СТЕЛЫ ---
async def get_stela_logic(prompt):
    if not ai_client: return "Ошибка: Ключи не настроены."
    
    def sync_ai():
        try:
            # Даем ИИ инструкцию, как вызывать музыку
            system_prompt = (
                "Ты — Стела. Если пользователь просит музыку, начни ответ с 'MUSIC_QUERY: ' "
                "и напиши только название трека и исполнителя. В остальных случаях просто отвечай остроумно."
            )
            completion = ai_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ]
            )
            return completion.choices[0].message.content
        except Exception as e:
            return f"Ошибка ИИ: {str(e)}"

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, sync_ai)

# --- ИНТЕРФЕЙС MINI APP ---
async def main_flet(page: ft.Page):
    page.title = "Стела ИИ"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#0a0a0a"
    page.vertical_alignment = "center"
    page.horizontal_alignment = "center"

    # Визуальный элемент (Сфера / Обложка)
    sphere_content = ft.Icon(ft.icons.AUTO_AWESOME, size=60, color="cyan200")
    sphere = ft.Container(
        content=sphere_content,
        width=200, height=200, shape="circle",
        gradient=ft.RadialGradient(colors=["blue900", "black"]),
        shadow=ft.BoxShadow(blur_radius=50, color="blue700"),
        animate=ft.animation.Animation(600, ft.AnimationCurve.EASE_OUT),
        animate_scale=400,
    )

    status = ft.Text("Стела готова к приключениям", size=16, text_align="center", color="cyan100")
    input_f = ft.TextField(label="Напиши или попроси музыку...", width=300, border_radius=15)

    async def handle_action(e):
        if not input_f.value: return
        
        user_text = input_f.value
        input_f.value = ""
        status.value = "Стела размышляет..."
        sphere.scale = 1.2
        page.update()

        ai_response = await get_stela_logic(user_text)

        # ПРОВЕРКА: Музыка или Текст?
        if "MUSIC_QUERY:" in ai_response and y_client:
            query = ai_response.replace("MUSIC_QUERY:", "").strip()
            search = y_client.search(query)
            
            if search.tracks and search.tracks.results:
                track = search.tracks.results[0]
                status.value = f"Включаю: {track.title}\n{track.artists[0].name}"
                
                # Загружаем обложку
                if track.cover_uri:
                    cover_url = f"https://{track.cover_uri.replace('%%', '200x200')}"
                    sphere.content = ft.Image(src=cover_url, border_radius=100, fit="cover")
                
                # Озвучиваем статус
                if page.tts: page.tts.say(f"Нашла для тебя {track.title}")
            else:
                status.value = f"Я искала {query}, но ничего не нашла..."
                if page.tts: page.tts.say("Прости, музыку не нашла.")
        else:
            # Обычный ответ
            status.value = ai_response
            sphere.content = ft.Icon(ft.icons.AUTO_AWESOME, size=60, color="cyan200")
            if page.tts: 
                await page.tts.say_async(ai_response)

        sphere.scale = 1.0
        page.update()

    page.add(
        sphere,
        ft.Container(height=30),
        status,
        ft.Container(height=20),
        input_f,
        ft.ElevatedButton("Спросить / Включить", on_click=handle_action, bgcolor="blue800", color="white")
    )

# --- ТЕЛЕГРАМ БОТ ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Призвать Стелу 🎙", web_app=WebAppInfo(url=RENDER_URL))]
    ])
    await message.answer("Я готова. Могу поболтать или найти музыку. Жми!", reply_markup=markup)

# --- ЗАПУСК ---
async def start_all():
    if bot: asyncio.create_task(dp.start_polling(bot))
    await ft.app_async(
        target=main_flet,
        view=ft.AppView.WEB_BROWSER,
        port=int(os.getenv("PORT", 10000)),
        host="0.0.0.0"
    )

if __name__ == "__main__":
    asyncio.run(start_all())
