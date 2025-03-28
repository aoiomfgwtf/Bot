import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackContext,
    filters,
    ConversationHandler
)
import pandas as pd
import os

# Настройки
TOKEN = "7587845741:AAE54-7FfJTcECoPwfVg-rEHttFrkK9IkSM"  # Замените на свой токен!
DATA_FILE = "user_data.csv"

# Инициализация файла данных
if not os.path.exists(DATA_FILE):
    df = pd.DataFrame(columns=["user_id", "date", "state", "level", "action"])
    df.to_csv(DATA_FILE, index=False)

# Клавиатуры
main_keyboard = ReplyKeyboardMarkup([["Апатия", "Мания"]], resize_keyboard=True)
level_keyboard = ReplyKeyboardMarkup([[str(i) for i in range(1,6)]], resize_keyboard=True)

async def start(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "Привет! Я помогу тебе отслеживать твое состояние.\n"
        "Выбери текущее состояние:",
        reply_markup=main_keyboard
    )

async def handle_state(update: Update, context: CallbackContext):
    state = update.message.text
    context.user_data['current_state'] = state
    await update.message.reply_text(
        f"Вы выбрали {state}. Какой уровень? (1-5):",
        reply_markup=level_keyboard
    )

async def handle_level(update: Update, context: CallbackContext):
    level = int(update.message.text)
    state = context.user_data.get('current_state', 'unknown')
    
    # Сохраняем данные
    user_id = update.effective_user.id
    date = update.message.date
    new_entry = pd.DataFrame([[user_id, date, state, level, ""]], 
                           columns=["user_id", "date", "state", "level", "action"])
    new_entry.to_csv(DATA_FILE, mode='a', header=False, index=False)
    
    # Отправляем рекомендации
    recommendations = get_recommendations(state, level)
    await update.message.reply_text(
        recommendations + "-",
        reply_markup=main_keyboard
    )

def get_recommendations(state, level):
    if state == "Апатия":
        return {
            1: "Отличное состояние! Поддержи его легкой активностью.",
            2: "Попробуй послушать музыку или выпей воды.",
            3: "Прими душ, выпей энергос",
            4: "Нужно что-то активное, поиграй на гитаре, сделай что-то руками (уборка и т.д.).",
            5: "То, что ты чувствуешь это временно, дай эмоциям выйти, спокойнее бро"
        }.get(level, "Неизвестный уровень")
    
    elif state == "Мания":
        return {
            1: "Легкое возбуждение - может быть полезно для работы.",
            2: "Сфокусируй энергию на одном деле, избегай многозадачности.",
            3: "Попей воды, скушай вкусняхи, нужно успокоиться",
            4: "Включи тупой видос, просто ляг и ничего не делай.",
            5: "Немедленно остановись. Прими успокоительное, если нужно. Выдохни, все пройдет бро"
        }.get(level, "Неизвестный уровень")
    
    return "Неизвестное состояние"

async def cancel(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "Диалог прерван. Нажми /start чтобы начать заново.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

def main():
    # Создаем Application
    application = Application.builder().token(TOKEN).build()
    
    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex("^(Апатия|Мания)$"), handle_state))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex("^[1-5]$"), handle_level))
    
    # Запускаем бота
    application.run_polling()

if __name__ == '__main__':
    main()