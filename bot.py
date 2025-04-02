import os
import json
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

# Загрузка конфига
TOKEN = os.getenv("TOKEN")
with open("advices.json", "r", encoding="utf-8") as f:
    ADVICES = json.load(f)

# Клавиатуры
main_kb = ReplyKeyboardMarkup([["Апатия", "Мания"]], resize_keyboard=True)
level_kb = ReplyKeyboardMarkup([[str(i) for i in range(1, 6)]], resize_keyboard=True)

async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("Выбери состояние:", reply_markup=main_kb)

async def handle_state(update: Update, context: CallbackContext):
    state = update.message.text
    context.user_data["state"] = state
    await update.message.reply_text(f"Уровень (1-5):", reply_markup=level_kb)

async def handle_level(update: Update, context: CallbackContext):
    level = update.message.text
    state = context.user_data["state"]
    advice = ADVICES["states"][state][level]
    
    text = (
        f"{advice['description']}\n\n"
        f"⚠️ Риск: {advice['risk']}\n\n"
        "Советы:\n" + "\n".join(f"• {a}" for a in advice['advices'])
    )
    await update.message.reply_text(text)

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^(Апатия|Мания)$"), handle_state))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^[1-5]$"), handle_level))
    app.run_polling()

if __name__ == "__main__":
    main()
