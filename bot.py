import logging
import json
import datetime
import os
from telebot import TeleBot, types
from telebot.custom_filters import TextFilter
import telebot.util

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфигурация
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8476080850:AAHBhfAUmgbnNlhmfSS1n6fw4lqMk9xK6a8')
ADMIN_IDS = [986688734, 5412048228, 901147670, 5082760438]  # Замени на свой ID

bot = TeleBot(BOT_TOKEN)

# Файл для хранения данных
DATA_FILE = "library_data.json"

# Загрузка данных
def load_data():
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"books": {}}

# Сохранение данных
def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# Клавиатуры
def get_main_keyboard(is_admin=False):
    if is_admin:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row("📚 Взять книгу", "📖 Вернуть книгу")
        markup.row("🔍 Поиск книг", "⭐ Оценить книгу") 
        markup.row("📋 Все книги", "📅 Мои книги")
        markup.row("➕ Добавить книгу", "🗑️ Удалить книгу")
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row("📚 Взять книгу", "📖 Вернуть книгу")
        markup.row("🔍 Поиск книг", "⭐ Оценить книгу")
        markup.row("📋 Все книги", "📅 Мои книги")
    markup.row("❌ Отмена")
    return markup

def get_cancel_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("❌ Отмена")
    return markup

# Команда /start
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    is_admin = user_id in ADMIN_IDS
    
    if is_admin:
        welcome_text = "👑 Здравствуйте, вы вошли как админ!"
    else:
        welcome_text = "📚 Здравствуйте, у нас есть много книг!"
    
    bot.send_message(message.chat.id, welcome_text, reply_markup=get_main_keyboard(is_admin))

# Обработка кнопки "Все книги"
@bot.message_handler(func=lambda message: message.text == "📋 Все книги")
def all_books(message):
    data = load_data()
    
    if not data["books"]:
        bot.send_message(message.chat.id, "📚 В библиотеке пока нет книг.")
        return
    
    books_text = "📚 Список всех книг:\n\n"
    
    for book_name, book_info in data["books"].items():
        books_text += f"📖 {book_name}\n"
        if book_info.get("author"):
            books_text += f"   ✍️ Автор: {book_info['author']}\n"
        
        if book_info.get("taken"):
            books_text += f"   ❌ Занята\n"
            books_text += f"   👤 У: {book_info.get('taken_by', 'Неизвестно')}\n"
            books_text += f"   📅 До: {book_info.get('due_date', 'Не указано')}\n"
        else:
            books_text += f"   ✅ Доступна\n"
            books_text += f"   🏢 Место: {book_info.get('location', 'Не указано')}\n"
        books_text += "\n"
    
    bot.send_message(message.chat.id, books_text)

# Обработка кнопки "Отмена"
@bot.message_handler(func=lambda message: message.text == "❌ Отмена")
def cancel(message):
    user_id = message.from_user.id
    is_admin = user_id in ADMIN_IDS
    bot.send_message(message.chat.id, "❌ Действие отменено", reply_markup=get_main_keyboard(is_admin))

# Запуск бота
if __name__ == "__main__":
    print("Бот запущен...")
    bot.infinity_polling()

