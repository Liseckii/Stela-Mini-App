import os
import asyncio
import logging
from dotenv import load_dotenv

# Веб-сервер и интерфейс
import flet as ft
import flet_fastapi
from fastapi import FastAPI

# Бот и ИИ
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from groq import Groq

# 1. ЗАГРУЗКА КОНФИГУРАЦИИ
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
RENDER_URL = "https://onrender.com" # Убедись, что это твой адрес на Render

logging.basicConfig(level=logging.INFO)

# Инициализация (с проверкой на наличие ключей)
ai_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
bot = Bot(token=TELEGRAM_TOKEN) if TELEGRAM_TOKEN else None
dp = Dispatcher()

# --- ЛОГИКА ИИ (STELA) ---
async def get_stela_answer(prompt):
    if not ai_client:
        return "Ошибка: Не настроен API ключ Groq."
    
    def sync_ai():
        try:
            completion = ai_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": "Ты — Стела. Остроумный и краткий ИИ ассистент. Отвечай на русском."},
                    {"role": "user", "content": prompt}
                ],
            )
            return completion.choices.message.content
        except Exception as e:
            return f"Мои мысли запутались: {str(e)}"
    
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, sync_ai)

# --- ИНТЕРФЕЙС (FLET MINI APP) ---
async def main_flet(page: ft.Page):
    page.title = "Стела ИИ"
    page.theme_mode = ft.ThemeMode.DARK
    page.window_bgcolor = ft.colors.BLACK
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    # Визуальный эффект "Сферы"
    sphere = ft.Container(
        content=ft.Icon(ft.icons.AUTO_AWESOME, size=60, color=ft.colors.CYAN_200),
        width=160,
        height=160,
        shape=ft.BoxShape.CIRCLE,
        gradient=ft.RadialGradient(
            colors=[ft.colors.BLUE_900, ft.colors.BLACK]
        ),
        shadow=ft.BoxShadow(blur_radius=50, color=ft.colors.BLUE_700),
        animate_scale=ft.animation.Animation(400, ft.AnimationCurve.BOUNCE_OUT),
    )

    status_label = ft.Text("Стела слушает", size=16, italic=True, color=ft.colors.CYAN_100)
    input_field = ft.TextField(
        label="Спроси Стелу...",
        width=300,
        border_radius=10,
        border_color=ft.colors.CYAN_900,
        focused_border_color=ft.colors.CYAN_400
    )

    async def handle_submit(e):
        if not input_field.value: return
        
        status_label.value = "Стела думает..."
        sphere.scale = 1.2
        page.update()

        response = await get_stela_answer(input_field.value)
        
        status_label.value = response
        sphere.scale = 1.0
        input_field.value = ""
        
        # Озвучка (работает в браузерах с поддержкой TTS)
        if page.tts:
            page.tts.say(response)
        
        page.update()

    page.add(
        sphere,
        ft.Container(height=20),
        status_label,
        ft.Container(height=10),
        input_field,
        ft.ElevatedButton(
            "Отправить", 
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
            web_app=WebAppInfo(url=f"{RENDER_URL}/stela")
        )]
    ])
    await message.answer(
        "Я Стела. Твой новый ИИ-ассистент в формате Mini App. Нажми кнопку ниже!",
        reply_markup=markup
    )

# --- ИНТЕГРАЦИЯ И ЗАПУСК ---
app = FastAPI()

# Подключаем Flet к FastAPI по пути /stela
app.mount("/stela", flet_fastapi.app(main_flet))

@app.on_event("startup")
async def on_startup():
    if bot:
        # Запускаем бота асинхронно, чтобы не блокировать сервер
        asyncio.create_task(dp.start_polling(bot))
    else:
        logging.error("БОТ НЕ ЗАПУЩЕН: Проверь TELEGRAM_TOKEN!")

if __name__ == "__main__":
    import uvicorn
    # Render передает порт через переменную окружения
    port = int(os.getenv("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
