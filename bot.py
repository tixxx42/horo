from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes

# Состояния диалога
COUNTRY, SPECIALTY, BUDGET, LANGUAGE = range(4)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Давай подберём университет. В какой стране хочешь учиться?")
    return COUNTRY

async def country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["country"] = update.message.text
    await update.message.reply_text("Окей! А какое направление (например: IT, медицина, архитектура)?")
    return SPECIALTY

async def specialty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["specialty"] = update.message.text
    await update.message.reply_text("Хорошо. Какой у тебя бюджет в год (например: 5000 евро)?")
    return BUDGET

async def budget(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["budget"] = update.message.text
    await update.message.reply_text("Принято. На каком языке хочешь учиться (например: английский)?")
    return LANGUAGE

async def language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["language"] = update.message.text

    country = context.user_data["country"]
    specialty = context.user_data["specialty"]
    budget = context.user_data["budget"]
    language = context.user_data["language"]

    await update.message.reply_text(
        f"Ты выбрал:\n"
        f"🌍 Страна: {country}\n"
        f"📚 Направление: {specialty}\n"
        f"💰 Бюджет: {budget}\n"
        f"🗣 Язык: {language}\n\n"
        f"Теперь я могу искать университеты по этим фильтрам!"
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Диалог прерван.")
    return ConversationHandler.END

import asyncio

async def main():
    app = Application.builder().token("8350744806:AAGTMP5KG_wdLlO8CF3pham9CKF4YPhnxlk").build()

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

    print("Бот запущен...")
    await app.run_polling(close_loop=False)

if __name__ == "__main__":
    import asyncio
    import nest_asyncio
    nest_asyncio.apply()
    # Создаем новый event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        loop.run_until_complete(main())
    finally:
        loop.close()

