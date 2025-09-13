from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, ContextTypes, filters
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
COUNTRY, SPECIALTY, BUDGET, LANGUAGE = range(4)

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
        cursor.execute(
            """
            SELECT name, country, specialty, language, cost, link
            FROM universities
            WHERE country ILIKE %s
              AND specialty ILIKE %s
              AND language ILIKE %s
              AND cost <= %s
            """,
            (f"%{country}%", f"%{specialty}%", f"%{language}%", budget)
        )
        results = cursor.fetchall()
        conn.close()
        return results
    except Exception as e:
        print(f"Ошибка при работе с базой данных: {e}")
        return None

# =================== БОТ ===================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! В какой стране хочешь учиться?")
    return COUNTRY

async def country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["country"] = update.message.text
    await update.message.reply_text("Окей! А какое направление (например: IT, медицина, архитектура)?")
    return SPECIALTY

async def specialty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["specialty"] = update.message.text
    await update.message.reply_text("Хорошо. Какой бюджет в год (например: 5000)?")
    return BUDGET

async def budget(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        budget_value = int(update.message.text)
        if budget_value <= 0:
            await update.message.reply_text("Пожалуйста, введите положительное число для бюджета (например: 5000)")
            return BUDGET
        context.user_data["budget"] = budget_value
        await update.message.reply_text("Принято. На каком языке обучения хочешь?")
        return LANGUAGE
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите число для бюджета (например: 5000)")
        return BUDGET

async def language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["language"] = update.message.text

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

    # Добавляем обработчики
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            COUNTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, country)],
            SPECIALTY: [MessageHandler(filters.TEXT & ~filters.COMMAND, specialty)],
            BUDGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, budget)],
            LANGUAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, language)],
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
