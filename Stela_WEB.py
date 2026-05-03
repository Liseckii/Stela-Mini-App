import os
import asyncio
from dotenv import load_dotenv
from fastapi import FastAPI, Request, UploadFile, File
from fastapi.templating import Jinja2Templates
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton

load_dotenv()

# Инициализация
app = FastAPI()
templates = Jinja2Templates(directory="templates")
bot = Bot(token=os.getenv('TELEGRAM_TOKEN'))
dp = Dispatcher()

# --- ЛОГИКА WEB-ИНТЕРФЕЙСА ---

@app.get("/")
async def serve_home(request: Request):
    # Отдает твою сферу из index.html
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/process_audio")
async def process_audio(audio: UploadFile = File(...)):
    # Сюда прилетит звук из Mini App
    with open("voice_from_app.wav", "wb") as f:
        f.write(await audio.read())
    # Тут вызывай распознавание и ответ AI
    return {"status": "ok"}

# --- ЛОГИКА БОТА ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    # ЗАМЕНИ НА СВОЙ URL ПОСЛЕ ДЕПЛОЯ
    web_app_url = "https://onrender.com" 
    
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Призвать Стелу 🎙", web_app=WebAppInfo(url=web_app_url))]
    ])
    await message.answer("Я готова! Нажми на сферу.", reply_markup=markup)

# --- ЗАПУСК ---

async def run_bot():
    await dp.start_polling(bot)

if __name__ == "__main__":
    import uvicorn
    # Запускаем бота в отдельном потоке
    loop = asyncio.get_event_loop()
    loop.create_task(run_bot())
    # Запускаем веб-сервер
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
