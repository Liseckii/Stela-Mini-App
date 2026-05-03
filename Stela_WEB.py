import os
import asyncio
import logging
import flet as ft
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from groq import Groq

# Настройки
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
# Твой адрес на Render (без /stela в конце для этого способа)
RENDER_URL = "https://onrender.com" 

logging.basicConfig(level=logging.INFO)

# Инициализация
ai_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
bot = Bot(token=TELEGRAM_TOKEN) if TELEGRAM_TOKEN else None
dp = Dispatcher()

# --- ЛОГИКА ИИ ---
async def get_stela_answer(prompt):
    if not ai_client: return "Ключ ИИ не настроен."
    def sync_ai():
        completion = ai_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": "Ты — Стела. Остроумный ИИ."}, {"role": "user", "content": prompt}],
        )
        return completion.choices.message.content
    return await asyncio.get_event_loop().run_in_executor(None, sync_ai)

# --- ИНТЕРФЕЙС FLET ---
async def main_flet(page: ft.Page):
    page.title = "Стела ИИ"
    page.theme_mode = ft.ThemeMode.DARK
    page.vertical_alignment = "center"
    page.horizontal_alignment = "center"

    sphere = ft.Container(
        content=ft.Icon(ft.icons.AUTO_AWESOME, size=60, color="cyan200"),
        width=160, height=160, shape="circle",
        gradient=ft.RadialGradient(colors=["blue900", "black"]),
        shadow=ft.BoxShadow(blur_radius=50, color="blue700"),
        animate_scale=400,
    )

    status = ft.Text("Стела готова", size=16)
    input_f = ft.TextField(label="Спросить Стелу...", width=300)

    async def send_click(e):
        if not input_f.value: return
        status.value = "Стела думает..."
        sphere.scale = 1.2
        page.update()
        
        res = await get_stela_answer(input_f.value)
        
        status.value = res
        sphere.scale = 1.0
        input_f.value = ""
        if page.tts: page.tts.say(res)
        page.update()

    page.add(sphere, ft.Container(height=20), status, input_f, 
             ft.ElevatedButton("Спросить", on_click=send_click))

# --- ТЕЛЕГРАМ БОТ ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Запустить Стелу 🎙", web_app=WebAppInfo(url=RENDER_URL))]
    ])
    await message.answer("Стела готова. Нажми кнопку!", reply_markup=markup)

# --- ЗАПУСК ---
async def start_all():
    # Запускаем бота в фоне
    if bot:
        asyncio.create_task(dp.start_polling(bot))
    
    # Запускаем Flet как веб-сервер
    await ft.app_async(
        target=main_flet,
        view=ft.AppView.WEB_BROWSER,
        port=int(os.getenv("PORT", 10000)),
        host="0.0.0.0"
    )

if __name__ == "__main__":
    asyncio.run(start_all())
