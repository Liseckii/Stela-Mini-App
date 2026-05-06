import os
import asyncio
import logging
import flet as ft
# Правильные импорты для новых версий
from flet import Audio, animation, AnimationCurve
from supabase import create_client
from groq import Groq
from yandex_music import Client as YandexClient
from docx import Document
from pptx import Presentation
from duckduckgo_search import DDGS

# Логирование для отладки на Render
logging.basicConfig(level=logging.INFO)

# --- ИНИЦИАЛИЗАЦИЯ СЕРВИСОВ ---
def init_services():
    try:
        sb_url = os.getenv("SUPABASE_URL")
        sb_key = os.getenv("SUPABASE_KEY")
        supabase = create_client(sb_url, sb_key) if sb_url and sb_key else None
        
        ai_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        
        y_token = os.getenv("YANDEX_TOKEN")
        y_client = YandexClient(y_token).init() if y_token else None
        
        return supabase, ai_client, y_client
    except Exception as e:
        logging.error(f"Ошибка инициализации: {e}")
        return None, None, None

supabase, ai_client, y_client = init_services()

# --- ФУНКЦИИ ИНСТРУМЕНТОВ ---
def web_search(query):
    try:
        with DDGS() as ddgs:
            results = [r['body'] for r in ddgs.text(query, max_results=2)]
            return "\n".join(results)
    except: return "Поиск временно недоступен."

def create_file(mode, title, content):
    fname = f"{title}.docx" if mode == "DOC" else f"{title}.pptx"
    try:
        if mode == "DOC":
            doc = Document(); doc.add_heading(title, 0); doc.add_paragraph(content); doc.save(fname)
        else:
            prs = Presentation(); slide = prs.slides.add_slide(prs.slide_layouts[1])
            slide.shapes.title.text = title; slide.placeholders[1].text = content; prs.save(fname)
        return fname
    except Exception as e: return f"Ошибка файла: {e}"

# --- ГЛАВНЫЙ ИНТЕРФЕЙС ---
async def main_flet(page: ft.Page):
    # Безопасное получение параметров в 0.22.1
    user_id = "guest"
    if page.query_params:
        user_id = page.query_params.get("user_id", "guest")

    # Настройки страницы
    page.title = "Stela OS"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#050505"
    page.window_width = 400
    accent = "cyan"

    # Плеер
    audio_player = Audio(src="https://", autoplay=True)
    page.overlay.append(audio_player)

    # Анимированная сфера
    sphere = ft.Container(
        content=ft.Icon(ft.icons.AUTO_AWESOME_MOTION, size=80, color=accent),
        width=150, height=150, shape=ft.BoxShape.CIRCLE,
        shadow=ft.BoxShadow(blur_radius=50, color=accent),
        animate_scale=ft.animation.Animation(400, "easeInOut"),
    )

    chat_log = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=10)
    input_f = ft.TextField(label="Команда...", border_color=accent, expand=True, on_submit=lambda e: run_stela(e))

    async def run_stela(e):
        prompt = input_f.value
        if not prompt: return
        input_f.value = ""
        sphere.scale = 1.2
        chat_log.controls.append(ft.Text(f"Вы: {prompt}", color="white70"))
        page.update()

        # Логика ИИ
        res_ai = "Ошибка подключения ИИ."
        if ai_client:
            try:
                sys = "Ты Стела. Команды: [MUSIC] Трек, [DOC] Заголовок|Текст, [SEARCH] Запрос."
                comp = ai_client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "system", "content": sys}, {"role": "user", "content": prompt}]
                )
                res_ai = comp.choices.message.content
            except Exception as ex: res_ai = f"AI Error: {ex}"

        # Парсинг команд
        if "[SEARCH]" in res_ai:
            res_ai = f"Результат: {web_search(res_ai.replace('[SEARCH]', '').strip())[:300]}..."
        
        elif "[MUSIC]" in res_ai and y_client:
            query = res_ai.replace("[MUSIC]", "").strip()
            search = y_client.search(query)
            if search.tracks:
                track = search.tracks.results[0]
                audio_player.src = track.get_download_info(get_direct_links=True)[0].direct_link
                audio_player.play()
                res_ai = f"Слушаем: {track.title}"

        elif "[DOC]" in res_ai:
            p = res_ai.replace("[DOC]", "").split("|")
            fname = create_file("DOC", p[0].strip(), p[1].strip() if len(p)>1 else "...")
            res_ai = f"Файл {fname} создан."

        chat_log.controls.append(ft.Text(f"Стела: {res_ai}", color=accent))
        sphere.scale = 1.0
        page.update()

    # Вкладки
    tabs = ft.Tabs(
        selected_index=0,
        tabs=[
            ft.Tab(text="Чат", content=ft.Column([
                ft.Divider(height=20, color="transparent"),
                ft.Center(sphere),
                ft.Container(chat_log, height=350, padding=10, bgcolor="#111111", border_radius=15),
                ft.Row([input_f, ft.IconButton(ft.icons.SEND, on_click=run_stela, icon_color=accent)])
            ])),
            ft.Tab(text="Вид", content=ft.Column([
                ft.Text("Настройки темы появятся здесь", color="grey")
            ]))
        ], expand=1
    )

    page.add(tabs)

# --- ЗАПУСК (Оптимизировано для Render) ---
if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    ft.app(
        target=main_flet,
        view=ft.AppView.WEB_BROWSER,
        web_renderer=ft.WebRenderer.HTML, # Важно для мобильных устройств
        host="0.0.0.0",
        port=port
    )
