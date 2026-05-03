import os
import asyncio
import logging
import flet as ft
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from groq import Groq
from yandex_music import Client

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
YANDEX_TOKEN = os.getenv("YANDEX_TOKEN")
RENDER_URL = "https://onrender.com"

logging.basicConfig(level=logging.INFO)

# Инициализация сервисов
ai_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
y_client = Client(YANDEX_TOKEN).init() if YANDEX_TOKEN else None
bot = Bot(token=TELEGRAM_TOKEN) if TELEGRAM_TOKEN else None
dp = Dispatcher()

# --- МОЗГ СТЕЛЫ ---
async def get_stela_logic(prompt):
    if not ai_client: return "Ключи не настроены."
    def sync_ai():
        try:
            system_prompt = (
                "Ты — Стела, продвинутый ИИ-ассистент. Если тебя просят включить музыку, "
                "ответь строго по шаблону: [MUSIC] Исполнитель - Трек. "
                "В остальных случаях отвечай кратко, мудро и с характером."
            )
            completion = ai_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}]
            )
            return completion.choices[0].message.content
        except: return "Произошел сбой в нейронных связях."
    return await asyncio.get_event_loop().run_in_executor(None, sync_ai)

# --- ИНТЕРФЕЙС (FULL TUNING) ---
async def main_flet(page: ft.Page):
    page.title = "Stela OS"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#000000"
    page.padding = 20
    page.vertical_alignment = "center"
    page.horizontal_alignment = "center"

    # Аудио-плеер
    audio_player = ft.Audio(src="", autoplay=True)
    page.overlay.append(audio_player)

    # Визуальный центр (Сфера)
    sphere_icon = ft.Icon(ft.icons.AUTO_AWESOME, size=60, color="cyan200", animate_rotation=300)
    sphere = ft.Container(
        content=sphere_icon,
        width=180, height=180, shape="circle",
        gradient=ft.RadialGradient(colors=["#1a237e", "black"]),
        shadow=ft.BoxShadow(blur_radius=60, color="blue900", spread_radius=1),
        animate_scale=400,
        animate=ft.animation.Animation(1000, ft.AnimationCurve.EASE_IN_OUT),
    )

    # Зона текста с прокруткой (Стеклянный эффект)
    status_text = ft.Text("СИСТЕМА ГОТОВА", size=14, color="cyan100", text_align="center")
    response_area = ft.Container(
        content=ft.Column(
            [status_text], 
            scroll=ft.ScrollMode.ADAPTIVE, 
            horizontal_alignment="center",
            spacing=10
        ),
        padding=15,
        width=320,
        height=180,
        border_radius=20,
        bgcolor=ft.colors.with_opacity(0.1, "white"),
        border=ft.border.all(1, ft.colors.with_opacity(0.2, "white")),
    )

    # Поле ввода
    input_f = ft.TextField(
        label="Запрос к Stela OS...",
        width=300,
        border_radius=15,
        border_color="blue900",
        focused_border_color="cyan400",
        on_submit=lambda _: handle_action(None)
    )

    async def handle_action(e):
        if not input_f.value: return
        
        prompt = input_f.value
        input_f.value = ""
        status_text.value = "АНАЛИЗ ЗАПРОСА..."
        sphere.scale = 1.15
        sphere.shadow.color = "cyan700"
        page.update()

        ai_res = await get_stela_logic(prompt)

        # ЛОГИКА МУЗЫКИ
        if "[MUSIC]" in ai_res and y_client:
            query = ai_res.replace("[MUSIC]", "").strip()
            search = y_client.search(query)
            if search.tracks and search.tracks.results:
                track = search.tracks.results[0]
                status_text.value = f"PLAYING:\n{track.title}\n{track.artists[0].name}"
                
                # Обложка
                if track.cover_uri:
                    img_url = f"https://{track.cover_uri.replace('%%', '400x400')}"
                    sphere.content = ft.Image(src=img_url, border_radius=90, fit="cover")
                
                # Поток
                try:
                    info = track.get_download_info(get_direct_links=True)
                    audio_player.src = info[0].direct_link
                    audio_player.play()
                except: status_text.value = "ОШИБКА ПОТОКА"
            else:
                status_text.value = "ТРЕК НЕ НАЙДЕН В БАЗЕ"
        else:
            # Обычный разговор
            status_text.value = ai_res
            sphere.content = ft.Icon(ft.icons.AUTO_AWESOME, size=60, color="cyan200")
            if page.tts: page.tts.say(ai_res)

        sphere.scale = 1.0
        sphere.shadow.color = "blue900"
        page.update()

    page.add(
        sphere,
        ft.Container(height=30),
        response_area,
        ft.Container(height=20),
        input_f,
        ft.ElevatedButton(
            "ВЫПОЛНИТЬ", 
            on_click=handle_action,
            style=ft.ButtonStyle(bgcolor="blue900", color="white", shape=ft.RoundedRectangleBorder(radius=10))
        )
    )

# --- BOT LAUNCH ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="STELA OS [LAUNCH]", web_app=WebAppInfo(url=RENDER_URL))]
    ])
    await message.answer("Stela OS инициализирована. Ожидаю команд.", reply_markup=markup)

async def start_all():
    if bot: asyncio.create_task(dp.start_polling(bot))
    await ft.app_async(target=main_flet, view=ft.AppView.WEB_BROWSER, port=int(os.getenv("PORT", 10000)), host="0.0.0.0")

if __name__ == "__main__":
    asyncio.run(start_all())
