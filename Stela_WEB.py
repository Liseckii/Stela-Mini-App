import os
import uvicorn
import logging
from fastapi import FastAPI, Request
from groq import Groq
from yandex_music import Client as YandexClient

# Настройка логов
logging.basicConfig(level=logging.INFO)
app = FastAPI()

# Инициализация сервисов с проверкой ключей
try:
    ai_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    y_token = os.getenv("YANDEX_TOKEN")
    y_client = YandexClient(y_token).init() if y_token else None
except Exception as e:
    logging.error(f"Ошибка при старте сервисов: {e}")

@app.get("/")
async def health():
    return {"status": "Stela OS Server is Live", "ai_ready": os.getenv("GROQ_API_KEY") is not None}

@app.post("/ask")
async def ask(request: Request):
    try:
        data = await request.json()
        query = data.get("query", "")
        
        if not query:
            return {"answer": "Запрос пуст."}

        # 1. Запрос к ИИ
        sys_msg = "Ты Стела OS. Команды: [MUSIC] Название. Отвечай кратко."
        completion = ai_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": sys_msg},
                {"role": "user", "content": query}
            ]
        )
        answer = completion.choices[0].message.content
        music_url = None

        # 2. Логика музыки
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
                logging.error(f"Ошибка музыки: {e}")

        return {"answer": answer, "music_url": music_url}

    except Exception as e:
        logging.error(f"Ошибка сервера: {e}")
        return {"answer": f"Системная ошибка: {str(e)}"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
