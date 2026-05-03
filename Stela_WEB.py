import os
import asyncio
import logging
from dotenv import load_dotenv

# Библиотеки для веб-интерфейса
import flet as ft
import flet_fastapi
from fastapi import FastAPI

# Библиотеки для бота и ИИ
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from groq import Groq

# Загрузка настроек
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
RENDER_URL = "https://onrender.com" # Проверь свой URL на Render

# Инициализация ИИ и Бота
ai_client = Groq(api_key=GROQ_API_KEY)
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

logging.basicConfig(level=logging.INFO)

# --- ЛОГИКА AI ---
def get_stela_answer(prompt):
    try:
        completion = ai_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "Ты — Стела, идеальный ИИ. Отвечай кратко, остроумно и на русском."},
                {"role": "user", "content": prompt}
            ],
        )
        return completion.choices.message.content
    except Exception as e:
        return f"Ошибка мыслей: {e}"

# --- ИНТЕРФЕЙС FLET (Mini App) ---
async def main_flet(page: ft.Page):
    page.title = "Стела ИИ"
    page.theme_mode = ft.ThemeMode.DARK
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.padding = 50

    # Сфера Стелы
    sphere = ft.Container(
        content=ft.Icon(ft.icons.STARS_ROUNDED, size=80, color=ft.colors.WHITE),
        width=200,
        height=200,
        shape=ft.BoxShape.CIRCLE,
        gradient=ft.RadialGradient(
            colors=[ft.colors.CYAN_ACCENT, ft.colors.BLUE_800, ft.colors.BLACK]
        ),
        shadow=ft.BoxShadow(blur_radius=50, color=ft.colors.CYAN_400),
        animate=ft.animation.Animation(600, ft.AnimationCurve.DECELERATE),
    )

    status_text = ft.Text("Стела готова к общению", size=18, text_align="center")
    
    # Поле ввода (так как микрофон в чистом Flet WEB иногда капризный)
    user_input = ft.TextField(
        label="Твое сообщение...", 
        border_color=ft.colors.CYAN_700,
        on_submit=lambda e: process_text(e.control.value)
    )

    async def process_text(text):
        if not text: return
        status_text.value = "Стела думает..."
        sphere.scale = 1.2
        page.update()
        
        answer = await asyncio.to_thread(get_stela_answer, text)
        
        status_text.value = answer
        sphere.scale = 1.0
        # Используем новый метод озвучки Flet 0.21+
        if page.tts:
            page.tts.say(answer)
        
        user_input.value = ""
        page.update()

    page.add(
        sphere,
        ft.Divider(height=40, color=ft.colors.TRANSPARENT),
        status_text,
        ft.Divider(height=20, color=ft.colors.TRANSPARENT),
        user_input,
        ft.ElevatedButton("Спросить", on_click=lambda _: process_text(user_input.value))
    )

# --- ЛОГИКА ТЕЛЕГРАМ БОТА ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Открыть Стелу 🎙", web_app=WebAppInfo(url=f"{RENDER_URL}/stela"))]
    ])
    await message.answer(
        "Привет! Я Стела. Нажми кнопку ниже, чтобы открыть мой интерфейс.",
        reply_markup=markup
    )

# --- ЗАПУСК ВСЕГО ВМЕСТЕ ---
app = FastAPI()

# Интегрируем Flet в FastAPI
app.mount("/stela", flet_fastapi.app(main_flet))

@app.on_event("startup")
async def on_startup():
    # Запускаем бота при старте сервера
    asyncio.create_task(dp.start_polling(bot))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
