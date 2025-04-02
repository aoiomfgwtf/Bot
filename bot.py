import os
import logging
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackContext,
    filters,
    ConversationHandler,
    CallbackQueryHandler
)

# Настройка логов
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния диалога
SELECT_STATE, SELECT_LEVEL, FEEDBACK = range(3)

# Токен бота (замени на свой или используй переменную окружения)
TOKEN = os.getenv("TOKEN") or "7587845741:AAE54-7FfJTcECoPwfVg-rEHttFrkK9IkSM"

# Клавиатуры
def main_kb():
    return ReplyKeyboardMarkup([["Апатия", "Мания"]], resize_keyboard=True)

def level_kb():
    return ReplyKeyboardMarkup([[str(i) for i in range(1, 6)]], resize_keyboard=True)

def feedback_kb(advices):
    buttons = [[InlineKeyboardButton(a, callback_data=f"help_{i}")] for i, a in enumerate(advices)]
    buttons.append([InlineKeyboardButton("❌ Ничего не помогло", callback_data="help_none")])
    return InlineKeyboardMarkup(buttons)

# Советы (можно вынести в JSON)
ADVICES = {
    "Апатия": {
        "1": {
            "description": "Отличное состояние! Поддержи его легкой активностью.",
            "advices": ["Прогулка", "Музыка", "Вода"],
            "risk": "Низкий риск"
        },
        "2": {
            "description": "Есть риск провалиться глубже в мысли.",
            "advices": ["Горячий душ", "Кофе", "Звонок другу"],
            "risk": "Средний риск"
        }
    },
    "Мания": {
        "1": {
            "description": "Легкое возбуждение - может быть полезно для работы.",
            "advices": ["Фокусировка", "Запись идей", "Разминка"],
            "risk": "Низкий риск"
        },
        "2": {
            "description": "Состояние близкое к критическому.",
            "advices": ["Дыхание 4-7-8", "Холод на лицо", "Тупое видео"],
            "risk": "Высокий риск"
        }
    }
}

# Обработчики команд
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "📊 Выбери текущее состояние:",
        reply_markup=main_kb()
    )
    return SELECT_STATE

async def handle_state(update: Update, context: CallbackContext):
    state = update.message.text
    context.user_data['state'] = state
    await update.message.reply_text(
        f"🔢 Выбери уровень (1-5):",
        reply_markup=level_kb()
    )
    return SELECT_LEVEL

async def handle_level(update: Update, context: CallbackContext):
    level = update.message.text
    state = context.user_data['state']
    
    if state not in ADVICES or level not in ADVICES[state]:
        await update.message.reply_text("Ошибка: нет данных для этого состояния")
        return ConversationHandler.END
    
    advice = ADVICES[state][level]
    context.user_data['current_advice'] = advice
    
    text = (
        f"📌 {advice['description']}\n\n"
        f"⚠️ Уровень перегрузки: {advice['risk']}\n\n"
        "💡 Советы:\n" + "\n".join(f"• {a}" for a in advice['advices'])
    )
    
    await update.message.reply_text(text)
    await update.message.reply_text(
        "Что из этого помогло?",
        reply_markup=feedback_kb(advice['advices'])
    )
    return FEEDBACK

async def handle_feedback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    choice = query.data
    advice = context.user_data['current_advice']
    
    if choice == "help_none":
        await query.edit_message_text("🔄 Попробуем другие методы в следующий раз.")
    else:
        idx = int(choice.split("_")[1])
        helped_advice = advice['advices'][idx]
        await query.edit_message_text(f"✅ Запомнил: '{helped_advice}' помог.")
    
    # Возврат к началу
    await query.message.reply_text(
        "🔄 Хочешь проанализировать состояние снова?",
        reply_markup=main_kb()
    )
    return SELECT_STATE

async def cancel(update: Update, context: CallbackContext):
    await update.message.reply_text("Диалог прерван. Нажми /start чтобы начать заново.")
    return ConversationHandler.END

def main():
    application = Application.builder().token(TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            SELECT_STATE: [MessageHandler(filters.TEXT & filters.Regex("^(Апатия|Мания)$"), handle_state)],
            SELECT_LEVEL: [MessageHandler(filters.TEXT & filters.Regex("^[1-5]$"), handle_level)],
            FEEDBACK: [CallbackQueryHandler(handle_feedback)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    application.add_handler(conv_handler)
    
    # Запуск бота
    application.run_polling()

if __name__ == '__main__':
    main()
