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
ADMIN_IDS = [986688734, 5412048228, 901147670, 5082760438]

bot = TeleBot(BOT_TOKEN)

# Файл для хранения данных
DATA_FILE = "library_data.json"

# Состояния пользователей
user_states = {}

# Загрузка данных
def load_data():
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Миграция для старых данных
            for book_name, book_info in data.get("books", {}).items():
                if "reservations" not in book_info:
                    book_info["reservations"] = []
                if "taken_by_id" not in book_info and book_info.get("taken_by"):
                    book_info["taken_by_name"] = book_info.get("taken_by", "")
            return data
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
        markup.add("➕ Добавить книгу", "🗑️ Удалить книгу")
        markup.add("📝 Забронировать книгу", "🚫 Отменить бронь")
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("📚 Взять книгу", "📖 Вернуть книгу")
        markup.add("🔍 Поиск книг", "⭐ Оценить книгу")
        markup.add("📋 Все книги", "📅 Мои книги")
        markup.add("📝 Забронировать книгу", "🚫 Отменить бронь")
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
    
    # Проверка просроченных книг
    check_overdue_books_notification(message)
    
    # Проверка доступности забронированных книг
    check_reserved_books_availability(message)
    
    if is_admin:
        welcome_text = "👑 Здравствуйте, вы вошли как админ!"
    else:
        welcome_text = "📚 Здравствуйте, у нас есть много книг!"
    
    bot.send_message(message.chat.id, welcome_text, reply_markup=get_main_keyboard(is_admin))

# Проверка просроченных книг и отправка уведомлений
def check_overdue_books_notification(message):
    user_id = message.from_user.id
    data = load_data()
    
    overdue_books = []
    today = datetime.date.today()
    
    for book_name, book_info in data["books"].items():
        taken_by_id = book_info.get("taken_by_id")
        if taken_by_id == user_id and book_info.get("taken"):
            due_date_str = book_info.get("due_date", "")
            if due_date_str:
                try:
                    due_date = datetime.datetime.strptime(due_date_str, "%d.%m.%Y").date()
                    if due_date < today:
                        overdue_books.append({
                            "name": book_name,
                            "days_overdue": (today - due_date).days
                        })
                except ValueError:
                    continue
    
    if overdue_books:
        warning_text = "⚠️ <b>ВНИМАНИЕ! У вас есть просроченные книги:</b>\n\n"
        for book in overdue_books:
            warning_text += f"📖 {book['name']}\n"
            warning_text += f"   ⌛ Просрочено на {book['days_overdue']} дней\n\n"
        warning_text += "⚠️ Пожалуйста, верните книги как можно скорее!"
        bot.send_message(message.chat.id, warning_text, parse_mode='HTML')

# Проверка доступности забронированных книг
def check_reserved_books_availability(message):
    user_id = message.from_user.id
    data = load_data()
    
    available_reservations = []
    
    for book_name, book_info in data["books"].items():
        # Проверяем, есть ли пользователь в очереди бронирования и книга теперь доступна
        reservations = book_info.get("reservations", [])
        user_position = None
        
        for i, reservation in enumerate(reservations):
            if reservation.get("user_id") == user_id:
                user_position = i
                break
        
        # Если пользователь первый в очереди и книга доступна
        if user_position == 0 and not book_info.get("taken") and not book_info.get("reserved"):
            available_reservations.append(book_name)
    
    if available_reservations:
        notification_text = "🎉 <b>Хорошие новости!</b>\n\n"
        notification_text += "Книги, которые вы забронировали, теперь доступны:\n\n"
        
        for book_name in available_reservations:
            notification_text += f"📖 <b>{book_name}</b>\n"
        
        notification_text += "\n🕐 У вас есть 24 часа чтобы взять книгу, иначе она перейдет следующему в очереди."
        bot.send_message(message.chat.id, notification_text, parse_mode='HTML')

# Обработка кнопки "Все книги"
@bot.message_handler(func=lambda message: message.text == "📋 Все книги")
def all_books(message):
    data = load_data()
    
    if not data["books"]:
        bot.send_message(message.chat.id, "📚 В библиотеке пока нет книг.")
        return
    
    books_text = "📚 <b>Список всех книг:</b>\n\n"
    
    for book_name, book_info in data["books"].items():
        books_text += f"📖 <b>{book_name}</b>\n"
        if book_info.get("author"):
            books_text += f"   ✍️ Автор: {book_info['author']}\n"
        
        # Рейтинг
        ratings = book_info.get("ratings", {})
        if ratings:
            avg_rating = sum(ratings.values()) / len(ratings)
            books_text += f"   ⭐ Рейтинг: {avg_rating:.1f}/5\n"
        
        if book_info.get("taken"):
            taken_by = book_info.get("taken_by_name", "Неизвестно")
            books_text += f"   ❌ Занята\n"
            books_text += f"   👤 У: {taken_by}\n"
            books_text += f"   📅 До: {book_info.get('due_date', 'Не указано')}\n"
            
            # Показываем очередь бронирования
            reservations = book_info.get("reservations", [])
            if reservations:
                books_text += f"   📝 В очереди: {len(reservations)} чел.\n"
        else:
            books_text += f"   ✅ Доступна\n"
            books_text += f"   🏢 Место: {book_info.get('location', 'Не указано')}\n"
        books_text += "\n"
    
    bot.send_message(message.chat.id, books_text, parse_mode='HTML')

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

# Обработка кнопки "Мои книги" - ИСПРАВЛЕННАЯ ВЕРСИЯ
@bot.message_handler(func=lambda message: message.text == "📅 Мои книги")
def my_books(message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    data = load_data()
    
    # Книги, которые пользователь взял
    taken_books = []
    # Книги, которые пользователь забронировал
    reserved_books = []
    
    for book_name, book_info in data["books"].items():
        # Проверяем по ID пользователя (новый способ) или по имени (старый способ для совместимости)
        taken_by_id = book_info.get("taken_by_id")
        taken_by_name = book_info.get("taken_by_name", "")
        
        if (taken_by_id == user_id or taken_by_name == user_name) and book_info.get("taken"):
            taken_books.append((book_name, book_info))
        
        # Проверяем бронирования
        reservations = book_info.get("reservations", [])
        for i, reservation in enumerate(reservations):
            if reservation.get("user_id") == user_id:
                reserved_books.append({
                    "name": book_name,
                    "position": i + 1,
                    "book_info": book_info
                })
    
    result_text = ""
    
    if taken_books:
        result_text += f"📚 <b>Ваши взятые книги ({len(taken_books)}):</b>\n\n"
        has_overdue = False
        
        for book_name, book_info in taken_books:
            result_text += f"📖 <b>{book_name}</b>\n"
            due_date = book_info.get("due_date", "")
            if due_date:
                try:
                    due_date_obj = datetime.datetime.strptime(due_date, "%d.%m.%Y").date()
                    today = datetime.date.today()
                    days_left = (due_date_obj - today).days
                    
                    if days_left < 0:
                        result_text += f"   ⚠️ <b>ПРОСРОЧЕНО на {abs(days_left)} дней!</b>\n"
                        has_overdue = True
                    elif days_left == 0:
                        result_text += f"   🔥 <b>Вернуть СЕГОДНЯ!</b>\n"
                    elif days_left <= 3:
                        result_text += f"   ⚠️ Вернуть через {days_left} дня\n"
                    else:
                        result_text += f"   📅 Вернуть до: {due_date}\n"
                except:
                    result_text += f"   📅 Вернуть до: {due_date}\n"
            
            result_text += "\n"
        
        if has_overdue:
            result_text += "⚠️ <b>ВНИМАНИЕ! У вас есть просроченные книги. Пожалуйста, верните их как можно скорее!</b>\n\n"
    
    if reserved_books:
        result_text += f"📝 <b>Ваши забронированные книги ({len(reserved_books)}):</b>\n\n"
        
        for reservation in reserved_books:
            result_text += f"📖 <b>{reservation['name']}</b>\n"
            result_text += f"   📍 Ваша позиция в очереди: {reservation['position']}\n"
            
            # Показываем примерное время ожидания
            if reservation['position'] == 1:
                result_text += f"   🎉 Вы следующий в очереди!\n"
            else:
                estimated_wait = reservation['position'] * 7  # Примерно 7 дней на человека
                result_text += f"   ⏳ Примерное время ожидания: {estimated_wait} дней\n"
            
            # Если книга сейчас свободна и вы первый в очереди
            if reservation['position'] == 1 and not reservation['book_info'].get("taken"):
                result_text += f"   ✅ Книга сейчас доступна! Можете взять её.\n"
            
            result_text += "\n"
    
    if not taken_books and not reserved_books:
        result_text = "📚 У вас нет взятых или забронированных книг."
    
    bot.send_message(message.chat.id, result_text, parse_mode='HTML')

# Обработка кнопки "Забронировать книгу"
@bot.message_handler(func=lambda message: message.text == "📝 Забронировать книгу")
def reserve_book_start(message):
    data = load_data()
    
    if not data["books"]:
        bot.send_message(message.chat.id, "📚 В библиотеке пока нет книг.")
        return
    
    # Показываем только занятые книги, которые можно забронировать
    available_for_reservation = []
    for book_name, book_info in data["books"].items():
        if book_info.get("taken"):
            # Проверяем, не забронировал ли уже пользователь эту книгу
            reservations = book_info.get("reservations", [])
            already_reserved = any(reservation.get("user_id") == message.from_user.id for reservation in reservations)
            
            if not already_reserved:
                available_for_reservation.append(book_name)
    
    if not available_for_reservation:
        bot.send_message(message.chat.id, "❌ Все доступные книги уже забронированы вами или свободны.")
        return
    
    books_list = "\n".join([f"📖 {book}" for book in available_for_reservation])
    user_states[message.chat.id] = {'action': 'reserve_book', 'step': 'book_name'}
    bot.send_message(message.chat.id, 
                    f"📝 Какую книгу хотите забронировать?\n\n"
                    f"Доступны для бронирования (занятые книги):\n\n{books_list}", 
                    reply_markup=get_cancel_keyboard())

# Обработка кнопки "Отменить бронь"
@bot.message_handler(func=lambda message: message.text == "🚫 Отменить бронь")
def cancel_reservation_start(message):
    user_id = message.from_user.id
    data = load_data()
    
    # Находим книги, которые пользователь забронировал
    user_reservations = []
    
    for book_name, book_info in data["books"].items():
        reservations = book_info.get("reservations", [])
        for i, reservation in enumerate(reservations):
            if reservation.get("user_id") == user_id:
                user_reservations.append({
                    "book_name": book_name,
                    "position": i + 1
                })
    
    if not user_reservations:
        bot.send_message(message.chat.id, "❌ У вас нет активных бронирований.")
        return
    
    books_list = "\n".join([f"📖 {res['book_name']} (позиция: {res['position']})" for res in user_reservations])
    user_states[message.chat.id] = {'action': 'cancel_reservation', 'step': 'book_name'}
    bot.send_message(message.chat.id, 
                    f"🚫 Какую бронь хотите отменить?\n\n{books_list}", 
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
    
    elif state['action'] == 'cancel_reservation':
        handle_cancel_reservation(message, user_text)

def handle_take_book(message, state, user_text):
    chat_id = message.chat.id
    
    if state['step'] == 'book_name':
        data = load_data()
        if user_text not in data["books"]:
            bot.send_message(chat_id, "❌ Такой книги нет в библиотеке!")
            user_states.pop(chat_id, None)
            return
        
        book_info = data["books"][user_text]
        
        # Проверяем, свободна ли книга
        if book_info.get("taken"):
            bot.send_message(chat_id, "❌ Эта книга уже занята!")
            user_states.pop(chat_id, None)
            return
        
        # Проверяем, есть ли бронирование и является ли пользователь первым в очереди
        reservations = book_info.get("reservations", [])
        if reservations:
            first_reservation = reservations[0]
            if first_reservation.get("user_id") != message.from_user.id:
                bot.send_message(chat_id, 
                               f"❌ Эта книга забронирована. Вы не первый в очереди.\n"
                               f"📝 Ваша позиция: {self.get_user_position(reservations, message.from_user.id)}")
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
            
            # Удаляем пользователя из очереди бронирования, если он там был
            reservations = data["books"][book_name].get("reservations", [])
            data["books"][book_name]["reservations"] = [r for r in reservations if r.get("user_id") != message.from_user.id]
            
            data["books"][book_name]["taken"] = True
            data["books"][book_name]["taken_by_id"] = message.from_user.id
            data["books"][book_name]["taken_by_name"] = user_states[chat_id]['person_name']
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
        
        # Уведомляем следующего в очереди бронирования
        reservations = data["books"][book_name].get("reservations", [])
        if reservations:
            next_user_id = reservations[0].get("user_id")
            next_user_name = reservations[0].get("user_name", "Пользователь")
            
            try:
                bot.send_message(
                    next_user_id,
                    f"🎉 <b>Хорошие новости!</b>\n\n"
                    f"Книга '<b>{book_name}</b>', которую вы забронировали, теперь доступна!\n"
                    f"🕐 У вас есть 24 часа чтобы взять книгу.\n\n"
                    f"📍 Местонахождение книги: {user_text}",
                    parse_mode='HTML'
                )
            except Exception as e:
                logger.error(f"Не удалось отправить уведомление пользователю {next_user_id}: {e}")
        
        data["books"][book_name]["taken"] = False
        data["books"][book_name]["taken_by_id"] = None
        data["books"][book_name]["taken_by_name"] = ""
        data["books"][book_name]["due_date"] = ""
        data["books"][book_name]["location"] = user_text
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
                # Показываем информацию о бронировании
                reservations = book_info.get("reservations", [])
                if reservations:
                    result_text += f"   📝 В очереди: {len(reservations)} чел.\n"
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
            "taken_by_id": None,
            "taken_by_name": "",
            "due_date": "",
            "reservations": [],
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
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    
    data = load_data()
    
    if user_text not in data["books"]:
        bot.send_message(chat_id, "❌ Такой книги нет в библиотеке!")
        user_states.pop(chat_id, None)
        return
    
    book_info = data["books"][user_text]
    
    # Проверяем, занята ли книга
    if not book_info.get("taken"):
        bot.send_message(chat_id, "❌ Эта книга уже доступна! Можете взять её без брони.")
        user_states.pop(chat_id, None)
        return
    
    # Проверяем, не забронировал ли уже пользователь эту книгу
    reservations = book_info.get("reservations", [])
    for reservation in reservations:
        if reservation.get("user_id") == user_id:
            bot.send_message(chat_id, "❌ Вы уже забронировали эту книгу!")
            user_states.pop(chat_id, None)
            return
    
    # Добавляем бронирование
    new_reservation = {
        "user_id": user_id,
        "user_name": user_name,
        "reserved_date": datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
    }
    
    reservations.append(new_reservation)
    data["books"][user_text]["reservations"] = reservations
    save_data(data)
    
    position = len(reservations)
    
    is_admin = message.from_user.id in ADMIN_IDS
    bot.send_message(chat_id,
        f"✅ Книга '{user_text}' забронирована!\n"
        f"📝 Ваша позиция в очереди: {position}\n\n"
        f"ℹ️ Вы получите уведомление, когда книга станет доступна.",
        reply_markup=get_main_keyboard(is_admin))
    
    user_states.pop(chat_id, None)

def handle_cancel_reservation(message, user_text):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    data = load_data()
    
    if user_text not in data["books"]:
        bot.send_message(chat_id, "❌ Такой книги нет в библиотеке!")
        user_states.pop(chat_id, None)
        return
    
    book_info = data["books"][user_text]
    reservations = book_info.get("reservations", [])
    
    # Удаляем бронирование пользователя
    initial_count = len(reservations)
    reservations = [r for r in reservations if r.get("user_id") != user_id]
    
    if len(reservations) == initial_count:
        bot.send_message(chat_id, "❌ У вас нет брони на эту книгу!")
        user_states.pop(chat_id, None)
        return
    
    data["books"][user_text]["reservations"] = reservations
    save_data(data)
    
    is_admin = message.from_user.id in ADMIN_IDS
    bot.send_message(chat_id,
        f"✅ Бронирование книги '{user_text}' отменено!",
        reply_markup=get_main_keyboard(is_admin))
    
    user_states.pop(chat_id, None)

# Вспомогательная функция для получения позиции пользователя в очереди
def get_user_position(reservations, user_id):
    for i, reservation in enumerate(reservations):
        if reservation.get("user_id") == user_id:
            return i + 1
    return None

# Запуск бота
if __name__ == "__main__":
    print("Бот запущен...")
    bot.infinity_polling()
