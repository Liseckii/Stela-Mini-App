import os
import asyncio
import logging
import flet as ft
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from groq import Groq

# 1. ЗАГРУЗКА НАСТРОЕК
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
# Твой адрес на Render (проверь, чтобы совпадал!)
RENDER_URL = "https://onrender.com" 

logging.basicConfig(level=logging.INFO)

# Инициализация объектов
ai_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
bot = Bot(token=TELEGRAM_TOKEN) if TELEGRAM_TOKEN else None
dp = Dispatcher()

# --- ЛОГИКА AI (STELA) ---
async def get_stela_answer(prompt):
    if not ai_client:
        return "Ошибка: Не настроен API ключ Groq."
    
    def sync_ai():
        try:
            completion = ai_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": "Ты Стела, краткий ИИ ассистент."},
                    {"role": "user", "content": prompt}
                ]
            )
            return completion.choices.message.content
        except Exception as e:
            return f"Ошибка ИИ: {str(e)}"

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, sync_ai)

# --- ИНТЕРФЕЙС (FLET MINI APP) ---
async def main_flet(page: ft.Page):
    page.title = "Стела ИИ"
    page.theme_mode = ft.ThemeMode.DARK
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.padding = 20

    # Визуальный эффект "Сферы"
    sphere = ft.Container(
        content=ft.Icon(ft.icons.AUTO_AWESOME, size=60, color=ft.colors.CYAN_200),
        width=160,
        height=160,
        shape=ft.BoxShape.CIRCLE,
        gradient=ft.RadialGradient(colors=[ft.colors.BLUE_900, ft.colors.BLACK]),
        shadow=ft.BoxShadow(blur_radius=50, color=ft.colors.BLUE_700),
        animate_scale=ft.animation.Animation(400, ft.AnimationCurve.BOUNCE_OUT),
    )

    status_label = ft.Text("Стела готова", size=16, text_align="center")
    input_field = ft.TextField(
        label="Спроси меня...",
        width=300,
        border_radius=15,
        border_color=ft.colors.CYAN_900
    )

    async def handle_submit(e):
        if not input_field.value:
            return
        
        user_text = input_field.value
        input_field.value = ""
        status_label.value = "Стела думает..."
        sphere.scale = 1.2
        page.update()

        response = await get_stela_answer(user_text)
        
        status_label.value = response
        sphere.scale = 1.0
        
        if hasattr(page, "tts") and page.tts:
            page.tts.say(response)
        
        page.update()

    page.add(
        sphere,
        ft.Container(height=20),
        status_label,
        ft.Container(height=10),
        input_field,
        ft.ElevatedButton(
            "Спросить", 
            on_click=handle_submit,
            style=ft.ButtonStyle(color=ft.colors.WHITE, bgcolor=ft.colors.BLUE_800)
        )
    )

# --- ТЕЛЕГРАМ БОТ ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="Запустить Стелу 🎙", 
            web_app=WebAppInfo(url=RENDER_URL)
        )]
    ])
    await message.answer("Я готова. Нажми кнопку ниже!", reply_markup=markup)

# --- ЗАПУСК ---
async def start_all():
    # Запуск бота в фоне
    if bot:
        asyncio.create_task(dp.start_polling(bot))
    
    # Запуск Flet сервера
    await ft.app_async(
        target=main_flet,
        view=ft.AppView.WEB_BROWSER,
        port=int(os.getenv("PORT", 10000)),
        host="0.0.0.0"
    )

if __name__ == "__main__":
    try:
        asyncio.run(start_all())
    except KeyboardInterrupt:
        pass
