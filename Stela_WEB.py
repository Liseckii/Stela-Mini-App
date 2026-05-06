import os
import uvicorn
import logging
import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from groq import Groq
from yandex_music import Client as YandexClient
from aiogram import Bot
from aiogram.types import FSInputFile
from docx import Document
from pptx import Presentation
from duckduckgo_search import DDGS

# Инициализация
logging.basicConfig(level=logging.INFO)
app = FastAPI()

ai_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
y_client = YandexClient(os.getenv("YANDEX_TOKEN")).init()
bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))

def create_stela_file(mode, title, content):
    clean_title = "".join([c for c in title if c.isalnum() or c in (' ', '_')]).strip() or "StelaDoc"
    path = f"/tmp/{clean_title}.docx" if mode == "DOC" else f"/tmp/{clean_title}.pptx"
    if mode == "DOC":
        doc = Document(); doc.add_heading(title, 0); doc.add_paragraph(content); doc.save(path)
    else:
        prs = Presentation(); slide = prs.slides.add_slide(prs.slide_layouts); slide.shapes.title.text = title; slide.placeholders.text = content; prs.save(path)
    return path

# --- ИНТЕРФЕЙС С ГОЛОСОМ ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
    <script src="https://telegram.org"></script>
    <style>
        body { background: #000; color: #fff; font-family: 'Segoe UI', sans-serif; margin: 0; padding: 20px; display: flex; flex-direction: column; height: 100vh; justify-content: space-between; overflow: hidden; }
        .sphere { width: 130px; height: 130px; background: radial-gradient(circle, #00f2ff, #000); border-radius: 50%; margin: 20px auto; box-shadow: 0 0 35px #00f2ff; transition: 0.4s; cursor: pointer; }
        .sphere.listening { box-shadow: 0 0 60px #ff00ea; background: radial-gradient(circle, #ff00ea, #000); transform: scale(1.1); }
        #chat { flex: 1; overflow-y: auto; background: rgba(255,255,255,0.05); border-radius: 20px; padding: 15px; margin-bottom: 15px; font-size: 14px; }
        .msg { margin-bottom: 10px; }
        .ai { color: #00f2ff; font-weight: bold; }
        .user { color: #888; text-align: right; }
        .input-box { display: flex; gap: 10px; }
        input { flex: 1; background: #111; border: 1px solid #333; border-radius: 12px; color: #fff; padding: 12px; outline: none; }
        button { background: #00f2ff; color: #000; border: none; border-radius: 12px; padding: 0 20px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="sphere" id="sphere" onclick="startVoice()"></div>
    <div id="chat">Система Stela OS готова к голосу...</div>
    <div class="input-box">
        <input type="text" id="input" placeholder="Команда или нажми на сферу...">
        <button onclick="send()">➤</button>
    </div>
    <audio id="player" style="display:none"></audio>

    <script>
        const tg = window.Telegram.WebApp;
        tg.expand();
        
        const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
        recognition.lang = 'ru-RU';

        function startVoice() {
            document.getElementById('sphere').classList.add('listening');
            recognition.start();
        }

        recognition.onresult = (event) => {
            const text = event.results[0][0].transcript;
            document.getElementById('input').value = text;
            document.getElementById('sphere').classList.remove('listening');
            send();
        };

        async function send() {
            const input = document.getElementById('input');
            const val = input.value;
            if(!val) return;
            
            document.getElementById('chat').innerHTML += `<div class="msg user">➤ ${val}</div>`;
            input.value = '';

            const res = await fetch('/ask', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({query: val, user_id: tg.initDataUnsafe.user?.id || "guest"})
            });
            const data = await res.json();

            document.getElementById('chat').innerHTML += `<div class="msg ai">Стела: ${data.answer}</div>`;
            
            // Озвучка ответа
            const speech = new SpeechSynthesisUtterance(data.answer.replace(/\[.*?\]/g, ''));
            speech.lang = 'ru-RU';
            window.speechSynthesis.speak(speech);

            if(data.music_url) {
                const p = document.getElementById('player');
                p.src = data.music_url;
                p.play();
            }
            document.getElementById('chat').scrollTop = 9999;
        }
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def index(): return HTML_TEMPLATE

@app.post("/ask")
async def ask(request: Request):
    data = await request.json()
    query = data.get("query")
    user_id = str(data.get("user_id", os.getenv("MY_CHAT_ID")))
    
    res = ai_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "system", "content": "Ты Стела OS. Команды: [MUSIC], [DOC], [SEARCH]"}, {"role": "user", "content": query}]
    ).choices[0].message.content

    music_url = None
    try:
        if "[MUSIC]" in res:
            search = y_client.search(res.replace("[MUSIC]", "").strip())
            if search.tracks and search.tracks.results:
                t = search.tracks.results[0]
                music_url = t.get_download_info(get_direct_links=True)[0].direct_link
                res = f"🎵 Включаю: {t.title}"
        elif "[DOC]" in res:
            path = create_stela_file("DOC", "Stela_File", res.replace("[DOC]", ""))
            await bot.send_document(chat_id=user_id, document=FSInputFile(path))
            res = "📄 Файл отправлен в ваш Telegram."
    except Exception as e: res = f"Ошибка: {str(e)}"

    return {"answer": res, "music_url": music_url}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 10000)))

