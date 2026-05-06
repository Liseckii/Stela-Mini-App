import os
import asyncio
import logging
import flet as ft
from flet import audio
from supabase import create_client, Client as SupabaseClient
from groq import Groq
from yandex_music import Client as YandexClient
from docx import Document
from pptx import Presentation
from duckduckgo_search import DDGS

# 1. КОНФИГУРАЦИЯ (Берем всё из переменных Render)
load_dotenv = lambda: None # На Render переменные подтягиваются сами
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
YANDEX_TOKEN = os.getenv("YANDEX_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") # Тот самый ключ, что ты прислал
MY_CHAT_ID = os.getenv("MY_CHAT_ID")

# Инициализация сервисов
supabase: SupabaseClient = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL else None
ai_client = Groq(api_key=GROQ_API_KEY)
y_client = YandexClient(YANDEX_TOKEN).init()

# --- ФУНКЦИИ ИНСТРУМЕНТОВ ---

def create_and_send_doc(mode, title, content):
    fname = f"{title}.docx" if mode == "DOC" else f"{title}.pptx"
    if mode == "DOC":
        doc = Document()
        doc.add_heading(title, 0)
        doc.add_paragraph(content)
        doc.save(fname)
    else:
        prs = Presentation()
        slide = prs.slides.add_slide(prs.slide_layouts[0])
        slide.shapes.title.text = title
        slide.placeholders[1].text = content
        prs.save(fname)
    return fname

def web_search(query):
    with DDGS() as ddgs:
        results = [r['body'] for r in ddgs.text(query, max_results=3)]
        return "\n".join(results)

# --- ИНТЕРФЕЙС СТЕЛЫ ---

async def main_flet(page: ft.Page):
    # В версии 0.22.0 параметры URL лежат здесь:
    user_id = page.query_params.get("user_id", "default_user")
    
    # Печатаем для отладки в логи Render (увидишь в консоли)
    print(f"Запуск для пользователя: {user_id}")

    # Загружаем тему (если нет — дефолт)
    res = supabase.table("stela_users").select("*").eq("user_id", user_id).execute()
    u_data = res.data[0] if res.data else {"bg_color": "#000000", "accent_color": "cyan"}
    
    page.bgcolor = u_data.get("bg_color")
    accent = u_data.get("accent_color")
    
    # Плеер
    audio_player = audio.Audio(src="", autoplay=True)
    page.overlay.append(audio_player)

    # Анимированная сфера
    sphere = ft.Container(
        content=ft.Icon(ft.icons.AUTO_AWESOME_MOTION, size=80, color=accent),
        width=160, height=160, shape="circle",
        shadow=ft.BoxShadow(blur_radius=50, color=accent),
        animate=ft.animation.Animation(600, "bounceOut"),
        animate_scale=ft.animation.Animation(400, "easeInOut"),
    )

    chat_log = ft.Column(scroll="auto", height=250)
    input_f = ft.TextField(label="Введите команду...", border_color=accent, expand=True)

    async def run_logic(e):
        prompt = input_f.value
        if not prompt: return
        input_f.value = ""
        sphere.scale = 1.3
        chat_log.controls.append(ft.Text(f"Вы: {prompt}", color="white70"))
        page.update()

        # Запрос к Llama-3 (Groq)
        system_msg = "Ты Стела. Команды: [MUSIC] Исполнитель - Трек, [DOC] Заголовок | Текст, [SEARCH] Запрос."
        completion = ai_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": system_msg}, {"role": "user", "content": prompt}]
        )
        res_ai = completion.choices.message.content

        # Обработка команд
        if "[SEARCH]" in res_ai:
            q = res_ai.replace("[SEARCH]", "").strip()
            data = web_search(q)
            res_ai = f"Нашла в сети: {data[:200]}..."
        
        elif "[MUSIC]" in res_ai:
            q = res_ai.replace("[MUSIC]", "").strip()
            search = y_client.search(q)
            if search.tracks:
                track = search.tracks.results[0]
                audio_player.src = track.get_download_info(get_direct_links=True)[0].direct_link
                audio_player.play()
                res_ai = f"Слушаем: {track.title}"

        elif "[DOC]" in res_ai:
            parts = res_ai.replace("[DOC]", "").split("|")
            fname = create_and_send_doc("DOC", parts[0].strip(), parts[1] if len(parts)>1 else "...")
            res_ai = f"Файл {fname} создан и сохранен!"

        chat_log.controls.append(ft.Text(f"Стела: {res_ai}", color=accent))
        sphere.scale = 1.0
        page.update()

    # --- ВКЛАДКА НАСТРОЕК ---
    async def save_settings(e):
        new_data = {"bg_color": cp_bg.value, "accent_color": cp_acc.value}
        supabase.table("stela_users").upsert({"user_id": user_id, **new_data}).execute()
        page.bgcolor = cp_bg.value
        page.update()

    cp_bg = ft.TextField(label="Цвет фона (HEX)", value=page.bgcolor)
    cp_acc = ft.TextField(label="Цвет акцента", value=accent)

    # Компоновка вкладок
    tabs = ft.Tabs(
        selected_index=0,
        tabs=[
            ft.Tab(text="Чат", content=ft.Column([ft.Center(sphere), chat_log, ft.Row([input_f, ft.IconButton(ft.icons.SEND, on_click=run_logic)])])),
            ft.Tab(text="Вид", content=ft.Column([cp_bg, cp_acc, ft.ElevatedButton("Сохранить", on_click=save_settings)]))
        ], expand=1
    )

    page.add(tabs)

# Запуск приложения на Render
if __name__ == "__main__":
    import os
    # Render автоматически передает номер порта в переменную PORT
    port = int(os.getenv("PORT", 10000)) 
    
    ft.app(
        target=main_flet,
        view=ft.AppView.WEB_BROWSER,
        host="0.0.0.0",  # ОБЯЗАТЕЛЬНО для Render
        port=port        # ОБЯЗАТЕЛЬНО для Render
    )
