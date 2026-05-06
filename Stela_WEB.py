import os
import asyncio
import logging
import flet as ft
from groq import Groq
from yandex_music import Client as YandexClient
from docx import Document
from pptx import Presentation
from duckduckgo_search import DDGS
from urllib.parse import urlparse, parse_qs

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# --- ИНИЦИАЛИЗАЦИЯ СЕРВИСОВ ---
def init_services():
    try:
        ai = Groq(api_key=os.getenv("GROQ_API_KEY"))
        y_token = os.getenv("YANDEX_TOKEN")
        y_client = YandexClient(y_token).init() if y_token else None
        return ai, y_client
    except Exception as e:
        logging.error(f"Ошибка инициализации сервисов: {e}")
        return None, None

ai_client, y_client = init_services()

# --- ФУНКЦИИ ИНСТРУМЕНТОВ ---
def web_search(query):
    try:
        with DDGS() as ddgs:
            results = [r['body'] for r in ddgs.text(query, max_results=2)]
            return "\n".join(results)
    except:
        return "Поиск временно недоступен."

def create_file(mode, title, content):
    fname = f"/tmp/{title}.docx" if mode == "DOC" else f"/tmp/{title}.pptx"
    try:
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
    except Exception as e:
        return f"Ошибка файла: {e}"

# --- ГЛАВНЫЙ ИНТЕРФЕЙС ---
async def main_flet(page: ft.Page):
    await asyncio.sleep(0.5)
    user_id = "guest"
    try:
        if page.route:
            parsed = urlparse(page.route)
            params = parse_qs(parsed.query)
            user_id = params.get("user_id", ["guest"])[0]
    except:
        pass

    page.title = "Stela OS"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#050505"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    accent = "cyan"

    # АУДИО
    audio_player = ft.Audio(src="https://", autoplay=True)
    page.overlay.append(audio_player)

    # ВИЗУАЛ
    sphere = ft.Container(
        content=ft.Icon(ft.icons.AUTO_AWESOME_MOTION, size=70, color=accent),
        width=140, height=140, shape=ft.BoxShape.CIRCLE,
        shadow=ft.BoxShadow(blur_radius=40, color=accent),
        animate_scale=ft.animation.Animation(400, "easeInOut"),
    )

    chat_log = ft.Column(scroll=ft.ScrollMode.AUTO, height=300, spacing=10)
    input_f = ft.TextField(label="Команда...", border_color=accent, expand=True)

    async def run_cmd(e):
        txt = input_f.value
        if not txt: return
        input_f.value = ""
        sphere.scale = 1.2
        chat_log.controls.append(ft.Text(f"Вы: {txt}", color="white70"))
        page.update()

        res_ai = "Ошибка: Мозг ИИ не настроен."
        if ai_client:
            try:
                sys_msg = "Ты Стела. Команды: [MUSIC] Трек, [DOC] Заголовок|Текст, [SEARCH] Запрос."
                comp = ai_client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": txt}]
                )
                # ИСПРАВЛЕННАЯ СТРОКА ТУТ:
                res_ai = comp.choices[0].message.content
            except Exception as ex:
                res_ai = f"AI Error: {ex}"

        # Обработка команд
        if "[SEARCH]" in res_ai:
            q = res_ai.replace("[SEARCH]", "").strip()
            res_ai = f"Результат поиска: {web_search(q)[:250]}..."
        elif "[MUSIC]" in res_ai and y_client:
            try:
                q = res_ai.replace("[MUSIC]", "").strip()
                s = y_client.search(q)
                if s.tracks and s.tracks.results:
                    t = s.tracks.results[0]
                    audio_player.src = t.get_download_info(get_direct_links=True)[0].direct_link
                    audio_player.play()
                    res_ai = f"Играет: {t.title} - {t.artists[0].name}"
            except:
                res_ai = "Не удалось запустить этот трек."
        elif "[DOC]" in res_ai:
            p = res_ai.replace("[DOC]", "").split("|")
            fname = create_file("DOC", p[0].strip() if p else "Doc", p[1].strip() if len(p)>1 else "...")
            res_ai = f"Документ создан: {fname}"

        chat_log.controls.append(ft.Text(f"Стела: {res_ai}", color=accent))
        sphere.scale = 1.0
        page.update()

    # СБОРКА ЭКРАНА
    main_layout = ft.Column(
        controls=[
            ft.Container(content=sphere, alignment=ft.alignment.center),
            ft.Container(height=10),
            ft.Container(content=chat_log, padding=10, bgcolor="#111111", border_radius=15, width=350),
            ft.Container(content=ft.Row([input_f, ft.IconButton(ft.icons.SEND, on_click=run_cmd, icon_color=accent)]), width=350)
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        alignment=ft.MainAxisAlignment.CENTER,
        expand=True
    )

    page.add(main_layout)
    page.update()

# --- ЗАПУСК ---
if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    ft.app(target=main_flet, view=ft.AppView.WEB_BROWSER, web_renderer=ft.WebRenderer.HTML, host="0.0.0.0", port=port)
