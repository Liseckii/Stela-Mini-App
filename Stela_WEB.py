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

# Инициализация
ai_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
y_client = Client(YANDEX_TOKEN).init() if YANDEX_TOKEN else None
bot = Bot(token=TELEGRAM_TOKEN) if TELEGRAM_TOKEN else None
dp = Dispatcher()

async def get_stela_answer(prompt):
    if not ai_client: return "Ключ ИИ не настроен."
    loop = asyncio.get_event_loop()
    def sync_ai():
        completion = ai_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": "Ты Стела. Если просят музыку - отвечай 'Ищу трек: [название]'."}, 
                      {"role": "user", "content": prompt}],
        )
        return completion.choices.message.content
    return await loop.run_in_executor(None, sync_ai)

async def main_flet(page: ft.Page):
    page.title = "Стела ИИ"
    page.theme_mode = ft.ThemeMode.DARK
    page.vertical_alignment = "center"
    page.horizontal_alignment = "center"
    page.bgcolor = "#050505"

    # Визуализация
    sphere = ft.Container(
        content=ft.Icon(ft.icons.AUTO_AWESOME, size=60, color="cyan200"),
        width=160, height=160, shape="circle",
        gradient=ft.RadialGradient(colors=["blue900", "black"]),
        shadow=ft.BoxShadow(blur_radius=50, color="blue700"),
        animate_scale=400,
    )

    status = ft.Text("Стела готова", size=16, text_align="center")
    
    # Плеер (скрыт по умолчанию)
    music_player = ft.Column(visible=False, horizontal_alignment="center")
    track_title = ft.Text("", size=14, weight="bold")
    
    async def find_music(query):
        if not y_client: return
        search = y_client.search(query)
        if search.tracks:
            track = search.tracks.results[0]
            track_title.value = f"🎵 {track.title} - {track.artists[0].name}"
            music_player.visible = True
            page.update()
            # Здесь можно добавить логику проигрывания через ft.Audio

    async def process_command(text):
        if not text: return
        status.value = "Стела думает..."
        sphere.scale = 1.2
        page.update()
        
        answer = await get_stela_answer(text)
        
        if "Ищу трек:" in answer:
            query = answer.split("Ищу трек:")[1].strip()
            await find_music(query)
            status.value = f"Включаю {query}"
        else:
            status.value = answer
            if page.tts: page.tts.say(answer)
        
        sphere.scale = 1.0
        page.update()

    # Поле ввода и кнопки
    input_f = ft.TextField(label="Напиши или нажми микрофон", width=300, border_radius=20)
    
    # Кнопка микрофона (в Mini App работает как переключатель)
    mic_btn = ft.IconButton(
        icon=ft.icons.MIC_ROUNDED,
        icon_color="cyan400",
        icon_size=40,
        on_click=lambda _: setattr(input_f, "value", "Включи музыку для души") # Заглушка для теста
    )

    music_player.controls = [track_title, ft.ProgressBar(width=200, color="cyan400")]

    page.add(
        sphere,
        ft.Container(height=20),
        status,
        music_player,
        ft.Row([input_f, mic_btn], alignment="center"),
        ft.ElevatedButton("Спросить", on_click=lambda _: process_command(input_f.value))
    )

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Запустить Стелу 🎙", web_app=WebAppInfo(url=RENDER_URL))]
    ])
    await message.answer("Стела готова к музыке и общению!", reply_markup=markup)

async def start_all():
    if bot: asyncio.create_task(dp.start_polling(bot))
    await ft.app_async(target=main_flet, view=ft.AppView.WEB_BROWSER, port=int(os.getenv("PORT", 10000)), host="0.0.0.0")

if __name__ == "__main__":
    asyncio.run(start_all())
