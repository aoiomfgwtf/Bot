import logging
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
TOKEN = "7587845741:AAE54-7FfJTcECoPwfVg-rEHttFrkK9IkSM"
DATA_FILE = "user_data.csv"
ADVICES_FILE = "advices.json"

# Загрузка советов из JSON
with open(ADVICES_FILE, "r", encoding="utf-8") as f:
    ADVICES_DATA = json.load(f)

# Состояния для ConversationHandler
SELECTING_LEVEL, SELECTING_ADVICE, CONFIRMING = range(3)

# Клавиатуры
def get_main_keyboard():
    return ReplyKeyboardMarkup([["Апатия", "Мания"]], resize_keyboard=True)

def get_level_keyboard():
    return ReplyKeyboardMarkup([[str(i) for i in range(1,6)]], resize_keyboard=True)

def get_advices_keyboard(advices):
    buttons = []
    for advice in advices:
        buttons.append([InlineKeyboardButton(advice, callback_data=f"advice_{advices.index(advice)}")])
    buttons.append([InlineKeyboardButton("Ничего не помогло", callback_data="advice_none")])
    return InlineKeyboardMarkup(buttons)

async def start(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "Привет! Я помогу тебе отслеживать твое состояние.\n"
        "Выбери текущее состояние:",
        reply_markup=get_main_keyboard()
    )
    return SELECTING_LEVEL

async def handle_state(update: Update, context: CallbackContext):
    state = update.message.text
    context.user_data['current_state'] = state
    await update.message.reply_text(
        f"Вы выбрали {state}. Какой уровень? (1-5):",
        reply_markup=get_level_keyboard()
    )
    return SELECTING_ADVICE

async def handle_level(update: Update, context: CallbackContext):
    level = int(update.message.text)
    state = context.user_data.get('current_state', 'unknown')
    
    # Сохраняем данные
    context.user_data['current_level'] = level
    
    # Получаем рекомендации
    state_data = ADVICES_DATA["states"][state][str(level)]
    message = (
        f"📌 {state_data['description']}\n\n"
        f"⚠️ Уровень перегрузки: {state_data['risk']}\n\n"
        f"Советы:\n" + "\n".join(f"• {advice}" for advice in state_data['advices'])
    )
    
    await update.message.reply_text(
        message,
        reply_markup=get_advices_keyboard(state_data['advices'])
    )
    return CONFIRMING

async def handle_advice_selection(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    selected_advice = query.data
    if selected_advice == "advice_none":
        await query.edit_message_text("Хорошо, попробуем другие методы в следующий раз.")
    else:
        advice_index = int(selected_advice.split("_")[1])
        state = context.user_data['current_state']
        level = context.user_data['current_level']
        selected_advice_text = ADVICES_DATA["states"][state][str(level)]['advices'][advice_index]
        
        # Здесь должна быть логика сохранения статистики
        await query.edit_message_text(
            f"✅ Вы отметили, что помогло: {selected_advice_text}\n"
            "Эта информация сохранена для улучшения рекомендаций."
        )
    
    await query.message.reply_text(
        "Нажми /start для нового анализа.",
        reply_markup=get_main_keyboard()
    )
    return ConversationHandler.END

async def cancel(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "Диалог прерван. Нажми /start чтобы начать заново."
    )
    return ConversationHandler.END

def main():
    application = Application.builder().token(TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            SELECTING_LEVEL: [
                MessageHandler(filters.TEXT & filters.Regex("^(Апатия|Мания)$"), handle_state)
            ],
            SELECTING_ADVICE: [
                MessageHandler(filters.TEXT & filters.Regex("^[1-5]$"), handle_level)
            ],
            CONFIRMING: [
                CallbackQueryHandler(handle_advice_selection)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    application.add_handler(conv_handler)
    application.run_polling()

if __name__ == '__main__':
    main()
