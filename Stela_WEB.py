import os
import asyncio
import logging
import flet as ft
from groq import Groq
from yandex_music import Client as YandexClient
from docx import Document
from pptx import Presentation
from duckduckgo_search import DDGS
from supabase import create_client
from aiogram import Bot
from aiogram.types import FSInputFile
from urllib.parse import urlparse, parse_qs

# Настройка логирования для Render
logging.basicConfig(level=logging.INFO)

# --- БЕЗОПАСНАЯ ИНИЦИАЛИЗАЦИЯ ---
def init_services():
    try:
        ai = Groq(api_key=os.getenv("GROQ_API_KEY"))
        y_token = os.getenv("YANDEX_TOKEN")
        y_client = YandexClient(y_token).init() if y_token else None
        
        sb_url = os.getenv("SUPABASE_URL")
        sb_key = os.getenv("SUPABASE_KEY")
        supabase = create_client(sb_url, sb_key) if sb_url and sb_key else None
        
        bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))
        return ai, y_client, supabase, bot
    except Exception as e:
        logging.error(f"Critical Init Error: {e}")
        return None, None, None, None

ai_client, y_client, supabase, bot = init_services()

# --- МОДУЛЬ ФАЙЛОВ ---
def create_file(mode, title, content):
    clean_title = "".join([c for c in title if c.isalnum() or c in (' ', '_')]).strip()
    if not clean_title: clean_title = "Document"
    fname = f"/tmp/{clean_title}.docx" if mode == "DOC" else f"/tmp/{clean_title}.pptx"
    try:
        if mode == "DOC":
            doc = Document()
            doc.add_heading(clean_title, 0)
            doc.add_paragraph(content)
            doc.save(fname)
        else:
            prs = Presentation()
            slide = prs.slides.add_slide(prs.slides.add_slide_layouts[0])
            slide.shapes.title.text = clean_title
            slide.placeholders[1].text = content
            prs.save(fname)
        return fname
    except Exception as e:
        return f"Error: {e}"

# --- ГЛАВНЫЙ ИНТЕРФЕЙС ---
async def main_flet(page: ft.Page):
    # Пауза для корректного сбора данных URL в мобильном WebApp
    await asyncio.sleep(1.0)
    
    # Сбор данных пользователя
    user_id = "guest"
    try:
        if page.query_params and "user_id" in page.query_params:
            user_id = str(page.query_params["user_id"])
        elif page.route:
            user_id = parse_qs(urlparse(page.route).query).get("user_id", ["guest"])[0]
    except:
        user_id = "guest"

    # Параметры темы (загрузка из Supabase)
    accent = "cyan"
    page.bgcolor = "#050505"
    if supabase and user_id != "guest":
        try:
            res = supabase.table("stela_users").select("accent_color, bg_color").eq("user_id", user_id).execute()
            if res.data:
                accent = res.data[0].get("accent_color", "cyan")
                page.bgcolor = res.data[0].get("bg_color", "#050505")
        except: pass

    page.title = "Stela OS"
    page.theme_mode = ft.ThemeMode.DARK
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    # Плеер
    audio_player = ft.Audio(src="https://google.com", autoplay=False)
    page.overlay.append(audio_player)

    # Визуал: Сфера
    sphere = ft.Container(
        content=ft.Icon(ft.icons.AUTO_AWESOME_MOTION, size=70, color=accent),
        width=140, height=140, shape=ft.BoxShape.CIRCLE,
        shadow=ft.BoxShadow(blur_radius=40, color=accent),
        animate_scale=ft.animation.Animation(400, "easeInOut"),
    )

    chat_log = ft.Column(scroll=ft.ScrollMode.AUTO, height=300, spacing=10)
    input_f = ft.TextField(label="Команда Стеле...", border_color=accent, expand=True)

    async def run_cmd(e):
        txt = input_f.value
        if not txt: return
        input_f.value = ""
        sphere.scale = 1.2
        chat_log.controls.append(ft.Text(f"➤ {txt}", color="white70"))
        page.update()

        res_ai = "Ошибка ИИ"
        if ai_client:
            try:
                sys_msg = f"Ты Стела OS. Команды: [MUSIC] Трек, [DOC] Заголовок|Текст, [SEARCH] Запрос."
                comp = ai_client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": txt}]
                )
                res_ai = comp.choices[0].message.content
            except Exception as ex: res_ai = f"AI Error: {ex}"

        # ОБРАБОТКА
        try:
            if "[MUSIC]" in res_ai and y_client:
                q = res_ai.replace("[MUSIC]", "").strip()
                s = y_client.search(q)
                if s.tracks and s.tracks.results:
                    t = s.tracks.results[0]
                    audio_player.src = t.get_download_info(get_direct_links=True)[0].direct_link
                    audio_player.play()
                    res_ai = f"🎵 Играет: {t.title}"
            
            elif "[DOC]" in res_ai:
                p = res_ai.replace("[DOC]", "").split("|")
                title = p[0].strip() if len(p) > 0 else "Doc"
                text = p[1].strip() if len(p) > 1 else "..."
                fname = create_file("DOC", title, text)
                if bot and user_id != "guest":
                    await bot.send_document(chat_id=user_id, document=FSInputFile(fname))
                    res_ai = f"📄 Файл отправлен в ваш Telegram."
                else: res_ai = f"📄 Файл создан: {fname}"
        except Exception as err: res_ai = f"Ошибка команды: {err}"

        chat_log.controls.append(ft.Text(f"Стела: {res_ai}", color=accent))
        sphere.scale = 1.0
        page.update()

    # Сборка UI
    page.add(
        ft.Column([
            ft.Container(content=sphere, alignment=ft.alignment.center, padding=20),
            ft.Container(chat_log, padding=10, bgcolor="#111111", border_radius=15, width=350),
            ft.Row([input_f, ft.IconButton(ft.icons.SEND, on_click=run_cmd, icon_color=accent)], width=350)
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    )
    page.update()

if __name__ == "__main__":
    ft.app(
        target=main_flet, 
        view=ft.AppView.WEB_BROWSER, 
        web_renderer=ft.WebRenderer.HTML, 
        host="0.0.0.0", 
        port=int(os.getenv("PORT", 10000))
    )
