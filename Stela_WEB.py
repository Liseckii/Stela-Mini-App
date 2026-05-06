import os
import uvicorn
import logging
from fastapi import FastAPI, Request
from groq import Groq
from yandex_music import Client as YandexClient

# Настройка логирования
logging.basicConfig(level=logging.INFO)
app = FastAPI()

# Инициализация сервисов из переменных Render
ai_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
y_client = YandexClient(os.getenv("YANDEX_TOKEN")).init()

@app.get("/")
async def health_check():
    return {"status": "Stela OS Server is Live"}

@app.post("/ask")
async def ask(request: Request):
    try:
        data = await request.json()
        query = data.get("query")
        user_id = data.get("user_id", "mobile_user")

        # 1. Запрос к Groq
        sys_prompt = "Ты Стела OS. Отвечай кратко. Если просят музыку, пиши [MUSIC] Название."
        completion = ai_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": sys_prompt}, {"role": "user", "content": query}]
        )
        res_ai = completion.choices[0].message.content

        # 2. Логика музыки
        music_url = None
        if "[MUSIC]" in res_ai:
            search_query = res_ai.replace("[MUSIC]", "").strip()
            search = y_client.search(search_query)
            if search.tracks and search.tracks.results:
                track = search.tracks.results[0]
                info = track.get_download_info(get_direct_links=True)
                music_url = info[0].direct_link
                res_ai = f"🎵 Включаю: {track.title} - {track.artists[0].name}"

        return {"answer": res_ai, "music_url": music_url}

    except Exception as e:
        logging.error(f"Error: {e}")
        return {"answer": f"Ошибка сервера: {str(e)}", "music_url": None}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
