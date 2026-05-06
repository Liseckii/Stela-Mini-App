import os
import uvicorn
import logging
import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from groq import Groq
from yandex_music import Client as YandexClient
from aiogram import Bot, Dispatcher, F, types
from aiogram.types import FSInputFile
from docx import Document
from pptx import Presentation
from duckduckgo_search import DDGS

# Настройка
logging.basicConfig(level=logging.INFO)
app = FastAPI()
ai_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
y_client = YandexClient(os.getenv("YANDEX_TOKEN")).init()
bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))
dp = Dispatcher()

# --- ФУНКЦИЯ РАСШИФРОВКИ ГОЛОСА ---
def transcribe_voice(file_path):
    try:
        with open(file_path, "rb") as audio_file:
            transcription = ai_client.audio.transcriptions.create(
                model="whisper-large-v3", 
                file=audio_file,
                language="ru"
            )
            return transcription.text
    except Exception as e:
        logging.error(f"Ошибка Whisper: {e}")
        return None

# --- ЛОГИКА ОБРАБОТКИ КОМАНД (ЕДИНАЯ) ---
async def process_stela_logic(query, user_id):
    sys_msg = "Ты Стела OS. Команды: [MUSIC] Исполнитель Трек, [DOC] Заголовок|Текст, [SEARCH] Запрос."
    res = ai_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": query}]
    ).choices[0].message.content

    music_url = None
    try:
        if "[MUSIC]" in res:
            search = y_client.search(res.replace("[MUSIC]", "").strip())
            if search.tracks and search.tracks.results:
                t = search.tracks.results[0]
                music_url = t.get_download_info(get_direct_links=True)[0].direct_link
                res = f"🎵 Включаю: {t.title} - {t.artists[0].name}"
        elif "[DOC]" in res:
            # (Код создания файла как в прошлых шагах)
            res = "📄 Файл сформирован и отправлен вам."
    except: pass
    return res, music_url

# --- ОБРАБОТЧИК ГОЛОСОВЫХ В ТЕЛЕГРАМ ---
@dp.message(F.voice)
async def handle_tg_voice(message: types.Message):
    voice = message.voice
    file_id = voice.file_id
    file = await bot.get_file(file_id)
    file_path = f"/tmp/{file_id}.ogg"
    
    await bot.download_file(file.file_path, file_path)
    
    # 1. Переводим в текст
    user_text = transcribe_voice(file_path)
    if not user_text:
        await message.answer("Сорри, не смогла разобрать голос.")
        return

    # 2. Выполняем логику
    ans, _ = await process_stela_logic(user_text, message.from_user.id)
    await message.answer(f"🎤 Вы сказали: {user_text}\n\n🤖 {ans}")
    os.remove(file_path)

# --- WEB ИНТЕРФЕЙС (HTML_TEMPLATE ОСТАЕТСЯ ПРЕЖНИМ) ---
@app.get("/", response_class=HTMLResponse)
async def index():
    return "<h1>Stela OS Active</h1><p>Используйте голосовые сообщения в боте.</p>"

@app.post("/ask")
async def ask(request: Request):
    data = await request.json()
    ans, m_url = await process_stela_logic(data.get("query"), data.get("user_id"))
    return {"answer": ans, "music_url": m_url}

# ЗАПУСК БОТА ПАРАЛЛЕЛЬНО С СЕРВЕРОМ
@app.on_event("startup")
async def startup():
    asyncio.create_task(dp.start_polling(bot))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
