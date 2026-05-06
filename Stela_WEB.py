import os
import asyncio
import logging
import flet as ft
from groq import Groq
from yandex_music import Client as YandexClient
from docx import Document
from duckduckgo_search import DDGS
from aiogram import Bot
from aiogram.types import FSInputFile

logging.basicConfig(level=logging.INFO)

# --- Инициализация ---
ai_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
y_client = YandexClient(os.getenv("YANDEX_TOKEN")).init()
bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))

# --- Функции ---
async def search_music(query):
    try:
        search = y_client.search(query)
        if search.tracks and search.tracks.results:
            t = search.tracks.results[0]
            # Берем самую короткую прямую ссылку
            info = t.get_download_info(get_direct_links=True)[0]
            return {"url": info.direct_link, "title": f"{t.title} - {t.artists[0].name}"}
    except: return None

def create_doc(title, content):
    path = f"/tmp/stela_file.docx"
    doc = Document()
    doc.add_heading(title, 0)
    doc.add_paragraph(content)
    doc.save(path)
    return path

# --- Интерфейс ---
async def main_flet(page: ft.Page):
    page.theme_mode = "dark"
    page.bgcolor = "#050505"
    accent = "cyan"
    
    # Получаем ID пользователя
    user_id = page.query_params.get("user_id", os.getenv("MY_CHAT_ID"))

    audio_player = ft.Audio(src="https://google.com", autoplay=False)
    page.overlay.append(audio_player)

    sphere = ft.Container(
        content=ft.Icon(ft.icons.AUTO_AWESOME_MOTION, size=70, color=accent),
        width=140, height=140, shape="circle",
        shadow=ft.BoxShadow(blur_radius=40, color=accent),
        animate_scale=400
    )

    chat = ft.Column(scroll="auto", height=350, spacing=10)

    async def run_stela(e):
        txt = input_f.value
        if not txt: return
        input_f.value = ""
        sphere.scale = 1.2
        chat.controls.append(ft.Text(f"➤ {txt}", color="white70"))
        page.update()

        # Запрос к ИИ
        sys_msg = "Ты Стела. Команды: [MUSIC] Исполнитель Трек, [DOC] Заголовок|Текст, [SEARCH] Запрос."
        res = ai_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": txt}]
        ).choices[0].message.content

        # Логика команд
        if "[MUSIC]" in res:
            m_data = await search_music(res.replace("[MUSIC]", "").strip())
            if m_data:
                audio_player.src = m_data["url"]
                audio_player.play()
                res = f"🎵 Включаю: {m_data['title']}"
            else: res = "Трек не найден."

        elif "[DOC]" in res:
            parts = res.replace("[DOC]", "").split("|")
            title = parts[0].strip() if len(parts)>0 else "Документ"
            body = parts[1].strip() if len(parts)>1 else "Контент"
            f_path = create_doc(title, body)
            await bot.send_document(user_id, FSInputFile(f_path))
            res = "📄 Документ готов и отправлен вам в Telegram!"

        elif "[SEARCH]" in res:
            with DDGS() as ddgs:
                search_res = [r['body'] for r in ddgs.text(res.replace("[SEARCH]", ""), max_results=1)]
                res = f"🔍 Нашла: {search_res[0]}" if search_res else "Ничего не нашла."

        chat.controls.append(ft.Text(f"Стела: {res}", color=accent))
        sphere.scale = 1.0
        page.update()

    input_f = ft.TextField(label="Команда Стеле...", expand=True, on_submit=run_stela)
    
    page.add(
        ft.Column([
            ft.Center(sphere),
            ft.Container(chat, padding=10, bgcolor="#111111", border_radius=15),
            ft.Row([input_f, ft.IconButton(ft.icons.SEND, on_click=run_stela, icon_color=accent)])
        ], horizontal_alignment="center")
    )

if __name__ == "__main__":
    ft.app(target=main_flet, view=ft.AppView.WEB_BROWSER, web_renderer="html", host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
