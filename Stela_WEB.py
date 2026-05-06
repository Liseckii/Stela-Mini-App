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

# Инициализация
ai_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
y_client = YandexClient(os.getenv("YANDEX_TOKEN")).init()
bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))

def create_stela_doc(title, content):
    clean_title = "".join([c for c in title if c.isalnum() or c in (' ', '_')]).strip() or "StelaDoc"
    path = f"/tmp/{clean_title}.docx"
    doc = Document()
    doc.add_heading(title, 0)
    doc.add_paragraph(content)
    doc.save(path)
    return path

@app.post("/ask")
@app.post("/")
async def ask(request: Request):
    try:
        data = await request.json()
        query = data.get("query", "")
        user_id = data.get("user_id", os.getenv("MY_CHAT_ID"))

        sys = "Ты Стела OS. Команды: [MUSIC] Трек, [DOC] Заголовок|Текст, [SEARCH] Запрос."
        res = ai_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": sys}, {"role": "user", "content": query}]
        ).choices[0].message.content

        music_url = None
        # Логика команд
        if "[MUSIC]" in res:
            q = res.replace("[MUSIC]", "").strip()
            s = y_client.search(q)
            if s.tracks and s.tracks.results:
                t = s.tracks.results[0]
                music_url = t.get_download_info(get_direct_links=True)[0].direct_link
                res = f"🎵 Включаю: {t.title}"

        elif "[DOC]" in res:
            parts = res.replace("[DOC]", "").split("|")
            title = parts[0].strip() if len(parts)>0 else "Doc"
            body = parts[1].strip() if len(parts)>1 else "Контент"
            f_path = create_stela_doc(title, body)
            await bot.send_document(chat_id=user_id, document=FSInputFile(f_path))
            res = f"✅ Файл '{title}' отправлен в Telegram."

        elif "[SEARCH]" in res:
            with DDGS() as ddgs:
                search_res = [r['body'] for r in ddgs.text(res.replace("[SEARCH]", ""), max_results=1)]
                res = f"🔍 Нашла: {search_res[0]}" if search_res else "Ничего не нашла."

        return {"answer": res, "music_url": music_url}
    except Exception as e:
        return {"answer": f"Ошибка: {str(e)}"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
