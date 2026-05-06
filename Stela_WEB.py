import os
import uvicorn
import logging
from fastapi import FastAPI, Request
from groq import Groq
from yandex_music import Client as YandexClient
from docx import Document
from aiogram import Bot
from aiogram.types import FSInputFile

logging.basicConfig(level=logging.INFO)
app = FastAPI()

# Инициализация (с проверкой на существование ключей)
GROQ_KEY = os.getenv("GROQ_API_KEY")
Y_TOKEN = os.getenv("YANDEX_TOKEN")
TG_TOKEN = os.getenv("TELEGRAM_TOKEN")

ai_client = Groq(api_key=GROQ_KEY) if GROQ_KEY else None
y_client = YandexClient(Y_TOKEN).init() if Y_TOKEN else None
bot = Bot(token=TG_TOKEN) if TG_TOKEN else None

@app.get("/")
async def health():
    return {"status": "online", "ai": ai_client is not None}

@app.post("/ask")
async def ask(request: Request):
    try:
        data = await request.json()
        query = data.get("query", "")
        user_id = data.get("user_id", os.getenv("MY_CHAT_ID"))

        if not ai_client:
            return {"answer": "Критическая ошибка: API ключ ИИ не найден на сервере."}

        # 1. Запрос к ИИ
        sys_msg = "Ты Стела OS. Команды: [MUSIC] Исполнитель Трек. Отвечай кратко и мудро."
        completion = ai_client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": query}]
        )
        # ИСПРАВЛЕНО: Правильный доступ к результату
        answer = completion.choices[0].message.content
        music_url = None

        # 2. Обработка музыки
        if "[MUSIC]" in answer and y_client:
            try:
                search_q = answer.replace("[MUSIC]", "").strip()
                search = y_client.search(search_q)
                if search.tracks and search.tracks.results:
                    track = search.tracks.results[0]
                    info = track.get_download_info(get_direct_links=True)
                    music_url = info[0].direct_link
                    answer = f"🎵 Включаю: {track.title} - {track.artists[0].name}"
            except Exception as e:
                logging.error(f"Music error: {e}")

        return {"answer": answer, "music_url": music_url}

    except Exception as e:
        logging.error(f"Global error: {e}")
        return {"answer": f"Ошибка сервера: {str(e)}", "music_url": None}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
