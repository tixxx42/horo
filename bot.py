from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, ContextTypes, filters, CallbackQueryHandler
from telegram import error as telegram_error
import psycopg2
import logging
import sys

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния диалога
CHOOSING, TYPING_COUNTRY, TYPING_SPECIALTY, TYPING_BUDGET, TYPING_LANGUAGE = range(5)

# Callback data
COUNTRY_FILTER = "country"
SPECIALTY_FILTER = "specialty"
BUDGET_FILTER = "budget"
LANGUAGE_FILTER = "language"

def search_universities(country, specialty, budget, language):
    try:
        conn = psycopg2.connect(
            dbname="unibot",
            user="postgres",
            password="@obwZWJq@Y46Yi",
            host="localhost",
            port="5432"
        )
        cursor = conn.cursor()
        
        # Создаем базовый запрос
        query = """
            SELECT name, country, specialty, language, cost, link
            FROM universities
            WHERE 1=1
        """
        params = []
        
        # Обработка нескольких значений для страны
        if country:
            countries = [c.strip() for c in country.split(",")]
            country_conditions = []
            for c in countries:
                country_conditions.append("country ILIKE %s")
                params.append(f"%{c}%")
            if country_conditions:
                query += f" AND ({' OR '.join(country_conditions)})"
        
        # Обработка нескольких значений для специальности
        if specialty:
            specialties = [s.strip() for s in specialty.split(",")]
            specialty_conditions = []
            for s in specialties:
                specialty_conditions.append("specialty ILIKE %s")
                params.append(f"%{s}%")
            if specialty_conditions:
                query += f" AND ({' OR '.join(specialty_conditions)})"
        
        # Обработка нескольких значений для языка
        if language:
            languages = [l.strip() for l in language.split(",")]
            language_conditions = []
            for l in languages:
                language_conditions.append("language ILIKE %s")
                params.append(f"%{l}%")
            if language_conditions:
                query += f" AND ({' OR '.join(language_conditions)})"
        
        # Бюджет остается как есть, так как это числовое значение
        if budget != 1000000:
            query += " AND cost <= %s"
            params.append(budget)
            
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        return results
    except Exception as e:
        print(f"Ошибка при работе с базой данных: {e}")
        return None

# =================== БОТ ===================

def get_filter_keyboard(context: ContextTypes.DEFAULT_TYPE = None):
    # Функция для получения статуса параметра
    def get_status(param):
        if not context or param not in context.user_data:
            return ""
        return "✅"
    
    keyboard = [
        [
            InlineKeyboardButton(f"Страна {get_status('country')}", callback_data=COUNTRY_FILTER),
            InlineKeyboardButton(f"Специальность {get_status('specialty')}", callback_data=SPECIALTY_FILTER)
        ],
        [
            InlineKeyboardButton(f"Бюджет $ {get_status('budget')}", callback_data=BUDGET_FILTER),
            InlineKeyboardButton(f"Язык обучения {get_status('language')}", callback_data=LANGUAGE_FILTER)
        ],
        [
            InlineKeyboardButton("🔍 Поиск", callback_data="search")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()  # Очищаем данные при новом старте
    await update.message.reply_text(
        "Привет! Я - бот, который поможет тебе подобрать университет по твоим критериям. "
        "Я знаю много университетов за границей. Давай начнем поиск!"
    )
    await update.message.reply_text(
        "Выбери параметры для поиска:",
        reply_markup=get_filter_keyboard(context)
    )
    return CHOOSING

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "new_search":
        context.user_data.clear()
        await query.message.edit_text(
            "Выбери параметр для настройки поиска:",
            reply_markup=get_filter_keyboard(context)
        )
        return CHOOSING

    if query.data == "search":
        # Устанавливаем значения по умолчанию для незаполненных параметров
        defaults = {
            "country": "",
            "specialty": "",
            "budget": 1000000,  # Очень большое число для отсутствия ограничения по бюджету
            "language": ""
        }
        
        # Используем значения пользователя или значения по умолчанию
        for key in defaults:
            if key not in context.user_data:
                context.user_data[key] = defaults[key]
        
        return await show_results(update, context)

    messages = {
        COUNTRY_FILTER: "🌍 Введите одну или несколько стран\n\nФормат: Страна, Страна, Страна\nПример: Германия, Франция, Италия\n\nИли введите одну страну: Германия",
        SPECIALTY_FILTER: "📚 Введите одно или несколько направлений\n\nФормат: Направление, Направление, Направление\nПример: IT, медицина, экономика\n\nИли введите одно направление: IT",
        BUDGET_FILTER: "💰 Введите максимальную сумму в $:",
        LANGUAGE_FILTER: "🗣 Введите один или несколько языков обучения\n\nФормат: Язык, Язык, Язык\nПример: английский, немецкий, французский\n\nИли введите один язык: английский"
    }

    context.user_data['current_filter'] = query.data
    await query.message.edit_text(messages[query.data])
    
    return {
        COUNTRY_FILTER: TYPING_COUNTRY,
        SPECIALTY_FILTER: TYPING_SPECIALTY,
        BUDGET_FILTER: TYPING_BUDGET,
        LANGUAGE_FILTER: TYPING_LANGUAGE
    }[query.data]

async def input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    current_filter = context.user_data.get('current_filter')
    text = update.message.text

    if current_filter == BUDGET_FILTER:
        try:
            budget_value = int(text)
            if budget_value <= 0:
                await update.message.reply_text(
                    "Пожалуйста, введите положительное число для бюджета (например: 5000)",
                    reply_markup=get_filter_keyboard(context)
                )
                return TYPING_BUDGET
            context.user_data["budget"] = budget_value
        except ValueError:
            await update.message.reply_text("Введите число")
            return TYPING_BUDGET
    else:
        context.user_data[current_filter] = text

    await update.message.reply_text(
        f"Параметр установлен! Выберите следующий параметр или нажмите 'Поиск':",
        reply_markup=get_filter_keyboard(context)
    )
    return CHOOSING

async def show_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    # Достаём фильтры
    country = context.user_data["country"]
    specialty = context.user_data["specialty"]
    budget = context.user_data["budget"]
    language = context.user_data["language"]

    print(f"Поиск по параметрам: страна='{country}', специальность='{specialty}', бюджет={budget}, язык='{language}'")

    # Поиск в базе
    results = search_universities(country, specialty, budget, language)
    if results:
        print(f"Найдено результатов: {len(results)}")
    else:
        print("Результатов не найдено")

    # Формируем ответ
    if results is None:
        text = "Произошла ошибка при обращении к базе данных. Попробуйте позже."
    elif results:
        text = "Нашёл такие университеты:\n\n"
        for r in results:
            text += f"🏛 {r[0]} ({r[1]})\n📚 {r[2]}\n🗣 {r[3]}\n💰 {r[4]} €/год\n🔗 {r[5]}\n\n"
    else:
        text = "К сожалению не удалось ничего найти"

    # Добавляем кнопку для нового поиска
    keyboard = [[InlineKeyboardButton("🔄 Новый поиск", callback_data="new_search")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.edit_text(text, reply_markup=reply_markup)
    return CHOOSING

    # Достаём фильтры
    country = context.user_data["country"]
    specialty = context.user_data["specialty"]
    budget = context.user_data["budget"]
    language = context.user_data["language"]

    print(f"Поиск по параметрам: страна='{country}', специальность='{specialty}', бюджет={budget}, язык='{language}'")

    # Поиск в базе
    results = search_universities(country, specialty, budget, language)
    if results:
        print(f"Найдено результатов: {len(results)}")
    else:
        print("Результатов не найдено")

    # Формируем ответ
    if results is None:
        text = "Произошла ошибка при обращении к базе данных. Попробуйте позже."
    elif results:
        text = "Нашёл такие университеты:\n\n"
        for r in results:
            text += f"🏛 {r[0]} ({r[1]})\n📚 {r[2]}\n🗣 {r[3]}\n💰 {r[4]} €/год\n🔗 {r[5]}\n\n"
    else:
        text = "К сожалению не удалось ничего найти"

    await update.message.reply_text(text)
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Диалог прерван.")
    return ConversationHandler.END


import asyncio
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors caused by updates."""
    logger.error("Exception while handling an update:", exc_info=context.error)
    
    if isinstance(context.error, telegram_error.Conflict):
        logger.error("Conflict: Another instance of the bot is running")
        sys.exit(1)

async def set_commands(application: Application):
    """Установка команд бота"""
    commands = [
        ('start', 'Начать поиск университетов')
    ]
    await application.bot.set_my_commands(commands)

async def main():
    """Основная функция бота"""
    # Настраиваем таймауты
    app = (
        Application.builder()
        .token("8350744806:AAGTMP5KG_wdLlO8CF3pham9CKF4YPhnxlk")
        .read_timeout(30)
        .write_timeout(30)
        .connect_timeout(30)
        .pool_timeout(30)
        .build()
    )
    
    # Устанавливаем команды бота
    await set_commands(app)

    # Добавляем обработчики
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING: [CallbackQueryHandler(button_handler)],
            TYPING_COUNTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_handler)],
            TYPING_SPECIALTY: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_handler)],
            TYPING_BUDGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_handler)],
            TYPING_LANGUAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_handler)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    app.add_error_handler(error_handler)
    
    logger.info("Запуск бота...")
    await app.initialize()
    logger.info("Бот запущен и ожидает сообщений...")
    
    try:
        # Запускаем бота и ждем сообщений
        await app.run_polling(drop_pending_updates=True)
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        raise

if __name__ == "__main__":
    # Для работы в интерактивных средах (например, VS Code Debug Console)
    import nest_asyncio
    nest_asyncio.apply()
    
    try:
        # Запускаем бота
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\nБот остановлен пользователем")
    except telegram_error.Conflict:
        logger.error("Обнаружен конфликт: другой экземпляр бота уже запущен")
    except Exception as e:
        logger.error(f"\nПроизошла ошибка: {e}")
    finally:
        logger.info("Сеанс завершен")
