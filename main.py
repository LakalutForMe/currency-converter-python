import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import requests
import json
from threading import Thread
import time
from abc import ABC, abstractmethod
from datetime import datetime
import os

# ========== АБСТРАКТНІ КЛАСИ ==========

class ExchangeRateProvider(ABC):
    """Абстрактний клас для отримання курсів валют"""
    
    @abstractmethod
    def get_exchange_rate(self, from_currency, to_currency):
        """Отримати курс обміну між валютами"""
        pass
    
    @abstractmethod
    def get_all_rates(self):
        """Отримати всі доступні курси"""
        pass

# ========== КОНКРЕТНІ РЕАЛІЗАЦІЇ ПРОВАЙДЕРІВ ==========

class OnlineRateProvider(ExchangeRateProvider):
    """Отримує курси валют через API та кешує їх у файл"""
    CACHE_FILE = "exchange_rates_cache.json"

    def __init__(self):
        self.rates = {}
        self.base_currency = "USD"
        self.last_update = None

    def fetch_rates(self):
        """Завантажити курси з API та зберегти у кеш"""
        try:
            url = f"https://api.exchangerate-api.com/v4/latest/{self.base_currency}"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.rates = data['rates']
                self.last_update = datetime.now()
                # Зберігаємо у кеш
                self.save_cache()
                return True
        except Exception as e:
            print(f"Помилка завантаження курсів: {e}")
        return self.load_cache()

    def save_cache(self):
        """Зберегти курси у файл кешу"""
        try:
            cache_data = {
                "rates": self.rates,
                "base_currency": self.base_currency,
                "last_update": self.last_update.strftime("%Y-%m-%d %H:%M:%S") if self.last_update else ""
            }
            with open(self.CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(cache_data, f)
        except Exception as e:
            print(f"Помилка збереження кешу: {e}")

    def load_cache(self):
        """Завантажити курси з кешу"""
        try:
            if os.path.exists(self.CACHE_FILE):
                with open(self.CACHE_FILE, "r", encoding="utf-8") as f:
                    cache_data = json.load(f)
                    self.rates = cache_data.get("rates", {})
                    self.base_currency = cache_data.get("base_currency", "USD")
                    last_update_str = cache_data.get("last_update", "")
                    if last_update_str:
                        self.last_update = datetime.strptime(last_update_str, "%Y-%m-%d %H:%M:%S")
                    return bool(self.rates)
        except Exception as e:
            print(f"Помилка завантаження кешу: {e}")
        return False

    
    def get_exchange_rate(self, from_currency, to_currency):
        """Отримати курс обміну між двома валютами"""
        if not self.rates:
            return 0
            
        if from_currency == to_currency:
            return 1
            
        try:
            if from_currency == self.base_currency:
                return self.rates.get(to_currency, 0)
            elif to_currency == self.base_currency:
                from_rate = self.rates.get(from_currency, 0)
                return (1 / from_rate) if from_rate != 0 else 0
            else:
                from_rate = self.rates.get(from_currency, 0)
                to_rate = self.rates.get(to_currency, 0)
                if from_rate != 0 and to_rate != 0:
                    return to_rate / from_rate
        except (KeyError, ZeroDivisionError):
            pass
        return 0
    
    def get_all_rates(self):
        """Отримати всі курси"""
        return self.rates.copy()

class OfflineRateProvider(ExchangeRateProvider):
    """Використовує збережені (кешовані) курси валют з файлу"""
    CACHE_FILE = "exchange_rates_cache.json"

    def __init__(self):
        self.rates = self.load_cache()
        if not self.rates:
            # Якщо кешу немає, fallback на статичні курси
            self.rates = {
                "USD": 1.0, "EUR": 0.85, "UAH": 37.0, "GBP": 0.73,
                "JPY": 110.0, "CAD": 1.25, "AUD": 1.35, "CHF": 0.92,
                "CNY": 6.45, "SEK": 8.75, "NOK": 8.95, "PLN": 3.85,
                "CZK": 21.5, "TRY": 8.25, "RUB": 75.0
            }

    def load_cache(self):
        """Завантажити курси з кешу"""
        try:
            if os.path.exists(self.CACHE_FILE):
                with open(self.CACHE_FILE, "r", encoding="utf-8") as f:
                    cache_data = json.load(f)
                    return cache_data.get("rates", {})
        except Exception as e:
            print(f"Помилка завантаження кешу (офлайн): {e}")
        return {}
    
    def get_exchange_rate(self, from_currency, to_currency):
        """Отримати курс з кешованих даних"""
        if from_currency == to_currency:
            return 1
            
        from_rate = self.rates.get(from_currency, 0)
        to_rate = self.rates.get(to_currency, 0)
        
        if from_rate != 0 and to_rate != 0:
            return to_rate / from_rate
        return 0
    
    def get_all_rates(self):
        """Повернути всі кешовані курси"""
        return self.rates.copy()

# ========== МЕНЕДЖЕР ІСТОРІЇ ==========

class HistoryManager:
    """Клас для зберігання та перегляду історії конвертацій"""
    
    def __init__(self):
        self.history_list = []
    
    def save_entry(self, entry):
        """Зберегти новий запис в історію"""
        self.history_list.append(entry)
        # Обмежуємо історію до 50 записів
        if len(self.history_list) > 50:
            self.history_list.pop(0)
    
    def get_history(self):
        """Повернути список всіх записів"""
        return self.history_list.copy()
    
    def clear_history(self):
        """Очистити історію"""
        self.history_list.clear()

# ========== ОСНОВНИЙ КЛАС КОНВЕРТЕРА ==========

class CurrencyConverter:
    """Основний клас, що реалізує логіку конвертації валют"""
    
    def __init__(self, exchange_rate_provider=None, history_manager=None):
        self.exchange_rate_provider = exchange_rate_provider or OnlineRateProvider()
        self.history_manager = history_manager or HistoryManager()
        
        # Список валют з назвами
        self.currencies = {
            "USD": "Долар США", "EUR": "Євро", "UAH": "Українська гривня",
            "GBP": "Фунт стерлінгів", "JPY": "Японська єна", "CAD": "Канадський долар",
            "AUD": "Австралійський долар", "CHF": "Швейцарський франк", 
            "CNY": "Китайський юань", "SEK": "Шведська крона", "NOK": "Норвезька крона",
            "PLN": "Польський злотий", "CZK": "Чеська крона", 
            "TRY": "Турецька ліра"
        }
    
    def convert(self, amount, from_currency, to_currency):
        """Обчислити результат конвертації"""
        try:
            amount = float(amount)
            if amount < 0:
                return None, "Сума не може бути від'ємною"
            
            rate = self.get_exchange_rate(from_currency, to_currency)
            
            if rate <= 0:
                return None, "Не вдалося отримати курс валют"
            
            result = amount * rate
            
            # Зберігаємо в історію
            entry = {
                "timestamp": datetime.now().strftime("%d.%m.%Y %H:%M"),
                "amount": amount,
                "from_currency": from_currency,
                "to_currency": to_currency,
                "rate": rate,
                "result": result
            }
            self.history_manager.save_entry(entry)
            
            return result, None
            
        except ValueError:
            return None, "Некоректне значення суми"
        except Exception as e:
            return None, f"Помилка конвертації: {str(e)}"
    
    def get_exchange_rate(self, from_currency, to_currency):
        """Отримати курс обміну"""
        return self.exchange_rate_provider.get_exchange_rate(from_currency, to_currency)

# ========== ІНТЕРФЕЙС КОРИСТУВАЧА ==========

class UserInterface:
    """Клас для взаємодії з користувачем через графічний інтерфейс"""
    
    def __init__(self, converter):
        self.converter = converter
        self.window = tk.Tk()
        self.setup_window()
        self.create_widgets()
        self.updating_from_code = False
        
        # Запускаємо завантаження курсів
        self.refresh_rates()
        self.auto_update_rates()
    
    def setup_window(self):
        """Налаштування головного вікна"""
        self.window.title("💱 Конвертер Валют")
        self.window.geometry("500x600")
        self.window.configure(bg='#1a1a2e')
        self.window.resizable(False, False)
    
    def create_widgets(self):
        """Створення елементів інтерфейсу"""
        # Головний фрейм
        main_frame = tk.Frame(self.window, bg='#1a1a2e', padx=25, pady=20)
        main_frame.pack(fill='both', expand=True)
        
        # Заголовок
        title_label = tk.Label(
            main_frame, 
            text="💱 Конвертер Валют", 
            font=('Segoe UI', 20, 'bold'),
            bg='#1a1a2e', 
            fg='#4a90e2'
        )
        title_label.pack(pady=(0, 10))
        
        # Статус курсів
        self.rate_label = tk.Label(
            main_frame,
            text="Завантаження курсів валют...",
            font=('Segoe UI', 10),
            bg='#1a1a2e',
            fg='#6bb6ff'
        )
        self.rate_label.pack(pady=(0, 5))
        
        self.update_label = tk.Label(
            main_frame,
            text="",
            font=('Segoe UI', 8),
            bg='#1a1a2e',
            fg='#888888'
        )
        self.update_label.pack(pady=(0, 15))
        
        # Фрейм конвертації
        self.create_conversion_frame(main_frame)
        
        # Кнопки управління
        self.create_control_buttons(main_frame)
        
        # Історія конвертацій
        self.create_history_frame(main_frame)
        
        # Статус
        self.status_label = tk.Label(
            main_frame,
            text="Готово до роботи",
            font=('Segoe UI', 9),
            bg='#1a1a2e',
            fg='#4CAF50'
        )
        self.status_label.pack(pady=(10, 0))
    
    def create_conversion_frame(self, parent):
        """Створити фрейм для конвертації"""
        convert_frame = tk.Frame(parent, bg='#16213e', relief='flat', bd=2)
        convert_frame.pack(fill='x', pady=10, padx=10)
        convert_frame_inner = tk.Frame(convert_frame, bg='#16213e', padx=20, pady=15)
        convert_frame_inner.pack(fill='both', expand=True)
        
        # Перша валюта
        from_label = tk.Label(convert_frame_inner, text="З валюти:", font=('Segoe UI', 10, 'bold'),
                             bg='#16213e', fg='#e94560')
        from_label.pack(anchor='w')
        
        from_frame = tk.Frame(convert_frame_inner, bg='#16213e')
        from_frame.pack(fill='x', pady=(5, 10))
        
        self.amount1_var = tk.StringVar(value="1")
        self.amount1_entry = tk.Entry(from_frame, textvariable=self.amount1_var,
                                     font=('Segoe UI', 12), bg='#0f3460', fg='white',
                                     insertbackground='#e94560', relief='flat', bd=5, width=12)
        self.amount1_entry.pack(side='left', padx=(0, 10))
        self.amount1_entry.bind('<KeyRelease>', self.on_amount1_change)
        
        currency_list = [f"{code} - {name}" for code, name in self.converter.currencies.items()]
        
        self.from_dropdown = ttk.Combobox(from_frame, values=currency_list, state='readonly',
                                         font=('Segoe UI', 10), width=25)
        self.from_dropdown.current(2)  # UAH
        self.from_dropdown.pack(side='left')
        self.from_dropdown.bind('<<ComboboxSelected>>', self.on_currency_change)
        
        # Кнопка обміну
        swap_btn = tk.Button(convert_frame_inner, text="⇄", command=self.swap_currencies,
                            bg='#e94560', fg='white', font=('Segoe UI', 14, 'bold'),
                            relief='flat', width=3, height=1, cursor='hand2')
        swap_btn.pack(pady=5)
        
        # Друга валюта
        to_label = tk.Label(convert_frame_inner, text="В валюту:", font=('Segoe UI', 10, 'bold'),
                           bg='#16213e', fg='#e94560')
        to_label.pack(anchor='w')
        
        to_frame = tk.Frame(convert_frame_inner, bg='#16213e')
        to_frame.pack(fill='x', pady=5)
        
        self.amount2_var = tk.StringVar(value="0")
        self.amount2_entry = tk.Entry(to_frame, textvariable=self.amount2_var,
                                     font=('Segoe UI', 12), bg='#0f3460', fg='white',
                                     insertbackground='#e94560', relief='flat', bd=5, width=12)
        self.amount2_entry.pack(side='left', padx=(0, 10))
        self.amount2_entry.bind('<KeyRelease>', self.on_amount2_change)
        
        self.to_dropdown = ttk.Combobox(to_frame, values=currency_list, state='readonly',
                                       font=('Segoe UI', 10), width=25)
        self.to_dropdown.current(1)  # EUR
        self.to_dropdown.pack(side='left')
        self.to_dropdown.bind('<<ComboboxSelected>>', self.on_currency_change)
    
    def create_control_buttons(self, parent):
        """Створити кнопки управління"""
        buttons_frame = tk.Frame(parent, bg='#1a1a2e')
        buttons_frame.pack(pady=15)
        
        refresh_btn = tk.Button(buttons_frame, text="🔄 Оновити курси", command=self.refresh_rates,
                               bg='#e94560', fg='white', font=('Segoe UI', 10, 'bold'),
                               relief='flat', padx=15, pady=6, cursor='hand2')
        refresh_btn.pack(side='left', padx=(0, 8))
        
        clear_btn = tk.Button(buttons_frame, text="🗑️ Очистити", command=self.clear_fields,
                             bg='#0f3460', fg='white', font=('Segoe UI', 10, 'bold'),
                             relief='flat', padx=15, pady=6, cursor='hand2')
        clear_btn.pack(side='left', padx=(0, 8))
        
        offline_btn = tk.Button(buttons_frame, text="📱 Офлайн режим", command=self.toggle_offline_mode,
                               bg='#4CAF50', fg='white', font=('Segoe UI', 10, 'bold'),
                               relief='flat', padx=15, pady=6, cursor='hand2')
        offline_btn.pack(side='left')
    
    def create_history_frame(self, parent):
        """Створити фрейм для історії"""
        history_frame = tk.LabelFrame(parent, text="📋 Історія конвертацій", 
                                     font=('Segoe UI', 10, 'bold'), bg='#1a1a2e', 
                                     fg='#4a90e2', bd=1, relief='solid')
        history_frame.pack(fill='both', expand=True, pady=(10, 0))
        
        # Текстове поле для історії
        self.history_text = scrolledtext.ScrolledText(
            history_frame, height=8, bg='#0f3460', fg='white',
            font=('Consolas', 9), relief='flat', bd=5,
            insertbackground='white'
        )
        self.history_text.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Кнопка очищення історії
        clear_history_btn = tk.Button(
            history_frame, text="🗑️ Очистити історію",
            command=self.clear_history, bg='#FF5722', fg='white',
            font=('Segoe UI', 9), relief='flat', pady=3
        )
        clear_history_btn.pack(pady=(0, 5))
    
    def get_selected_currency_code(self, dropdown_value):
        """Отримати код валюти з вибраного значення"""
        return dropdown_value.split(" - ")[0] if " - " in dropdown_value else dropdown_value
    
    def on_amount1_change(self, event=None):
        """Обробка зміни першої суми"""
        if not self.updating_from_code:
            self.update_conversion(direction="forward")
    
    def on_amount2_change(self, event=None):
        """Обробка зміни другої суми"""
        if not self.updating_from_code:
            self.update_conversion(direction="backward")
    
    def on_currency_change(self, event=None):
        """Обробка зміни валют"""
        self.update_conversion(direction="forward")
    
    def update_conversion(self, direction="forward"):
        """Оновити конвертацію"""
        try:
            from_curr = self.get_selected_currency_code(self.from_dropdown.get())
            to_curr = self.get_selected_currency_code(self.to_dropdown.get())
            
            if direction == "forward":
                amount = self.amount1_var.get()
                result, error = self.converter.convert(amount, from_curr, to_curr)
                
                if error:
                    self.show_error(error)
                    return
                
                self.updating_from_code = True
                self.amount2_var.set(f"{result:.6f}".rstrip('0').rstrip('.') if result != 0 else "0")
                self.updating_from_code = False
                
            else:  # backward
                amount = self.amount2_var.get()
                result, error = self.converter.convert(amount, to_curr, from_curr)
                
                if error:
                    self.show_error(error)
                    return
                
                self.updating_from_code = True
                self.amount1_var.set(f"{result:.6f}".rstrip('0').rstrip('.') if result != 0 else "0")
                self.updating_from_code = False
            
            # Оновити відображення курсу
            rate = self.converter.get_exchange_rate(from_curr, to_curr)
            if rate > 0:
                self.rate_label.config(
                    text=f"1 {self.converter.currencies.get(from_curr, from_curr)} = "
                         f"{rate:.6f}".rstrip('0').rstrip('.') + 
                         f" {self.converter.currencies.get(to_curr, to_curr)}"
                )
            
            # Оновити історію
            self.update_history_display()
            
        except Exception as e:
            self.show_error(f"Помилка обчислення: {str(e)}")
    
    def swap_currencies(self):
        """Поміняти валюти місцями"""
        from_idx = self.from_dropdown.current()
        to_idx = self.to_dropdown.current()
        amount1 = self.amount1_var.get()
        amount2 = self.amount2_var.get()
        
        self.from_dropdown.current(to_idx)
        self.to_dropdown.current(from_idx)
        self.amount1_var.set(amount2)
        self.amount2_var.set(amount1)
    
    def clear_fields(self):
        """Очистити поля вводу"""
        self.amount1_var.set("0")
        self.amount2_var.set("0")
    
    def refresh_rates(self):
        """Оновити курси валют"""
        def update():
            if isinstance(self.converter.exchange_rate_provider, OnlineRateProvider):
                self.status_label.config(text="Оновлення курсів...", fg='#FFA500')
                success = self.converter.exchange_rate_provider.fetch_rates()
                
                if success:
                    self.window.after(0, lambda: self.status_label.config(text="Курси оновлено", fg='#4CAF50'))
                    timestamp = self.converter.exchange_rate_provider.last_update
                    if timestamp:
                        self.window.after(0, lambda: self.update_label.config(
                            text=f"Останнє оновлення: {timestamp.strftime('%d.%m.%Y %H:%M')}"
                        ))
                else:
                    self.window.after(0, lambda: self.status_label.config(text="Помилка оновлення", fg='#FF5722'))
        
        Thread(target=update, daemon=True).start()
    
    def toggle_offline_mode(self):
        """Перемикання між онлайн та офлайн режимами"""
        if isinstance(self.converter.exchange_rate_provider, OnlineRateProvider):
            self.converter.exchange_rate_provider = OfflineRateProvider()
            self.status_label.config(text="Офлайн режим активний", fg='#FFA500')
            self.update_label.config(text="Використовуються збережені курси")
            # Змінюємо текст кнопки на "Онлайн режим"
            for widget in self.window.winfo_children():
                for child in widget.winfo_children():
                    if isinstance(child, tk.Button) and "Офлайн режим" in child.cget("text"):
                        child.config(text="🌐 Онлайн режим")
        else:
            self.converter.exchange_rate_provider = OnlineRateProvider()
            self.status_label.config(text="Онлайн режим активний", fg='#4CAF50')
            self.refresh_rates()
            # Змінюємо текст кнопки на "Офлайн режим"
            for widget in self.window.winfo_children():
                for child in widget.winfo_children():
                    if isinstance(child, tk.Button) and "Онлайн режим" in child.cget("text"):
                        child.config(text="📱 Офлайн режим")
    
    def auto_update_rates(self):
        """Автоматичне оновлення курсів"""
        def update_loop():
            while True:
                time.sleep(300)  # 5 хвилин
                if (self.window.winfo_exists() and 
                    isinstance(self.converter.exchange_rate_provider, OnlineRateProvider)):
                    self.refresh_rates()
                else:
                    break
        
        Thread(target=update_loop, daemon=True).start()
    
    def update_history_display(self):
        """Оновити відображення історії"""
        history = self.converter.history_manager.get_history()
        self.history_text.delete(1.0, tk.END)
        
        for entry in reversed(history[-10:]):  # Показуємо останні 10 записів
            line = (f"{entry['timestamp']} | "
                   f"{entry['amount']:.2f} {entry['from_currency']} → "
                   f"{entry['result']:.4f} {entry['to_currency']} "
                   f"(курс: {entry['rate']:.4f})\n")
            self.history_text.insert(tk.END, line)
    
    def clear_history(self):
        """Очистити історію"""
        self.converter.history_manager.clear_history()
        self.history_text.delete(1.0, tk.END)
        self.status_label.config(text="Історію очищено", fg='#4CAF50')
    
    def show_result(self, result):
        """Показати результат конвертації"""
        self.status_label.config(text=f"Результат: {result}", fg='#4CAF50')
    
    def show_error(self, error_message):
        """Показати повідомлення про помилку"""
        self.status_label.config(text=error_message, fg='#FF5722')
    
    def run(self):
        """Запустити інтерфейс"""
        self.window.mainloop()

# ========== ГОЛОВНА ФУНКЦІЯ ==========

def main():
    """Головна функція для запуску програми"""
    # Створюємо компоненти
    online_provider = OnlineRateProvider()
    history_manager = HistoryManager()
    converter = CurrencyConverter(online_provider, history_manager)
    
    # Запускаємо інтерфейс
    ui = UserInterface(converter)
    ui.run()

if __name__ == "__main__":
    main()