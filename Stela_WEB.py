import os
import asyncio
import logging
import flet as ft
from groq import Groq
from yandex_music import Client as YandexClient
from docx import Document
from pptx import Presentation
from duckduckgo_search import DDGS
from supabase import create_client, Client as SupabaseClient
from aiogram import Bot
from aiogram.types import FSInputFile

# --- НАСТРОЙКИ ---
logging.basicConfig(level=logging.INFO)

def init_services():
    try:
        # Инициализация Supabase
        sb_url = os.getenv("SUPABASE_URL")
        sb_key = os.getenv("SUPABASE_KEY")
        supabase = create_client(sb_url, sb_key) if sb_url else None
        
        # Инициализация Groq
        ai = Groq(api_key=os.getenv("GROQ_API_KEY"))
        
        # Инициализация общего Яндекса (для гостей)
        y_token = os.getenv("YANDEX_TOKEN")
        y_client = YandexClient(y_token).init() if y_token else None
        
        # Инициализация бота для отправки файлов
        bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))
        
        return supabase, ai, y_client, bot
    except Exception as e:
        logging.error(f"Ошибка инициализации: {e}")
        return None, None, None, None

supabase, ai_client, y_client, bot = init_services()

# --- ИНСТРУМЕНТЫ ---
def create_file(mode, title, content):
    clean_title = "".join([c for c in title if c.isalnum() or c in (' ', '_')]).strip()
    if not clean_title: clean_title = "Document"
    fname = f"/tmp/{clean_title}.docx" if mode == "DOC" else f"/tmp/{clean_title}.pptx"
    try:
        if mode == "DOC":
            doc = Document(); doc.add_heading(clean_title, 0); doc.add_paragraph(content); doc.save(fname)
        else:
            prs = Presentation(); slide = prs.slides.add_slide(prs.slide_layouts)
            slide.shapes.title.text = clean_title; slide.placeholders.text = content; prs.save(fname)
        return fname
    except Exception as e: return f"Error: {e}"

# --- ИНТЕРФЕЙС ---
async def main_flet(page: ft.Page):
    await asyncio.sleep(0.5)
    
    # Получаем ID из URL или ставим дефолт
    user_id = page.query_params.get("user_id", os.getenv("MY_CHAT_ID", "guest"))
    
    # Пытаемся загрузить тему пользователя из Supabase
    accent_color = "cyan"
    if supabase:
        try:
            res = supabase.table("stela_users").select("*").eq("user_id", str(user_id)).execute()
            if res.data:
                accent_color = res.data[0].get("accent_color", "cyan")
        except: pass

    page.title = "Stela OS"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#050505"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    # Плеер с заглушкой
    audio_player = ft.Audio(src="https://google.com", autoplay=False)
    page.overlay.append(audio_player)

    # Визуал
    sphere = ft.Container(
        content=ft.Icon(ft.icons.AUTO_AWESOME_MOTION, size=70, color=accent_color),
        width=140, height=140, shape=ft.BoxShape.CIRCLE,
        shadow=ft.BoxShadow(blur_radius=40, color=accent_color),
        animate_scale=ft.animation.Animation(400, "easeInOut"),
    )

    chat_log = ft.Column(scroll=ft.ScrollMode.AUTO, height=300, spacing=10)
    input_f = ft.TextField(label="Команда...", border_color=accent_color, expand=True)

    async def run_cmd(e):
        txt = input_f.value
        if not txt: return
        input_f.value = ""
        sphere.scale = 1.2
        chat_log.controls.append(ft.Text(f"➤ {txt}", color="white70"))
        page.update()

        res_ai = "Ошибка системы"
        if ai_client:
            try:
                sys_msg = "Ты Стела. Команды: [MUSIC] Трек, [DOC] Заголовок|Текст, [SEARCH] Запрос."
                comp = ai_client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": txt}]
                )
                res_ai = comp.choices[0].message.content
            except Exception as ex: res_ai = f"AI Error: {ex}"

        # ОБРАБОТКА КОМАНД
        try:
            if "[MUSIC]" in res_ai and y_client:
                q = res_ai.replace("[MUSIC]", "").strip()
                s = y_client.search(q)
                if s.tracks and s.tracks.results:
                    t = s.tracks.results[0]
                    lnk = t.get_download_info(get_direct_links=True)[0].direct_link
                    audio_player.src = lnk
                    audio_player.play()
                    res_ai = f"🎵 Играет: {t.title}"
                
            elif "[DOC]" in res_ai:
                p = res_ai.replace("[DOC]", "").split("|")
                fname = create_file("DOC", p[0].strip(), p[1].strip() if len(p)>1 else "...")
                # Отправка файла пользователю в Telegram
                if bot and user_id != "guest":
                    await bot.send_document(chat_id=user_id, document=FSInputFile(fname))
                    res_ai = f"📄 Файл создан и отправлен вам в личку."
                else: res_ai = f"📄 Файл создан (войдите через бота для получения)."

            elif "[SEARCH]" in res_ai:
                with DDGS() as ddgs:
                    r = [res['body'] for res in ddgs.text(res_ai.replace("[SEARCH]", ""), max_results=2)]
                    res_ai = f"🔍 Нашла: {' '.join(r)[:300]}..."
        except Exception as err: res_ai = f"Ошибка: {err}"

        chat_log.controls.append(ft.Text(f"Стела: {res_ai}", color=accent_color))
        sphere.scale = 1.0
        page.update()

    page.add(
        ft.Column([
            ft.Center(sphere),
            ft.Container(chat_log, padding=10, bgcolor="#111111", border_radius=15, width=350),
            ft.Row([input_f, ft.IconButton(ft.icons.SEND, on_click=run_cmd, icon_color=accent_color)], width=350)
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    )

if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    ft.app(target=main_flet, view=ft.AppView.WEB_BROWSER, web_renderer=ft.WebRenderer.HTML, host="0.0.0.0", port=port)
