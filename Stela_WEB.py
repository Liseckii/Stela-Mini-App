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

logging.basicConfig(level=logging.INFO)

def init_services():
    try:
        ai = Groq(api_key=os.getenv("GROQ_API_KEY"))
        y_token = os.getenv("YANDEX_TOKEN")
        y_client = YandexClient(y_token).init() if y_token else None
        return ai, y_client
    except Exception as e:
        logging.error(f"Ошибка сервисов: {e}")
        return None, None

ai_client, y_client = init_services()

# --- ИСПРАВЛЕННАЯ ФУНКЦИЯ ФАЙЛОВ ---
def create_file(mode, title, content):
    # Очищаем заголовок от запрещенных символов
    clean_title = "".join([c for c in title if c.isalnum() or c in (' ', '_')]).strip()
    if not clean_title: clean_title = "Document"
    
    # Путь ТОЛЬКО в /tmp/
    fname = f"/tmp/{clean_title}.docx" if mode == "DOC" else f"/tmp/{clean_title}.pptx"
    
    try:
        if mode == "DOC":
            doc = Document()
            doc.add_heading(clean_title, 0)
            doc.add_paragraph(content)
            doc.save(fname)
        else:
            prs = Presentation()
            slide = prs.slides.add_slide(prs.slide_layouts[0])
            slide.shapes.title.text = clean_title
            slide.placeholders[1].text = content
            prs.save(fname)
        return fname
    except Exception as e:
        logging.error(f"File Error: {e}")
        return f"Ошибка: {str(e)}"

# --- ИНТЕРФЕЙС ---
async def main_flet(page: ft.Page):
    await asyncio.sleep(0.5)
    
    page.title = "Stela OS"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#050505"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    accent = "cyan"

    # Плеер с добавлением уведомления об ошибке
    audio_player = ft.Audio(src="", autoplay=True)
    page.overlay.append(audio_player)

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

        res_ai = "Ошибка ИИ"
        if ai_client:
            try:
                sys_msg = "Ты Стела. Команды: [MUSIC] Исполнитель - Трек, [DOC] Заголовок|Текст, [SEARCH] Запрос."
                comp = ai_client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": txt}]
                )
                res_ai = comp.choices[0].message.content
            except Exception as ex:
                res_ai = f"AI Error: {ex}"

        # Команда МУЗЫКА
        if "[MUSIC]" in res_ai and y_client:
            try:
                q = res_ai.replace("[MUSIC]", "").strip()
                s = y_client.search(q)
                if s.tracks and s.tracks.results:
                    track = s.tracks.results[0]
                    # Получаем ссылку на поток
                    info = track.get_download_info(get_direct_links=True)
                    audio_player.src = info[0].direct_link
                    audio_player.play()
                    res_ai = f"🎵 Играет: {track.title} - {track.artists[0].name}"
                else:
                    res_ai = "Трек не найден."
            except Exception as music_err:
                res_ai = f"Ошибка плеера: {music_err}"

        # Команда ДОКУМЕНТ
        elif "[DOC]" in res_ai:
            p = res_ai.replace("[DOC]", "").split("|")
            title = p[0].strip() if p[0] else "Doc"
            text = p[1].strip() if len(p) > 1 else "..."
            path = create_file("DOC", title, text)
            res_ai = f"📄 Файл создан: {path}"

        chat_log.controls.append(ft.Text(f"Стела: {res_ai}", color=accent))
        sphere.scale = 1.0
        page.update()

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

if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    ft.app(target=main_flet, view=ft.AppView.WEB_BROWSER, web_renderer=ft.WebRenderer.HTML, host="0.0.0.0", port=port)
