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

# Токен бота (ЗАМЕНИ НА СВОЙ!)
TOKEN = os.getenv("TOKEN") or "ВАШ_ТОКЕН_ТУТ"

# Полные данные для всех состояний и уровней
ADVICES = {
    "Апатия": {
        "1": {
            "description": "Отличное состояние! Поддержи его легкой активностью.",
            "advices": ["Короткая прогулка", "Бодрая музыка", "Стакан воды"],
            "risk": "Низкий риск"
        },
        "2": {
            "description": "Легкая апатия. Не дай себе погрузиться глубже.",
            "advices": ["Горячий душ", "Кофе", "Звонок другу"],
            "risk": "Умеренный риск"
        },
        "3": {
            "description": "Средняя апатия. Нужно активное действие.",
            "advices": ["Уборка", "Спорт", "Рисование"],
            "risk": "Высокий риск"
        },
        "4": {
            "description": "Сильная апатия. Критическое состояние.",
            "advices": ["Разговор с близким", "Прогулка на улице", "Контрастный душ"],
            "risk": "Очень высокий риск"
        },
        "5": {
            "description": "Критическая апатия. Срочно принимай меры.",
            "advices": ["Экстренный звонок", "Медитация", "Выплеск эмоций"],
            "risk": "Критический уровень"
        }
    },
    "Мания": {
        "1": {
            "description": "Легкое возбуждение. Можно направить в работу.",
            "advices": ["Фокусировка на задаче", "Запись идей", "Разминка"],
            "risk": "Низкий риск"
        },
        "2": {
            "description": "Умеренная мания. Контролируй энергию.",
            "advices": ["Дыхательные упражнения", "Чай вместо кофе", "Таймер работы"],
            "risk": "Умеренный риск"
        },
        "3": {
            "description": "Сильная мания. Пора успокаиваться.",
            "advices": ["Холодная вода на лицо", "Тихая музыка", "Заземление"],
            "risk": "Высокий риск"
        },
        "4": {
            "description": "Очень сильная мания. Остановись!",
            "advices": ["Темная комната", "Дыхание 4-7-8", "Отдых без гаджетов"],
            "risk": "Очень высокий риск"
        },
        "5": {
            "description": "Критическая мания. Срочно успокаивайся!",
            "advices": ["Лечь в постель", "Принять успокоительное", "Позвать на помощь"],
            "risk": "Критический уровень"
        }
    }
}

# Клавиатуры
def main_kb():
    return ReplyKeyboardMarkup([["Апатия", "Мания"]], resize_keyboard=True)

def level_kb():
    return ReplyKeyboardMarkup([[str(i) for i in range(1, 6)]], resize_keyboard=True)

def feedback_kb(advices):
    buttons = [[InlineKeyboardButton(a, callback_data=f"help_{i}")] for i, a in enumerate(advices)]
    buttons.append([InlineKeyboardButton("❌ Ничего не помогло", callback_data="help_none")])
    return InlineKeyboardMarkup(buttons)

# Обработчики команд
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "📊 Выбери текущее состояние:",
        reply_markup=main_kb()
    )
    return SELECT_STATE

async def handle_state(update: Update, context: CallbackContext):
    state = update.message.text
    if state not in ADVICES:
        await update.message.reply_text("Ошибка: выбери Апатия или Мания")
        return SELECT_STATE
    
    context.user_data['state'] = state
    await update.message.reply_text(
        f"🔢 Выбери уровень (1-5):",
        reply_markup=level_kb()
    )
    return SELECT_LEVEL

async def handle_level(update: Update, context: CallbackContext):
    level = update.message.text
    state = context.user_data.get('state')
    
    if not state or state not in ADVICES:
        await update.message.reply_text("Ошибка: состояние не выбрано. Начни с /start")
        return ConversationHandler.END
    
    if level not in ADVICES[state]:
        await update.message.reply_text("Ошибка: выбери уровень от 1 до 5")
        return SELECT_LEVEL
    
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
    advice = context.user_data.get('current_advice', {})
    
    if choice == "help_none":
        await query.edit_message_text("🔄 Попробуем другие методы в следующий раз.")
    else:
        try:
            idx = int(choice.split("_")[1])
            helped_advice = advice.get('advices', [])[idx]
            await query.edit_message_text(f"✅ Запомнил: '{helped_advice}' помог.")
        except:
            await query.edit_message_text("⚠️ Ошибка обработки выбора")
    
    await query.message.reply_text(
        "🔄 Хочешь проанализировать состояние снова?",
        reply_markup=main_kb()
    )
    return SELECT_STATE

async def cancel(update: Update, context: CallbackContext):
    await update.message.reply_text("Диалог прерван. Нажми /start чтобы начать заново.")
    return ConversationHandler.END

def main():
    # Проверка токена
    if not TOKEN or TOKEN == "ВАШ_ТОКЕН_ТУТ":
        print("❌ ОШИБКА: Токен не установлен!")
        return
    
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
    print("✅ Бот запущен")
    application.run_polling()

if __name__ == '__main__':
    main()
