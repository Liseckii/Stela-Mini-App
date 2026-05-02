import flet as ft
from yandex_music import Client
import time
import os

# === НАСТРОЙКИ ===
TOKEN = 'y0__wgBELW5t-AIGN74BiDVoJKcFz_L8KNOw89vNCFujalfXUGXkQLI'

class StelaWeb:
    def __init__(self):
        try:
            self.client = Client(TOKEN).init()
            print("Яндекс.Музыка подключена")
        except:
            self.client = None
            print("Ошибка токена")

    def get_response(self, text):
        text = text.lower()
        if "включи" in text:
            query = text.replace("включи", "").strip()
            return f"Ищу трек: {query}"
        elif "привет" in text:
            return "Привет! Я Стела, твой мобильный ассистент."
        elif "время" in text:
            return f"Сейчас {time.strftime('%H:%M')}"
        return "Я пока не знаю такую команду, но я учусь!"

def main(page: ft.Page):
    page.title = "Stela AI Web"
    page.theme_mode = ft.ThemeMode.DARK
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    
    stela = StelaWeb()
    
    # Элементы интерфейса
    status = ft.Text("Нажми на микрофон", size=16, italic=True)
    chat_display = ft.Text("Готова к работе", size=20, weight="bold", text_align="center")
    
    # Функция озвучки (через браузер)
    tts = ft.TextToSpeech()
    page.overlay.append(tts)

    def on_result(e):
        if e.data:
            user_text = e.data
            chat_display.value = f"Вы: {user_text}"
            response = stela.get_response(user_text)
            
            # Ответ Стелы
            time.sleep(0.5)
            chat_display.value = f"Стела: {response}"
            tts.speak(response)
            page.update()

    stt = ft.SpeechToText(on_result=on_result)
    page.overlay.append(stt)

    def start_mic(e):
        stt.start()
        status.value = "Слушаю..."
        page.update()

    page.add(
        ft.Icon(ft.icons.AUTO_AWESOME, size=80, color=ft.colors.BLUE_400),
        ft.Text("СТЕЛА AI", size=40, weight="bold"),
        ft.Container(height=20),
        chat_display,
        status,
        ft.FloatingActionButton(icon=ft.icons.MIC, on_click=start_mic, bgcolor=ft.colors.BLUE_700),
    )

if __name__ == "__main__":
    # Явно указываем порт для Render
    port = int(os.environ.get("PORT", 8550))
    # Запускаем БЕЗ лишних команд, напрямую
    ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=port, host="0.0.0.0")
