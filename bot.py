import logging
import json
import datetime
import os
from telebot import TeleBot, types
import telebot

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

# Состояния пользователей
user_states = {}

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
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("📚 Взять книгу", "📖 Вернуть книгу")
        markup.add("🔍 Поиск книг", "⭐ Оценить книгу")
        markup.add("📋 Все книги", "📅 Мои книги")
        markup.add("📌 Забронировать", "➕ Добавить книгу")
        markup.add("🗑️ Удалить книгу")
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("📚 Взять книгу", "📖 Вернуть книгу")
        markup.add("🔍 Поиск книг", "⭐ Оценить книгу")
        markup.add("📋 Все книги", "📅 Мои книги")
        markup.add("📌 Забронировать")
    markup.add("❌ Отмена")
    return markup

def get_cancel_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("❌ Отмена")
    return markup

def get_rating_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    markup.add("1 ⭐", "2 ⭐⭐", "3 ⭐⭐⭐", "4 ⭐⭐⭐⭐", "5 ⭐⭐⭐⭐⭐")
    markup.add("❌ Отмена")
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

# Команда для отладки
@bot.message_handler(commands=['debug'])
def debug_info(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    username = message.from_user.username
    
    data = load_data()
    my_books = []
    
    for book_name, book_info in data["books"].items():
        if book_info.get("taken_by"):
            my_books.append(f"{book_name} -> {book_info['taken_by']}")
    
    debug_text = f"""
👤 Ваши данные:
ID: {user_id}
Имя: {first_name}
Юзернейм: {username}

📚 Все занятые книги:
{chr(10).join(my_books) if my_books else 'Нет занятых книг'}
"""
    bot.send_message(message.chat.id, debug_text)

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
    
    # Рейтинг
    ratings = book_info.get("ratings", {})
    if ratings:
        avg_rating = sum(ratings.values()) / len(ratings)
        books_text += f"   ⭐ Рейтинг: {avg_rating:.1f}/5\n"
    
    if book_info.get("taken"):
        books_text += f"   ❌ Занята\n"
        books_text += f"   👤 У: {book_info.get('taken_by', 'Неизвестно')}\n"
        books_text += f"   📅 До: {book_info.get('due_date', 'Не указано')}\n"
        if book_info.get("reserved"):
            books_text += f"   📌 Забронирована: {book_info.get('reserved_by', 'Кем-то')}\n"
    else:
        books_text += f"   ✅ Доступна\n"
        books_text += f"   🏢 Место: {book_info.get('location', 'Не указано')}\n"
    books_text += "\n"
    
    bot.send_message(message.chat.id, books_text)

# Обработка кнопки "Взять книгу"
@bot.message_handler(func=lambda message: message.text == "📚 Взять книгу")
def take_book_start(message):
    user_states[message.chat.id] = {'action': 'take_book', 'step': 'book_name'}
    bot.send_message(message.chat.id, "📖 Напишите название книги которую хотите взять:", reply_markup=get_cancel_keyboard())

# Обработка кнопки "Вернуть книгу"
@bot.message_handler(func=lambda message: message.text == "📖 Вернуть книгу")
def return_book_start(message):
    user_states[message.chat.id] = {'action': 'return_book', 'step': 'book_name'}
    bot.send_message(message.chat.id, "📖 Напишите название книги которую возвращаете:", reply_markup=get_cancel_keyboard())

# Обработка кнопки "Поиск книг"
@bot.message_handler(func=lambda message: message.text == "🔍 Поиск книг")
def search_books_start(message):
    user_states[message.chat.id] = {'action': 'search', 'step': 'query'}
    bot.send_message(message.chat.id, "🔍 Введите название книги или автора для поиска:", reply_markup=get_cancel_keyboard())

# Обработка кнопки "Оценить книгу"
@bot.message_handler(func=lambda message: message.text == "⭐ Оценить книгу")
def rate_book_start(message):
    data = load_data()
    
    if not data["books"]:
        bot.send_message(message.chat.id, "📚 В библиотеке пока нет книг для оценки.")
        return
    
    books_list = "\n".join([f"📖 {book}" for book in data["books"].keys()])
    user_states[message.chat.id] = {'action': 'rate_book', 'step': 'book_name'}
    bot.send_message(message.chat.id, f"⭐ Какую книгу хотите оценить?\n\n{books_list}", reply_markup=get_cancel_keyboard())

# Обработка кнопки "Мои книги"
@bot.message_handler(func=lambda message: message.text == "📅 Мои книги")
def my_books(message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    data = load_data()
    
    my_books_list = []
    
    # Ищем книги по ID пользователя (надежнее)
    for book_name, book_info in data["books"].items():
        # Проверяем по имени ИЛИ если добавили ID в будущем
        if (book_info.get("taken_by") == user_name or 
            str(book_info.get("taken_by_id")) == str(user_id)):
            my_books_list.append((book_name, book_info))
    
    if not my_books_list:
        # Покажем какие книги вообще заняты для отладки
        all_taken_books = []
        for book_name, book_info in data["books"].items():
            if book_info.get("taken"):
                all_taken_books.append(f"{book_name} -> {book_info.get('taken_by', 'Неизвестно')}")
        
        debug_info = f"""
📚 У вас нет взятых книг.

Ваше имя в системе: '{user_name}'

Все занятые книги:
{chr(10).join(all_taken_books) if all_taken_books else 'Нет занятых книг'}
"""
        bot.send_message(message.chat.id, debug_info)
        return
    
    result_text = f"📅 Ваши книги ({len(my_books_list)}):\n\n"
    
    for book_name, book_info in my_books_list:
        result_text += f"📖 {book_name}\n"
due_date = book_info.get("due_date", "")
if due_date:
    try:
        due_date_obj = datetime.datetime.strptime(due_date, "%d.%m.%Y").date()
        today = datetime.date.today()
        days_left = (due_date_obj - today).days
        
        if days_left < 0:
            result_text += f"   ⚠️ ПРОСРОЧЕНО на {abs(days_left)} дней!\n"
        elif days_left == 0:
            result_text += f"   🔥 Вернуть СЕГОДНЯ!\n"
        elif days_left <= 3:
            result_text += f"   ⚠️ Вернуть через {days_left} дня\n"
        else:
            result_text += f"   📅 Вернуть до: {due_date}\n"
    except:  # ← ВЫНЕСИ ЭТУ СТРОКУ НА УРОВЕНЬ С try!
        result_text += f"   📅 Вернуть до: {due_date}\n"

    result_text += "\n"  # ← ЭТА СТРОКА ДОЛЖНА БЫТЬ ЗДЕСЬ!

bot.send_message(message.chat.id, result_text)

# Обработка кнопки "Забронировать"
@bot.message_handler(func=lambda message: message.text == "📌 Забронировать")
def reserve_book_start(message):
    data = load_data()
    
    # Показываем только занятые книги
    taken_books = []
    for book_name, book_info in data["books"].items():
        if book_info.get("taken") and not book_info.get("reserved"):
            taken_books.append(book_name)
    
    if not taken_books:
        bot.send_message(message.chat.id, "📚 Сейчас все книги доступны для взятия!")
        return
    
    books_list = "\n".join([f"📖 {book}" for book in taken_books[:10]])
    
    user_states[message.chat.id] = {'action': 'reserve_book', 'step': 'book_name'}
    bot.send_message(message.chat.id, 
        f"📌 Какую книгу хотите забронировать?\n"
        f"📩 Вы получите уведомление, когда она освободится\n\n{books_list}",
        reply_markup=get_cancel_keyboard())

# Обработка кнопки "Добавить книгу" (только для админов)
@bot.message_handler(func=lambda message: message.text == "➕ Добавить книгу")
def add_book_start(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "❌ Эта функция только для администраторов!")
        return
    
    user_states[message.chat.id] = {'action': 'add_book', 'step': 'book_name'}
    bot.send_message(message.chat.id, "➕ Напишите название новой книги:", reply_markup=get_cancel_keyboard())

# Обработка кнопки "Удалить книгу" (только для админов)
@bot.message_handler(func=lambda message: message.text == "🗑️ Удалить книгу")
def delete_book_start(message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "❌ Эта функция только для администраторов!")
        return
    
    data = load_data()
    if not data["books"]:
        bot.send_message(message.chat.id, "📚 В библиотеке нет книг для удаления.")
        return
    
    books_list = "\n".join([f"📖 {book}" for book in data["books"].keys()])
    user_states[message.chat.id] = {'action': 'delete_book', 'step': 'book_name'}
    bot.send_message(message.chat.id, f"🗑️ Какую книгу удалить?\n\n{books_list}", reply_markup=get_cancel_keyboard())

# Обработка кнопки "Отмена"
@bot.message_handler(func=lambda message: message.text == "❌ Отмена")
def cancel(message):
    user_states.pop(message.chat.id, None)
    is_admin = message.from_user.id in ADMIN_IDS
    bot.send_message(message.chat.id, "❌ Действие отменено", reply_markup=get_main_keyboard(is_admin))

# Обработка текстовых сообщений
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    chat_id = message.chat.id
    user_text = message.text
    
    if chat_id not in user_states:
        is_admin = message.from_user.id in ADMIN_IDS
        bot.send_message(chat_id, "Выберите действие из меню:", reply_markup=get_main_keyboard(is_admin))
        return
    
    state = user_states[chat_id]
    
    if state['action'] == 'take_book':
        handle_take_book(message, state, user_text)
    
    elif state['action'] == 'return_book':
        handle_return_book(message, state, user_text)
    
    elif state['action'] == 'search':
        handle_search(message, user_text)
    
    elif state['action'] == 'rate_book':
        handle_rate_book(message, state, user_text)
    
    elif state['action'] == 'add_book':
        handle_add_book(message, state, user_text)
    
    elif state['action'] == 'delete_book':
        handle_delete_book(message, user_text)
    
    elif state['action'] == 'reserve_book':
        handle_reserve_book(message, user_text)

def handle_take_book(message, state, user_text):
    chat_id = message.chat.id
    
    if state['step'] == 'book_name':
        data = load_data()
        if user_text not in data["books"]:
            bot.send_message(chat_id, "❌ Такой книги нет в библиотеке!")
            user_states.pop(chat_id, None)
            return

if data["books"][user_text].get("taken"):
            bot.send_message(chat_id, "❌ Эта книга уже занята!")
            user_states.pop(chat_id, None)
            return
        
        user_states[chat_id]['book_name'] = user_text
        user_states[chat_id]['step'] = 'person_name'
        bot.send_message(chat_id, "👤 Ваше имя:", reply_markup=get_cancel_keyboard())
    
    elif state['step'] == 'person_name':
        user_states[chat_id]['person_name'] = user_text
        user_states[chat_id]['step'] = 'due_date'
        bot.send_message(chat_id, "📅 До какого числа берете книгу (в формате ДД.ММ.ГГГГ):", reply_markup=get_cancel_keyboard())
    
    elif state['step'] == 'due_date':
        try:
            due_date = datetime.datetime.strptime(user_text, "%d.%m.%Y").date()
            today = datetime.date.today()
            
            if due_date <= today:
                bot.send_message(chat_id, "❌ Дата должна быть в будущем! Попробуйте снова:")
                return
            
            # Сохраняем взятие книги
            data = load_data()
            book_name = user_states[chat_id]['book_name']
            data["books"][book_name]["taken"] = True
            data["books"][book_name]["taken_by"] = user_states[chat_id]['person_name']
            data["books"][book_name]["taken_by_id"] = message.from_user.id
            data["books"][book_name]["due_date"] = user_text
            save_data(data)
            
            is_admin = message.from_user.id in ADMIN_IDS
            bot.send_message(chat_id, 
                f"✅ Книга '{book_name}' успешно взята!\n"
                f"👤 Читатель: {user_states[chat_id]['person_name']}\n"
                f"📅 Вернуть до: {user_text}",
                reply_markup=get_main_keyboard(is_admin))
            
        except ValueError:
            bot.send_message(chat_id, "❌ Неправильный формат даты! Используйте ДД.ММ.ГГГГ:")
            return
        
        user_states.pop(chat_id, None)

def handle_return_book(message, state, user_text):
    chat_id = message.chat.id
    
    if state['step'] == 'book_name':
        data = load_data()
        if user_text not in data["books"]:
            bot.send_message(chat_id, "❌ Такой книги нет в библиотеке!")
            user_states.pop(chat_id, None)
            return
        
        if not data["books"][user_text].get("taken"):
            bot.send_message(chat_id, "❌ Эта книга уже в библиотеке!")
            user_states.pop(chat_id, None)
            return
        
        user_states[chat_id]['book_name'] = user_text
        user_states[chat_id]['step'] = 'location'
        bot.send_message(chat_id, "🏢 Где оставляете книгу?", reply_markup=get_cancel_keyboard())
    
    elif state['step'] == 'location':
        # Сохраняем возврат книги
        data = load_data()
        book_name = user_states[chat_id]['book_name']
        data["books"][book_name]["taken"] = False
        data["books"][book_name]["taken_by"] = ""
        data["books"][book_name]["taken_by_id"] = ""
        data["books"][book_name]["due_date"] = ""
        data["books"][book_name]["location"] = user_text
        
        # 🔔 УВЕДОМЛЕНИЕ ДЛЯ ТОГО, КТО ЗАБРОНИРОВАЛ
        reserved_by_id = data["books"][book_name].get("reserved_by_id")
        if reserved_by_id:
            try:
                bot.send_message(
                    reserved_by_id,
                    f"🔔 Книга '{book_name}' которую вы бронировали теперь доступна!\n"
                    f"🏢 Находится: {user_text}\n"
                    f"📚 Можете взять её в библиотеке!"
                )
                # Снимаем бронь после уведомления
                data["books"][book_name]["reserved"] = False
                data["books"][book_name]["reserved_by"] = ""
                data["books"][book_name]["reserved_by_id"] = ""
            except Exception as e:
                logger.error(f"Не удалось отправить уведомление: {e}")
        
        save_data(data)
        
        is_admin = message.from_user.id in ADMIN_IDS
        bot.send_message(chat_id,

f"✅ Книга '{book_name}' возвращена!\n"
            f"🏢 Место: {user_text}",
            reply_markup=get_main_keyboard(is_admin))
        
        user_states.pop(chat_id, None)

def handle_search(message, user_text):
    chat_id = message.chat.id
    search_query = user_text.lower()
    data = load_data()
    
    found_books = []
    for book_name, book_info in data["books"].items():
        if search_query in book_name.lower():
            found_books.append((book_name, book_info))
        elif book_info.get("author") and search_query in book_info["author"].lower():
            found_books.append((book_name, book_info))
    
    if not found_books:
        bot.send_message(chat_id, "❌ Книги по вашему запросу не найдены.", reply_markup=get_main_keyboard(message.from_user.id in ADMIN_IDS))
    else:
        result_text = f"🔍 Найдено книг: {len(found_books)}\n\n"
        for book_name, book_info in found_books[:10]:
            result_text += f"📖 {book_name}\n"
            if book_info.get("author"):
                result_text += f"   ✍️ Автор: {book_info['author']}\n"
            
            # Рейтинг
            ratings = book_info.get("ratings", {})
            if ratings:
                avg_rating = sum(ratings.values()) / len(ratings)
                result_text += f"   ⭐ Рейтинг: {avg_rating:.1f}/5\n"
            
            if book_info.get("taken"):
                result_text += f"   ❌ Занята (вернётся {book_info.get('due_date', 'неизвестно')})\n"
                if book_info.get("reserved"):
                    result_text += f"   📌 Забронирована: {book_info.get('reserved_by', 'Кем-то')}\n"
            else:
                result_text += f"   ✅ Доступна\n"
            result_text += "\n"
        
        if len(found_books) > 10:
            result_text += f"... и ещё {len(found_books) - 10} книг\n"
        
        bot.send_message(chat_id, result_text, reply_markup=get_main_keyboard(message.from_user.id in ADMIN_IDS))
    
    user_states.pop(chat_id, None)

def handle_rate_book(message, state, user_text):
    chat_id = message.chat.id
    
    if state['step'] == 'book_name':
        data = load_data()
        if user_text not in data["books"]:
            bot.send_message(chat_id, "❌ Такой книги нет в библиотеке!")
            user_states.pop(chat_id, None)
            return
        
        user_states[chat_id]['book_name'] = user_text
        user_states[chat_id]['step'] = 'rating'
        bot.send_message(chat_id, "⭐ Поставьте оценку от 1 до 5 звёзд:", reply_markup=get_rating_keyboard())
    
    elif state['step'] == 'rating':
        try:
            score_text = user_text.split()[0]  # Берем только цифру из "1 ⭐"
            score = int(score_text)
            if score < 1 or score > 5:
                raise ValueError
        except:
            bot.send_message(chat_id, "❌ Пожалуйста, выберите оценку от 1 до 5:")
            return
        
        book_name = user_states[chat_id]['book_name']
        user_id = message.from_user.id
        
        data = load_data()
        
        if "ratings" not in data["books"][book_name]:
            data["books"][book_name]["ratings"] = {}
        
        data["books"][book_name]["ratings"][str(user_id)] = score
        save_data(data)
        
        # Вычисляем средний рейтинг
        ratings = data["books"][book_name]["ratings"]
        avg_rating = sum(ratings.values()) / len(ratings)
        
        is_admin = message.from_user.id in ADMIN_IDS
        bot.send_message(chat_id, 
            f"✅ Спасибо! Вы поставили {score} ⭐ книге '{book_name}'\n"
            f"📊 Средний рейтинг: {avg_rating:.1f}/5",
            reply_markup=get_main_keyboard(is_admin))
        
        user_states.pop(chat_id, None)

def handle_add_book(message, state, user_text):
    chat_id = message.chat.id
    
    if state['step'] == 'book_name':
        user_states[chat_id]['book_name'] = user_text
        user_states[chat_id]['step'] = 'author'
        bot.send_message(chat_id, "✍️ Укажите автора книги:", reply_markup=get_cancel_keyboard())

elif state['step'] == 'author':
        user_states[chat_id]['author'] = user_text
        user_states[chat_id]['step'] = 'location'
        bot.send_message(chat_id, "🏢 Где будет храниться книга?", reply_markup=get_cancel_keyboard())
    
    elif state['step'] == 'location':
        book_name = user_states[chat_id]['book_name']
        author = user_states[chat_id]['author']
        location = user_text
        
        data = load_data()
        
        if book_name in data["books"]:
            bot.send_message(chat_id, "❌ Такая книга уже есть в библиотеке!")
            user_states.pop(chat_id, None)
            return
        
        # Добавляем новую книгу
        data["books"][book_name] = {
            "author": author,
            "location": location,
            "taken": False,
            "taken_by": "",
            "taken_by_id": "",
            "due_date": "",
            "reserved": False,
            "reserved_by": "",
            "reserved_by_id": "",
            "ratings": {}
        }
        save_data(data)
        
        is_admin = message.from_user.id in ADMIN_IDS
        bot.send_message(chat_id, 
            f"✅ Книга '{book_name}' добавлена!\n"
            f"✍️ Автор: {author}\n"
            f"🏢 Место: {location}",
            reply_markup=get_main_keyboard(is_admin))
        
        user_states.pop(chat_id, None)

def handle_delete_book(message, user_text):
    chat_id = message.chat.id
    data = load_data()
    
    if user_text not in data["books"]:
        bot.send_message(chat_id, "❌ Такой книги нет в библиотеке!")
        user_states.pop(chat_id, None)
        return
    
    # Удаляем книгу
    del data["books"][user_text]
    save_data(data)
    
    is_admin = message.from_user.id in ADMIN_IDS
    bot.send_message(chat_id, f"✅ Книга '{user_text}' удалена!", reply_markup=get_main_keyboard(is_admin))
    user_states.pop(chat_id, None)

def handle_reserve_book(message, user_text):
    chat_id = message.chat.id
    data = load_data()
    
    if user_text not in data["books"]:
        bot.send_message(chat_id, "❌ Такой книги нет в библиотеке!")
        user_states.pop(chat_id, None)
        return
    
    book_info = data["books"][user_text]
    
    if not book_info.get("taken"):
        bot.send_message(chat_id, "✅ Эта книга уже доступна! Можете взять её прямо сейчас.")
        user_states.pop(chat_id, None)
        return
    
    if book_info.get("reserved"):
        bot.send_message(chat_id, "❌ Эта книга уже забронирована другим пользователем.")
        user_states.pop(chat_id, None)
        return
    
    # Бронируем книгу
    data["books"][user_text]["reserved"] = True
    data["books"][user_text]["reserved_by"] = message.from_user.first_name
    data["books"][user_text]["reserved_by_id"] = message.from_user.id
    save_data(data)
    
    bot.send_message(chat_id,
        f"📌 Книга '{user_text}' забронирована!\n"
        f"👤 Бронь на: {message.from_user.first_name}\n"
        f"📚 Сейчас у: {book_info.get('taken_by', 'Неизвестно')}\n"
        f"📅 Вернётся: {book_info.get('due_date', 'Неизвестно')}\n"
        f"📩 Вы получите уведомление, когда книга освободится!",
        reply_markup=get_main_keyboard(message.from_user.id in ADMIN_IDS))
    
    user_states.pop(chat_id, None)

# Запуск бота
if __name__ == "__main__":
    print("Бот запущен...")
    bot.infinity_polling()





