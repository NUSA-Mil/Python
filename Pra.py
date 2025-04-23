import aiohttp
import asyncio
import tkinter as tk
from tkinter import ttk, messagebox
from io import BytesIO
from PIL import Image, ImageTk
from urllib.parse import quote

# Настройки API
API_NINJAS_KEY = "3phhsZS2a04JcTWNfWCgDw==WqQ23oxQVceXAJ92"
WEATHER_API = "https://wttr.in/{}_0tqp_lang=ru.png"
QUOTES_API = "https://api.api-ninjas.com/v1/quotes"


class WeatherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Weather & Quotes")
        self.root.geometry("800x600")

        # Создаем интерфейс
        self.create_widgets()

    def create_widgets(self):
        # Ввод города
        self.city_frame = ttk.Frame(self.root)
        self.city_frame.pack(pady=10)

        ttk.Label(self.city_frame, text="Введите город:").pack(side=tk.LEFT)
        self.city_entry = ttk.Entry(self.city_frame, width=30)
        self.city_entry.pack(side=tk.LEFT, padx=5)
        self.city_entry.bind("<Return>", lambda e: self.update_data())

        # Кнопка обновления
        self.update_btn = ttk.Button(self.root, text="Обновить", command=self.update_data)
        self.update_btn.pack(pady=5)

        # Вкладки
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Вкладка погоды
        self.weather_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.weather_tab, text="Погода")

        # Вкладка цитат
        self.quotes_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.quotes_tab, text="Цитаты")

        # Карта погоды
        self.weather_map = ttk.Label(self.weather_tab)
        self.weather_map.pack(pady=10)

        # Информация о погоде
        self.weather_info = ttk.Label(self.weather_tab, font=('Arial', 12))
        self.weather_info.pack()

        # Цитата
        self.quote_text = tk.Text(self.quotes_tab, wrap=tk.WORD, height=10, width=60, font=('Arial', 12))
        self.quote_text.pack(pady=20, padx=10)
        self.quote_author = ttk.Label(self.quotes_tab, font=('Arial', 10, 'italic'))
        self.quote_author.pack()

    async def fetch_weather_map(self, city):
        """Загружает карту погоды"""
        try:
            url = WEATHER_API.format(quote(city))
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        image_data = await response.read()
                        return image_data
                    return None
        except Exception as e:
            print(f"Ошибка загрузки карты: {e}")
            return None

    async def fetch_quote(self):
        """Получает цитату"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(QUOTES_API, headers={"X-Api-Key": API_NINJAS_KEY}) as response:
                    if response.status == 200:
                        return await response.json()
                    return None
        except Exception as e:
            print(f"Ошибка загрузки цитаты: {e}")
            return None

    def update_data(self):
        """Обновляет все данные"""
        city = self.city_entry.get()
        if not city:
            messagebox.showerror("Ошибка", "Введите город")
            return

        async def update():
            # Показываем индикатор загрузки
            self.update_btn.config(text="Загрузка...", state=tk.DISABLED)

            # Загружаем данные асинхронно
            map_data, quote_data = await asyncio.gather(
                self.fetch_weather_map(city),
                self.fetch_quote()
            )

            # Обновляем интерфейс
            self.root.after(0, lambda: self.update_ui(city, map_data, quote_data))

        asyncio.create_task(update())

    def update_ui(self, city, map_data, quote_data):
        """Обновляет интерфейс с новыми данными"""
        try:
            # Обновляем карту погоды
            if map_data:
                image = Image.open(BytesIO(map_data))
                image = image.resize((600, 400), Image.LANCZOS)
                photo = ImageTk.PhotoImage(image)
                self.weather_map.config(image=photo)
                self.weather_map.image = photo
            else:
                self.weather_map.config(text="Не удалось загрузить карту погоды")

            # Обновляем цитату
            if quote_data:
                quote = quote_data[0]
                self.quote_text.delete(1.0, tk.END)
                self.quote_text.insert(tk.END, quote['quote'])
                self.quote_author.config(text=f"— {quote['author']}")

            # Обновляем информацию о городе
            self.weather_info.config(text=f"Погода в {city}")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка обновления: {str(e)}")
        finally:
            self.update_btn.config(text="Обновить", state=tk.NORMAL)


if __name__ == "__main__":
    root = tk.Tk()
    app = WeatherApp(root)


    # Запускаем цикл событий asyncio
    async def run_tk():
        while True:
            root.update()
            await asyncio.sleep(0.05)


    asyncio.get_event_loop().run_until_complete(run_tk())