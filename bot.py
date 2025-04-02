import os
import json
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

# Настройки
TOKEN = os.getenv("7587845741:AAE54-7FfJTcECoPwfVg-rEHttFrkK9IkSM")
ADVICES_FILE = "advices.json"
STATS_FILE = "stats.json"

# Загрузка данных
with open(ADVICES_FILE, "r", encoding="utf-8") as f:
    ADVICES = json.load(f)

# Создаём файл статистики, если его нет
if not os.path.exists(STATS_FILE):
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump({}, f)

# Состояния
SELECT_STATE, SELECT_LEVEL, FEEDBACK = range(3)

# Клавиатуры
def main_kb():
    return ReplyKeyboardMarkup([["Апатия", "Мания"]], resize_keyboard=True)

def level_kb():
    return ReplyKeyboardMarkup([[str(i) for i in range(1, 6)]], resize_keyboard=True)

def feedback_kb(advices):
    buttons = [[InlineKeyboardButton(a, callback_data=f"help_{i}")] for i, a in enumerate(advices)]
    buttons.append([InlineKeyboardButton("❌ Ничего не помогло", callback_data="help_none")])
    return InlineKeyboardMarkup(buttons)

# Обработчики
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
    
    # Сохраняем для фидбека
    context.user_data['current_advice'] = ADVICES["states"][state][level]
    
    # Формируем сообщение
    advice = context.user_data['current_advice']
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
    
    # Загружаем статистику
    with open(STATS_FILE, "r", encoding="utf-8") as f:
        stats = json.load(f)
    
    # Обновляем статистику
    state = context.user_data['state']
    level = list(ADVICES["states"][state].keys())[list(ADVICES["states"][state].values()).index(advice)]
    
    if choice == "help_none":
        await query.edit_message_text("🔄 Попробуем другие методы в следующий раз.")
    else:
        idx = int(choice.split("_")[1])
        helped_advice = advice['advices'][idx]
        
        # Записываем в статистику
        key = f"{state}_{level}"
        if key not in stats:
            stats[key] = {a: 0 for a in advice['advices']}
        stats[key][helped_advice] += 1
        
        await query.edit_message_text(f"✅ Запомнил: '{helped_advice}' помог.")
    
    # Сохраняем статистику
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    
    # Возвращаем к началу
    await query.message.reply_text(
        "🔄 Хочешь проанализировать состояние снова?",
        reply_markup=main_kb()
    )
    return SELECT_STATE

def main():
    app = Application.builder().token(TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            SELECT_STATE: [MessageHandler(filters.TEXT & filters.Regex("^(Апатия|Мания)$"), handle_state)],
            SELECT_LEVEL: [MessageHandler(filters.TEXT & filters.Regex("^[1-5]$"), handle_level)],
            FEEDBACK: [CallbackQueryHandler(handle_feedback)]
        },
        fallbacks=[CommandHandler('cancel', lambda u,c: ConversationHandler.END)]
    )
    
    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == "__main__":
    main()
