import os
import uvicorn
import logging
from fastapi import FastAPI, Request
from groq import Groq
from yandex_music import Client as YandexClient
from docx import Document
from aiogram import Bot
from aiogram.types import FSInputFile

# Настройка логирования
logging.basicConfig(level=logging.INFO)
app = FastAPI()

# Инициализация сервисов
try:
    ai_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    y_token = os.getenv("YANDEX_TOKEN")
    y_client = YandexClient(y_token).init() if y_token else None
    bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))
except Exception as e:
    logging.error(f"Ошибка инициализации сервисов: {e}")

def create_doc(title, content):
    clean_title = "".join([c for c in title if c.isalnum() or c in (' ', '_')]).strip() or "StelaDoc"
    path = f"/tmp/{clean_title}.docx"
    doc = Document()
    doc.add_heading(title, 0)
    doc.add_paragraph(content)
    doc.save(path)
    return path

@app.post("/")
@app.post("/ask")
async def ask(request: Request):
    try:
        data = await request.json()
        query = data.get("query", "")
        user_id = data.get("user_id", os.getenv("MY_CHAT_ID"))

        # 1. Запрос к ИИ (Llama 3.1)
        sys_prompt = "Ты Стела OS. Команды: [MUSIC] Название, [DOC] Заголовок|Текст. Отвечай кратко."
        completion = ai_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": sys_prompt}, {"role": "user", "content": query}]
        )
        answer = completion.choices[0].message.content
        music_url = None

        # 2. Логика музыки
        if "[MUSIC]" in answer and y_client:
            q_music = answer.replace("[MUSIC]", "").strip()
            search = y_client.search(q_music)
            if search.tracks and search.tracks.results:
                track = search.tracks.results[0]
                info = track.get_download_info(get_direct_links=True)
                music_url = info[0].direct_link
                answer = f"🎵 Включаю: {track.title}"

        # 3. Логика файлов
        elif "[DOC]" in answer:
            parts = answer.replace("[DOC]", "").split("|")
            t = parts[0].strip() if len(parts) > 0 else "Документ"
            c = parts[1].strip() if len(parts) > 1 else "Контент"
            f_path = create_doc(t, c)
            await bot.send_document(chat_id=user_id, document=FSInputFile(f_path))
            answer = f"✅ Файл '{t}' отправлен в Telegram."

        return {"answer": answer, "music_url": music_url}

    except Exception as e:
        logging.error(f"Ошибка: {e}")
        return {"answer": f"Ошибка сервера: {str(e)}", "music_url": None}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
