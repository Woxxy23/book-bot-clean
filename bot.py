import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
import json
import datetime
import asyncio
from typing import Dict, List

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфигурация
BOT_TOKEN = "8476080850:AAHBhfAUmgbnNlhmfSS1n6fw4lqMk9xK6a8"
ADMIN_IDS = [986688734]  # Замени на свой ID

# Состояния для ConversationHandler
BOOK_NAME, PERSON_NAME, DUE_DATE = range(3)
RETURN_BOOK_NAME, RETURN_LOCATION = range(3, 5)
ADD_BOOK_NAME, ADD_LOCATION, ADD_AUTHOR = range(5, 8)
DELETE_BOOK = range(8, 9)
SEARCH_BOOK = range(9, 10)
RATE_BOOK, RATE_SCORE = range(10, 12)
RESERVE_BOOK = range(12, 13)

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
        buttons = [
            ["📚 Взять книгу", "📖 Вернуть книгу"],
            ["🔍 Поиск книг", "⭐ Оценить книгу"],
            ["📋 Все книги", "📅 Мои книги"],
            ["➕ Добавить книгу", "🗑️ Удалить книгу"]
        ]
    else:
        buttons = [
            ["📚 Взять книгу", "📖 Вернуть книгу"],
            ["🔍 Поиск книг", "⭐ Оценить книгу"],
            ["📋 Все книги", "📅 Мои книги"]
        ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

def get_cancel_keyboard():
    return ReplyKeyboardMarkup([["❌ Отмена"]], resize_keyboard=True)

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_admin = user_id in ADMIN_IDS
    
    if is_admin:
        welcome_text = "👑 Здравствуйте, вы вошли как админ!"
    else:
        welcome_text = "📚 Здравствуйте, у нас есть много книг!"
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=get_main_keyboard(is_admin)
    )

# Обработка отмены
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_admin = user_id in ADMIN_IDS
    
    await update.message.reply_text(
        "❌ Действие отменено",
        reply_markup=get_main_keyboard(is_admin)
    )
    return ConversationHandler.END
# Обработка кнопки "Взять книгу"
async def take_book_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 Напишите название книги которую хотите взять:",
        reply_markup=get_cancel_keyboard()
    )
    return BOOK_NAME

async def take_book_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Отмена":
        return await cancel(update, context)
    
    context.user_data['book_name'] = update.message.text
    await update.message.reply_text("👤 Ваше имя:", reply_markup=get_cancel_keyboard())
    return PERSON_NAME

async def take_book_person(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Отмена":
        return await cancel(update, context)
    
    context.user_data['person_name'] = update.message.text
    await update.message.reply_text("📅 До какого числа берете книгу (в формате ДД.ММ.ГГГГ):", reply_markup=get_cancel_keyboard())
    return DUE_DATE

async def take_book_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Отмена":
        return await cancel(update, context)
    
    try:
        due_date = datetime.datetime.strptime(update.message.text, "%d.%m.%Y").date()
        today = datetime.date.today()
        
        if due_date <= today:
            await update.message.reply_text("❌ Дата должна быть в будущем! Попробуйте снова:")
            return DUE_DATE
        
        data = load_data()
        book_name = context.user_data['book_name']
        
        if book_name not in data["books"]:
            await update.message.reply_text("❌ Такой книги нет в библиотеке!")
            return ConversationHandler.END
        
        if data["books"][book_name].get("taken"):
            await update.message.reply_text("❌ Эта книга уже занята!")
            return ConversationHandler.END
        
        # Обновляем данные книги
        data["books"][book_name]["taken"] = True
        data["books"][book_name]["taken_by"] = context.user_data['person_name']
        data["books"][book_name]["due_date"] = update.message.text
        save_data(data)
        
        user_id = update.effective_user.id
        is_admin = user_id in ADMIN_IDS
        
        await update.message.reply_text(
            f"✅ Книга '{book_name}' успешно взята!\n"
            f"👤 Читатель: {context.user_data['person_name']}\n"
            f"📅 Вернуть до: {update.message.text}",
            reply_markup=get_main_keyboard(is_admin)
        )
        
    except ValueError:
        await update.message.reply_text("❌ Неправильный формат даты! Используйте ДД.ММ.ГГГГ:")
        return DUE_DATE
    
    return ConversationHandler.END

# Обработка кнопки "Вернуть книгу"
async def return_book_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 Напишите название книги которую возвращаете:",
        reply_markup=get_cancel_keyboard()
    )
    return RETURN_BOOK_NAME

async def return_book_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Отмена":
        return await cancel(update, context)
    
    context.user_data['return_book'] = update.message.text
    await update.message.reply_text("🏢 Где оставляете книгу?", reply_markup=get_cancel_keyboard())
    return RETURN_LOCATION

async def delete_book_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    
    if not data["books"]:
        await update.message.reply_text("📚 В библиотеке нет книг для удаления.")
        return ConversationHandler.END
    
    books_list = "\n".join([f"📖 {book}" for book in data["books"].keys()])
    
    await update.message.reply_text(
        f"🗑️ Какую книгу удалить?\n\n{books_list}",
        reply_markup=get_cancel_keyboard()
    )
    return DELETE_BOOK

async def delete_book_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Отмена":
        return await cancel(update, context)
    
    book_name = update.message.text
    data = load_data()
    
    if book_name not in data["books"]:
        await update.message.reply_text("❌ Такой книги нет в библиотеке!")
        return ConversationHandler.END
    
    # Удаляем книгу
    del data["books"][book_name]
    save_data(data)
    
    user_id = update.effective_user.id
    is_admin = user_id in ADMIN_IDS
    
    await update.message.reply_text(
        f"✅ Книга '{book_name}' удалена!",
        reply_markup=get_main_keyboard(is_admin)
    )
    
    return ConversationHandler.END

# 🔍 1. ПОИСК КНИГ
async def search_books_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔍 Введите название книги или автора для поиска:",
        reply_markup=get_cancel_keyboard()
    )
    return SEARCH_BOOK

async def search_books_result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Отмена":
        return await cancel(update, context)
    
    search_query = update.message.text.lower()
    data = load_data()
    
    found_books = []
    
    for book_name, book_info in data["books"].items():
        # Поиск по названию
        if search_query in book_name.lower():
            found_books.append((book_name, book_info))
        # Поиск по автору
        elif book_info.get("author") and search_query in book_info["author"].lower():
            found_books.append((book_name, book_info))
    
    if not found_books:
        await update.message.reply_text(
            "❌ Книги по вашему запросу не найдены.",
            reply_markup=get_main_keyboard(update.effective_user.id in ADMIN_IDS)
        )
        return ConversationHandler.END
    
    result_text = f"🔍 Найдено книг: {len(found_books)}\n\n"
    
    for book_name, book_info in found_books[:10]:  # Ограничиваем вывод
        result_text += f"📖 {book_name}\n"
        if book_info.get("author"):
            result_text += f"   ✍️ Автор: {book_info['author']}\n"
        
        # Рейтинг
        ratings = book_info.get("ratings", {})
        if ratings:
            avg_rating = sum(ratings.values()) / len(ratings)
            result_text += f"   ⭐ Рейтинг: {avg_rating:.1}/5\n"
        
        if book_info.get("taken"):
            result_text += f"   ❌ Занята (вернётся {book_info.get('due_date', 'неизвестно')})\n"
        else:
            result_text += f"   ✅ Доступна\n"
        
        result_text += "\n"
    
    if len(found_books) > 10:
        result_text += f"... и ещё {len(found_books) - 10} книг\n"
    
    user_id = update.effective_user.id
    is_admin = user_id in ADMIN_IDS
    
    await update.message.reply_text(
        result_text,
        reply_markup=get_main_keyboard(is_admin)
    )
    return ConversationHandler.END

# ⭐ 2. СИСТЕМА РЕЙТИНГОВ
async def rate_book_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    
    if not data["books"]:
        await update.message.reply_text("📚 В библиотеке пока нет книг для оценки.")
        return ConversationHandler.END
    
    books_list = "\n".join([f"📖 {book}" for book in data["books"].keys()])
    
    await update.message.reply_text(
        f"⭐ Какую книгу хотите оценить?\n\n{books_list}",
        reply_markup=get_cancel_keyboard()
    )
    return RATE_BOOK

async def rate_book_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Отмена":
        return await cancel(update, context)
    
    book_name = update.message.text
    data = load_data()
    
    if book_name not in data["books"]:
        await update.message.reply_text("❌ Такой книги нет в библиотеке!")
        return ConversationHandler.END
    
    context.user_data['rate_book'] = book_name
    
    await update.message.reply_text(
        "⭐ Поставьте оценку от 1 до 5 звёзд:",
        reply_markup=ReplyKeyboardMarkup([
            ["1 ⭐", "2 ⭐⭐", "3 ⭐⭐⭐"],
            ["4 ⭐⭐⭐⭐", "5 ⭐⭐⭐⭐⭐"],
            ["❌ Отмена"]
        ], resize_keyboard=True)
    )
    return RATE_SCORE

async def rate_book_score(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Отмена":
        return await cancel(update, context)
    
    try:
        score = int(update.message.text.split()[0])
        if score < 1 or score > 5:
            raise ValueError
    except:
        await update.message.reply_text("❌ Пожалуйста, выберите оценку от 1 до 5:")
        return RATE_SCORE
    
    book_name = context.user_data['rate_book']
    user_id = update.effective_user.id
    
    data = load_data()
    
    if "ratings" not in data["books"][book_name]:
        data["books"][book_name]["ratings"] = {}
    
    data["books"][book_name]["ratings"][str(user_id)] = score
    save_data(data)
    
    # Вычисляем средний рейтинг
    ratings = data["books"][book_name]["ratings"]
    avg_rating = sum(ratings.values()) / len(ratings)
    
    user_id = update.effective_user.id
    is_admin = user_id in ADMIN_IDS
    
    await update.message.reply_text(
        f"✅ Спасибо! Вы поставили {score} ⭐ книге '{book_name}'\n"
        f"📊 Средний рейтинг: {avg_rating:.1f}/5",
        reply_markup=get_main_keyboard(is_admin)
    )
    return ConversationHandler.END

# 📅 3. МОИ КНИГИ И НАПОМИНАНИЯ
async def my_books(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    data = load_data()
    
    my_books_list = []
    for book_name, book_info in data["books"].items():
        if book_info.get("taken_by") == user_name:
            my_books_list.append((book_name, book_info))
    
    if not my_books_list:
        await update.message.reply_text("📚 У вас нет взятых книг.")
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
            except:
                result_text += f"   📅 Вернуть до: {due_date}\n"
        
        result_text += "\n"
    
    await update.message.reply_text(result_text)

# 📅 4. СИСТЕМА РЕЗЕРВИРОВАНИЯ
async def reserve_book_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    
    # Показываем только занятые книги
    taken_books = []
    for book_name, book_info in data["books"].items():
        if book_info.get("taken") and not book_info.get("reserved"):
            taken_books.append(book_name)
    
    if not taken_books:
        await update.message.reply_text("📚 Сейчас все книги доступны для взятия!")
        return ConversationHandler.END
    
    books_list = "\n".join([f"📖 {book}" for book in taken_books[:10]])
    
    await update.message.reply_text(
        f"📅 Какую книгу хотите забронировать?\n"
        f"(Вы получите уведомление когда она освободится)\n\n{books_list}",
        reply_markup=get_cancel_keyboard()
    )
    return RESERVE_BOOK

async def reserve_book_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Отмена":
        return await cancel(update, context)
    
    book_name = update.message.text
    user_name = update.effective_user.first_name
    user_id = update.effective_user.id
    
    data = load_data()
    
    if book_name not in data["books"]:
        await update.message.reply_text("❌ Такой книги нет в библиотеке!")
        return ConversationHandler.END
    
    if not data["books"][book_name].get("taken"):
        await update.message.reply_text("✅ Эта книга уже доступна! Можете взять её прямо сейчас.")
        return ConversationHandler.END
    
    if data["books"][book_name].get("reserved"):
        await update.message.reply_text("❌ Эта книга уже забронирована другим пользователем.")
        return ConversationHandler.END
    
    # Бронируем книгу
    data["books"][book_name]["reserved"] = True
    data["books"][book_name]["reserved_by"] = user_name
    data["books"][book_name]["reserved_by_id"] = user_id
    save_data(data)
    
    await update.message.reply_text(
        f"✅ Книга '{book_name}' забронирована!\n"
        f"📩 Вы получите уведомление, когда она освободится.",
        reply_markup=get_main_keyboard(user_id in ADMIN_IDS)
    )
    return ConversationHandler.END

# Остальные функции (взять книгу, вернуть книгу и т.д.) остаются похожими, 
# но добавляем проверку бронирования при возврате:

async def return_book_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Отмена":
        return await cancel(update, context)
    
    book_name = context.user_data['return_book']
    location = update.message.text
    
    data = load_data()
    
    if book_name not in data["books"]:
        await update.message.reply_text("❌ Такой книги нет в библиотеке!")
        return ConversationHandler.END
    
    if not data["books"][book_name].get("taken"):
        await update.message.reply_text("❌ Эта книга уже в библиотеке!")
        return ConversationHandler.END
    
    # Проверяем бронирование
    reserved_by_id = data["books"][book_name].get("reserved_by_id")
    
    # Обновляем данные книги
    data["books"][book_name]["taken"] = False
    data["books"][book_name]["taken_by"] = ""
    data["books"][book_name]["due_date"] = ""
    data["books"][book_name]["location"] = location
    
    user_id = update.effective_user.id
    is_admin = user_id in ADMIN_IDS
    
    await update.message.reply_text(
        f"✅ Книга '{book_name}' возвращена!\n"
        f"🏢 Место: {location}",
        reply_markup=get_main_keyboard(is_admin)
    )
    
    # 🔔 УВЕДОМЛЕНИЕ ДЛЯ ТОГО, КТО ЗАБРОНИРОВАЛ
    if reserved_by_id:
        try:
            await context.bot.send_message(
                chat_id=reserved_by_id,
                text=f"🔔 Книга '{book_name}' которую вы бронировали теперь доступна!\n"
                     f"🏢 Находится: {location}\n"
                     f"📚 Можете взять её в библиотеке!"
            )
            # Снимаем бронь после уведомления
            data["books"][book_name]["reserved"] = False
            data["books"][book_name]["reserved_by"] = ""
            data["books"][book_name]["reserved_by_id"] = ""
        except Exception as e:
            logger.error(f"Не удалось отправить уведомление: {e}")
    
    save_data(data)
    return ConversationHandler.END

# Обновляем функцию добавления книги для автора
async def add_book_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "➕ Напишите название новой книги:",
        reply_markup=get_cancel_keyboard()
    )
    return ADD_BOOK_NAME

async def add_book_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Отмена":
        return await cancel(update, context)
    
    context.user_data['new_book'] = update.message.text
    await update.message.reply_text("✍️ Укажите автора книги:", reply_markup=get_cancel_keyboard())
    return ADD_AUTHOR

async def add_book_author(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Отмена":
        return await cancel(update, context)
    
    context.user_data['new_author'] = update.message.text
    await update.message.reply_text("🏢 Где будет храниться книга?", reply_markup=get_cancel_keyboard())
    return ADD_LOCATION

async def add_book_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Отмена":
        return await cancel(update, context)
    
    book_name = context.user_data['new_book']
    author = context.user_data['new_author']
    location = update.message.text
    
    data = load_data()
    
    if book_name in data["books"]:
        await update.message.reply_text("❌ Такая книга уже есть в библиотеке!")
        return ConversationHandler.END
    
    # Добавляем новую книгу
    data["books"][book_name] = {
        "author": author,
        "location": location,
        "taken": False,
        "taken_by": "",
        "due_date": "",
        "reserved": False,
        "ratings": {}
    }
    save_data(data)
    
    user_id = update.effective_user.id
    is_admin = user_id in ADMIN_IDS
    
    await update.message.reply_text(
        f"✅ Книга '{book_name}' добавлена!\n"
        f"✍️ Автор: {author}\n"
        f"🏢 Место: {location}",
        reply_markup=get_main_keyboard(is_admin)
    )
    
    return ConversationHandler.END

# Обновляем отображение всех книг
async def all_books(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    
    if not data["books"]:
        await update.message.reply_text("📚 В библиотеке пока нет книг.")
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
                books_text += f"   📅 Забронирована: {book_info.get('reserved_by', 'Кем-то')}\n"
        else:
            books_text += f"   ✅ Доступна\n"
            books_text += f"   🏢 Место: {book_info.get('location', 'Не указано')}\n"
        books_text += "\n"
    
    await update.message.reply_text(books_text)

# Основная функция
def main():
    # Создаем Application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    
    # ConversationHandler для взятия книги
    take_book_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📚 Взять книгу$"), take_book_start)],
        states={
            BOOK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, take_book_name)],
            PERSON_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, take_book_person)],
            DUE_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, take_book_date)],
        },
        fallbacks=[MessageHandler(filters.Regex("^❌ Отмена$"), cancel)]
    )
    
    # ConversationHandler для возврата книги
    return_book_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📖 Вернуть книгу$"), return_book_start)],
        states={
            RETURN_BOOK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, return_book_name)],
            RETURN_LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, return_book_location)],
        },
        fallbacks=[MessageHandler(filters.Regex("^❌ Отмена$"), cancel)]
    )
    
    # ConversationHandler для добавления книги
    add_book_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^➕ Добавить книгу$"), add_book_start)],
        states={
            ADD_BOOK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_book_name)],
            ADD_AUTHOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_book_author)],
            ADD_LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_book_location)],
        },
        fallbacks=[MessageHandler(filters.Regex("^❌ Отмена$"), cancel)]
    )
    
    # ConversationHandler для удаления книги
    delete_book_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🗑️ Удалить книгу$"), delete_book_start)],
        states={
            DELETE_BOOK: [MessageHandler(filters.TEXT & ~filters.COMMAND, delete_book_confirm)],
        },
        fallbacks=[MessageHandler(filters.Regex("^❌ Отмена$"), cancel)]
    )
    
    # 🔍 ConversationHandler для поиска книг
    search_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🔍 Поиск книг$"), search_books_start)],
        states={
            SEARCH_BOOK: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_books_result)],
        },
        fallbacks=[MessageHandler(filters.Regex("^❌ Отмена$"), cancel)]
    )
    
    # ⭐ ConversationHandler для оценки книг
    rate_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^⭐ Оценить книгу$"), rate_book_start)],
        states={
            RATE_BOOK: [MessageHandler(filters.TEXT & ~filters.COMMAND, rate_book_name)],
            RATE_SCORE: [MessageHandler(filters.TEXT & ~filters.COMMAND, rate_book_score)],
        },
        fallbacks=[MessageHandler(filters.Regex("^❌ Отмена$"), cancel)]
    )
    
    # 📅 ConversationHandler для бронирования
    reserve_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📅 Мои книги$"), reserve_book_start)],
        states={
            RESERVE_BOOK: [MessageHandler(filters.TEXT & ~filters.COMMAND, reserve_book_confirm)],
        },
        fallbacks=[MessageHandler(filters.Regex("^❌ Отмена$"), cancel)]
    )
    
    # Добавляем все обработчики
    application.add_handler(take_book_conv)
    application.add_handler(return_book_conv)
    application.add_handler(add_book_conv)
    application.add_handler(delete_book_conv)
    application.add_handler(search_conv)
    application.add_handler(rate_conv)
    application.add_handler(reserve_conv)
    
    # Обработчик для кнопки "Все книги"
    application.add_handler(MessageHandler(filters.Regex("^📋 Все книги$"), all_books))
    
    # Обработчик для кнопки "Мои книги" (просмотр)
    application.add_handler(MessageHandler(filters.Regex("^📅 Мои книги$"), my_books))
    
    # Обработчик для любых других сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, cancel))
    
    # Запуск бота
    print("Бот запущен...")
    application.run_polling()

if __name__ == "__main__":
    main()