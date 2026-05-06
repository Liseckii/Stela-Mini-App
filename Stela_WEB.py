import os
import uvicorn
import logging
from fastapi import FastAPI, Request
from groq import Groq
from yandex_music import Client as YandexClient

# Настройка логирования
logging.basicConfig(level=logging.INFO)
app = FastAPI()

# Инициализация сервисов
try:
    ai_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    y_token = os.getenv("YANDEX_TOKEN")
    y_client = YandexClient(y_token).init() if y_token else None
except Exception as e:
    logging.error(f"Критическая ошибка инициализации: {e}")

# Обработка запросов и на главную, и на /ask
@app.post("/")
@app.post("/ask")
async def ask(request: Request):
    try:
        data = await request.json()
        query = data.get("query", "Привет")
        
        # Запрос к Llama
        completion = ai_client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[
                {"role": "system", "content": "Ты Стела OS. Отвечай кратко."},
                {"role": "user", "content": query}
            ]
        )
        answer = completion.choices[0].message.content
        music_url = None

        # Поиск музыки
        if "[MUSIC]" in answer and y_client:
            q = answer.replace("[MUSIC]", "").strip()
            search = y_client.search(q)
            if search.tracks and search.tracks.results:
                t = search.tracks.results[0]
                music_url = t.get_download_info(get_direct_links=True)[0].direct_link
                answer = f"🎵 Включаю: {t.title}"

        return {"answer": answer, "music_url": music_url}

    except Exception as e:
        logging.error(f"Ошибка на сервере: {e}")
        return {"answer": f"Ошибка системы: {str(e)}", "music_url": None}

# Хелсчек для браузера
@app.get("/")
async def health():
    return {"status": "online", "ai_ready": os.getenv("GROQ_API_KEY") is not None}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
