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

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# --- ИНИЦИАЛИЗАЦИЯ СЕРВИСОВ ---
def init_services():
    try:
        ai = Groq(api_key=os.getenv("GROQ_API_KEY"))
        y_token = os.getenv("YANDEX_TOKEN")
        y_client = YandexClient(y_token).init() if y_token else None
        bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))
        return ai, y_client, bot
    except Exception as e:
        logging.error(f"Ошибка инициализации: {e}")
        return None, None, None

ai_client, y_client, bot = init_services()

# --- МОДУЛЬ ФАЙЛОВ ---
def create_file(title, content):
    # Очистка имени (защита от Error 36)
    clean_title = "".join([c for c in title if c.isalnum() or c in (' ', '_')]).strip()
    if not clean_title: clean_title = "Stela_Document"
    
    path = f"/tmp/{clean_title}.docx"
    try:
        doc = Document()
        doc.add_heading(clean_title, 0)
        doc.add_paragraph(content)
        doc.save(path)
        return path
    except Exception as e:
        logging.error(f"File Error: {e}")
        return None

# --- ИНТЕРФЕЙС ---
async def main_flet(page: ft.Page):
    await asyncio.sleep(0.5)
    
    # 1. ПОЛУЧЕНИЕ USER_ID (Исправлено для устранения 'chat not found')
    user_id = page.query_params.get("user_id")
    
    # Если зашли без ID в ссылке, берем твой личный ID из переменных Render
    if not user_id or user_id == "guest":
        user_id = os.getenv("MY_CHAT_ID")
        logging.info(f"Используется резервный ID: {user_id}")

    page.title = "Stela Premium OS"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#050505"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    accent = "cyan"

    # Аудио-плеер
    audio_player = ft.Audio(src="https://google.com", autoplay=False)
    page.overlay.append(audio_player)

    # Визуал: Сфера
    sphere = ft.Container(
        content=ft.Icon(ft.icons.AUTO_AWESOME_MOTION, size=70, color=accent),
        width=140, height=140, shape=ft.BoxShape.CIRCLE,
        shadow=ft.BoxShadow(blur_radius=40, color=accent),
        animate_scale=ft.animation.Animation(400, "easeInOut"),
    )

    chat_log = ft.Column(scroll=ft.ScrollMode.AUTO, height=350, spacing=10)
    input_f = ft.TextField(label="Команда Стеле...", border_color=accent, expand=True)

    async def run_stela(e):
        txt = input_f.value
        if not txt: return
        input_f.value = ""
        sphere.scale = 1.2
        chat_log.controls.append(ft.Text(f"➤ {txt}", color="white70"))
        page.update()

        # Запрос к ИИ
        res_ai = "Ошибка связи."
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
                    info = t.get_download_info(get_direct_links=True)[0]
                    audio_player.src = info.direct_link
                    audio_player.play()
                    res_ai = f"🎵 Играет: {t.title} - {t.artists[0].name}"
                else: res_ai = "Трек не найден."

            elif "[DOC]" in res_ai:
                content_raw = res_ai.replace("[DOC]", "").strip()
                if "|" in content_raw:
                    p = content_raw.split("|")
                    title, body = p[0].strip(), p[1].strip()
                else:
                    title, body = "Document", content_raw
                
                f_path = create_file(title, body)
                if f_path and user_id:
                    # ОТПРАВКА В TELEGRAM
                    await bot.send_document(chat_id=user_id, document=FSInputFile(f_path))
                    res_ai = f"✅ Файл '{title}' отправлен вам в Telegram!"
                    os.remove(f_path)
                else: res_ai = "❌ Ошибка: не найден чат для отправки или файл не создан."

            elif "[SEARCH]" in res_ai:
                with DDGS() as ddgs:
                    search_res = [r['body'] for r in ddgs.text(res_ai.replace("[SEARCH]", ""), max_results=1)]
                    res_ai = f"🔍 Нашла: {search_res[0]}" if search_res else "Ничего не нашла."
        
        except Exception as proc_err:
            res_ai = f"Ошибка команды: {proc_err}"

        chat_log.controls.append(ft.Text(f"Стела: {res_ai}", color=accent))
        sphere.scale = 1.0
        page.update()

    # Сборка UI
    main_layout = ft.Column(
        controls=[
            ft.Container(content=sphere, alignment=ft.alignment.center, padding=20),
            ft.Container(chat_log, padding=10, bgcolor="#111111", border_radius=15, width=350),
            ft.Row([input_f, ft.IconButton(ft.icons.SEND, on_click=run_stela, icon_color=accent)], width=350)
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
