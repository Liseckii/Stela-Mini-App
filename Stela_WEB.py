import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
from groq import Groq
from yandex_music import Client as YandexClient
from aiogram import Bot
from aiogram.types import FSInputFile
from docx import Document

app = FastAPI()
ai_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
y_client = YandexClient(os.getenv("YANDEX_TOKEN")).init()
bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))

# HTML-интерфейс прямо в коде для удобства
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
    <script src="https://telegram.org"></script>
    <style>
        body { background: #050505; color: white; font-family: sans-serif; text-align: center; margin: 0; padding: 20px; }
        .sphere { width: 120px; height: 120px; background: radial-gradient(circle, cyan, black); border_radius: 50%; margin: 30px auto; box-shadow: 0 0 40px cyan; transition: 0.3s; }
        #chat { height: 300px; overflow-y: auto; background: #111; border-radius: 15px; padding: 10px; margin-bottom: 20px; text-align: left; font-size: 14px; }
        input { width: 80%; padding: 12px; border-radius: 10px; border: 1px solid cyan; background: #000; color: white; }
    </style>
</head>
<body>
    <div class="sphere" id="sphere"></div>
    <div id="chat">Система Stela OS готова...</div>
    <input type="text" id="input" placeholder="Команда..." onkeypress="if(event.key=='Enter') send()">
    <audio id="player" style="display:none"></audio>

    <script>
        const tg = window.Telegram.WebApp;
        tg.expand();

        async def send() {
            const val = document.getElementById('input').value;
            if(!val) return;
            document.getElementById('chat').innerHTML += `<p style="color:gray">➤ ${val}</p>`;
            document.getElementById('input').value = '';
            
            const sphere = document.getElementById('sphere');
            sphere.style.transform = 'scale(1.2)';

            const res = await fetch('/ask', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({query: val, user_id: tg.initDataUnsafe.user?.id || "guest"})
            });
            const data = await res.json();
            
            document.getElementById('chat').innerHTML += `<p style="color:cyan">Стела: ${data.answer}</p>`;
            if(data.music_url) {
                const p = document.getElementById('player');
                p.src = data.music_url;
                p.play();
            }
            sphere.style.transform = 'scale(1.0)';
        }
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def get_index():
    return HTML_TEMPLATE

@app.post("/ask")
async def ask_stela(request: Request):
    data = await request.json()
    query = data.get("query")
    user_id = data.get("user_id")
    
    # Логика Groq
    res = ai_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "system", "content": "Ты Стела. Команды: [MUSIC], [DOC]"}, {"role": "user", "content": query}]
    ).choices[0].message.content

    music_url = None
    if "[MUSIC]" in res:
        search = y_client.search(res.replace("[MUSIC]", "").strip())
        if search.tracks:
            music_url = search.tracks.results[0].get_download_info(get_direct_links=True)[0].direct_link

    if "[DOC]" in res:
        # Логика создания и отправки файла через bot.send_document (как в прошлом коде)
        pass

    return {"answer": res, "music_url": music_url}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
