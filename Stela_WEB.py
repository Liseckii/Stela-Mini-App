import os
import asyncio
import logging
import flet as ft
from supabase import create_client, Client as SupabaseClient
from groq import Groq
from yandex_music import Client as YandexClient
from docx import Document
from pptx import Presentation
from duckduckgo_search import DDGS
from urllib.parse import urlparse, parse_qs

# 1. ИНИЦИАЛИЗАЦИЯ СЕРВИСОВ
logging.basicConfig(level=logging.INFO)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: SupabaseClient = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL else None

ai_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
y_client = YandexClient(os.getenv("YANDEX_TOKEN")).init()
bot_token = os.getenv("TELEGRAM_TOKEN")

# --- ИНСТРУМЕНТЫ (ФАЙЛЫ И ПОИСК) ---
def create_file(mode, title, content):
    fname = f"{title}.docx" if mode == "DOC" else f"{title}.pptx"
    if mode == "DOC":
        doc = Document()
        doc.add_heading(title, 0)
        doc.add_paragraph(content)
        doc.save(fname)
    else:
        prs = Presentation()
        slide = prs.slides.add_slide(prs.slide_layouts)
        slide.shapes.title.text = title
        slide.placeholders.text = content
        prs.save(fname)
    return fname

def web_search(query):
    try:
        with DDGS() as ddgs:
            results = [r['body'] for r in ddgs.text(query, max_results=2)]
            return "\n".join(results)
    except: return "Поиск временно недоступен."

# --- ОСНОВНОЙ ИНТЕРФЕЙС ---
async def main_flet(page: ft.Page):
    # 1. ПОЛУЧЕНИЕ USER_ID (Безопасный метод для 0.22.1)
    user_id = "default_user"
    try:
        if page.query_params:
            user_id = page.query_params.get("user_id", user_id)
    except: pass

    # 2. ЗАГРУЗКА НАСТРОЕК ИЗ ОБЛАКА
    u_data = {"bg_color": "#000000", "accent_color": "cyan"}
    if supabase:
        try:
            res = supabase.table("stela_users").select("*").eq("user_id", user_id).execute()
            if res.data: u_data = res.data[0]
        except: pass

    page.title = "Stela Premium OS"
    page.bgcolor = u_data.get("bg_color", "#000000")
    accent = u_data.get("accent_color", "cyan")
    page.theme_mode = ft.ThemeMode.DARK
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    # Плеер (корректный импорт для 0.22.1)
    audio_player = ft.Audio(src="https://", autoplay=True)
    page.overlay.append(audio_player)

    # Анимированная сфера
    sphere = ft.Container(
        content=ft.Icon(ft.icons.AUTO_AWESOME_MOTION, size=80, color=accent),
        width=160, height=160, shape=ft.BoxShape.CIRCLE,
        shadow=ft.BoxShadow(blur_radius=50, color=accent),
        animate_scale=ft.animation.Animation(400, "easeInOut"),
    )

    chat_log = ft.Column(scroll=ft.ScrollMode.AUTO, height=250, width=350)
    input_f = ft.TextField(label="Команда...", border_color=accent, expand=True)

    async def run_logic(e):
        prompt = input_f.value
        if not prompt: return
        input_f.value = ""
        sphere.scale = 1.3
        chat_log.controls.append(ft.Text(f"Вы: {prompt}", color="white70"))
        page.update()

        # Запрос к ИИ
        system_msg = "Ты Стела. Команды: [MUSIC] Трек, [DOC] Заголовок | Текст, [SEARCH] Запрос."
        try:
            completion = ai_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "system", "content": system_msg}, {"role": "user", "content": prompt}]
            )
            res_ai = completion.choices.message.content
        except: res_ai = "Ошибка связи с мозгом."

        # Обработка команд
        if "[SEARCH]" in res_ai:
            q = res_ai.replace("[SEARCH]", "").strip()
            res_ai = f"Результат поиска: {web_search(q)[:200]}..."
        
        elif "[MUSIC]" in res_ai:
            q = res_ai.replace("[MUSIC]", "").strip()
            search = y_client.search(q)
            if search.tracks and search.tracks.results:
                track = search.tracks.results[0]
                audio_player.src = track.get_download_info(get_direct_links=True)[0].direct_link
                audio_player.play()
                res_ai = f"Играет: {track.title}"

        elif "[DOC]" in res_ai:
            parts = res_ai.replace("[DOC]", "").split("|")
            title = parts[0].strip() if parts else "Документ"
            content = parts[1].strip() if len(parts) > 1 else "..."
            fname = create_file("DOC", title, content)
            res_ai = f"Файл {fname} создан (сохранен на сервере)."

        chat_log.controls.append(ft.Text(f"Стела: {res_ai}", color=accent))
        sphere.scale = 1.0
        page.update()

    # --- ВКЛАДКИ ---
    chat_tab = ft.Column([
        ft.Center(sphere),
        ft.Container(chat_log, padding=10, bgcolor="#111111", border_radius=10),
        ft.Row([input_f, ft.IconButton(ft.icons.SEND, on_click=run_logic, icon_color=accent)])
    ])

    async def save_settings(e):
        new_settings = {"bg_color": cp_bg.value, "accent_color": cp_acc.value}
        if supabase:
            supabase.table("stela_users").upsert({"user_id": user_id, **new_settings}).execute()
        page.bgcolor = cp_bg.value
        page.update()

    cp_bg = ft.TextField(label="Цвет фона (HEX)", value=page.bgcolor)
    cp_acc = ft.TextField(label="Цвет акцента", value=accent)
    
    settings_tab = ft.Column([
        ft.Text("НАСТРОЙКИ ВИДА", size=20, color=accent),
        cp_bg, cp_acc,
        ft.ElevatedButton("СОХРАНИТЬ", on_click=save_settings, bgcolor=accent, color="black")
    ], scroll=ft.ScrollMode.AUTO)

    tabs = ft.Tabs(
        selected_index=0,
        tabs=[
            ft.Tab(text="Чат", content=chat_tab),
            ft.Tab(text="Настройки", content=settings_tab)
        ], expand=1
    )

    page.add(tabs)

# --- ЗАПУСК ---
if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    ft.app(target=main_flet, view=ft.AppView.WEB_BROWSER, host="0.0.0.0", port=port)
