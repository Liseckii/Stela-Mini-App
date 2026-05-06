import os
import uvicorn
import logging
from fastapi import FastAPI, Request
from groq import Groq
from yandex_music import Client as YandexClient
from docx import Document
from duckduckgo_search import DDGS
from aiogram import Bot
from aiogram.types import FSInputFile

logging.basicConfig(level=logging.INFO)
app = FastAPI()

# Инициализация сервисов
ai_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
y_client = YandexClient(os.getenv("YANDEX_TOKEN")).init()
bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))

def create_stela_doc(title, content):
    # Очистка заголовка от спецсимволов для безопасности
    clean_title = "".join([c for c in title if c.isalnum() or c in (' ', '_')]).strip() or "Stela_Doc"
    path = f"/tmp/{clean_title}.docx"
    doc = Document()
    doc.add_heading(title, 0)
    doc.add_paragraph(content)
    doc.save(path)
    return path

@app.get("/")
async def health(): 
    return {"status": "Stela OS 3.0 Live"}

@app.post("/ask")
async def ask(request: Request):
    try:
        data = await request.json()
        query = data.get("query", "")
        user_id = data.get("user_id", os.getenv("MY_CHAT_ID"))

        sys_prompt = "Ты Стела OS. Команды: [MUSIC] Исполнитель Трек, [DOC] Заголовок|Текст, [SEARCH] Запрос."
        completion = ai_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": sys_prompt}, {"role": "user", "content": query}]
        )
        res = completion.choices[0].message.content
        music_url = None

        # --- Обработка команд ---
        if "[MUSIC]" in res:
            q = res.replace("[MUSIC]", "").strip()
            search = y_client.search(q)
            if search.tracks and search.tracks.results:
                track = search.tracks.results[0]
                # Исправлено: получение первой доступной прямой ссылки
                info = track.get_download_info(get_direct_links=True)
                music_url = info[0].direct_link
                res = f"🎵 Включаю: {track.title} - {track.artists[0].name}"

        elif "[DOC]" in res:
            parts = res.replace("[DOC]", "").split("|")
            title = parts[0].strip() if len(parts) > 0 else "Doc"
            body = parts[1].strip() if len(parts) > 1 else "Содержимое"
            f_path = create_stela_doc(title, body)
            # Отправка и закрытие сессии для стабильности Render
            await bot.send_document(chat_id=user_id, document=FSInputFile(f_path))
            res = f"✅ Файл '{title}' отправлен вам в Telegram."
            if os.path.exists(f_path): os.remove(f_path)

        elif "[SEARCH]" in res:
            with DDGS() as ddgs:
                results = [r['body'] for r in ddgs.text(res.replace("[SEARCH]", ""), max_results=1)]
                res = f"🔍 Нашла: {' '.join(results)[:300]}..."

        return {"answer": res, "music_url": music_url}

    except Exception as e:
        logging.error(f"Error: {e}")
        return {"answer": f"⚠️ Системная ошибка: {str(e)}", "music_url": None}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
