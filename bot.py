import os
import logging
from datetime import datetime
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
TOKEN = os.getenv("TOKEN") or "7587845741:AAE54-7FfJTcECoPwfVg-rEHttFrkK9IkSM"

# Полные данные для всех состояний (как вы просили)
ADVICES = {
    "Апатия": {
        "1": {
            "description": "Отличное состояние! Поддержи его легкой активностью.",
            "advices": [
                "Короткая прогулка",
                "Прослушивание бодрой музыки",
                "Легкая растяжка"
            ],
            "risk": "Риск минимален. Состояние близко к балансу."
        },
        "2": {
            "description": "Выпей воды. Послушай музыку. Включи смешное видео. Есть риск провалиться глубже в мысли.",
            "advices": [
                "Выпей воды",
                "Послушай музыку",
                "Включи смешное видео",
                "Позвони другу (даже без причины)"
            ],
            "risk": "Начинается потеря энергии. Важно мягкое вовлечение."
        },
        "3": {
            "description": "Выпей кофе или энергетик. Прими горячий душ. Сделай что-то руками (уборка).",
            "advices": [
                "Выпей кофе или энергетик",
                "Прими горячий душ",
                "Сделай что-то руками (уборка, рисование)",
                "Напиши поток сознания на бумагу"
            ],
            "risk": "Средняя перегрузка. Тело сопротивляется действиям."
        },
        "4": {
            "description": "Необходимо с кем-то поговорить. Выйди на улицу и уйди далеко от дома.",
            "advices": [
                "Поговори с кем-то (о чём угодно)",
                "Выйди на улицу и уйди далеко от дома",
                "Крик в подушку",
                "Прими контрастный душ"
            ],
            "risk": "Высокая перегрузка. Возможны суицидальные мысли."
        },
        "5": {
            "description": "Настало время выплакаться и выплеснуть эмоции. Состояние критическое, но в этом и выход.",
            "advices": [
                "Выплачься (включи грустную музыку/фильм)",
                "Выплесни злость (бей подушку, рви бумагу)",
                "Экстренный звонок доверенному лицу",
                "Если есть препараты — прими (по рецепту)"
            ],
            "risk": "Кризис. Требуется внешняя помощь."
        }
    },
    "Мания": {
        "1": {
            "description": "Легкое возбуждение - может быть полезно для работы.",
            "advices": [
                "Направь энергию на 1 важное дело",
                "Запиши идеи, чтобы не забыть",
                "Сделай быструю разминку"
            ],
            "risk": "Риск минимален. Энергия под контролем."
        },
        "2": {
            "description": "Сфокусируй энергию на одном деле, избегай многозадачности.",
            "advices": [
                "Сфокусируйся на одном деле",
                "Избегай многозадачности",
                "Пей воду маленькими глотками"
            ],
            "risk": "Лёгкая перегрузка. Возможна тревожность."
        },
        "3": {
            "description": "Выпей воды. Поешь вкусняшек. Просто приляг и ничего не делай.",
            "advices": [
                "Выпей воды",
                "Поешь вкусняшек",
                "Приляг на 10 минут",
                "Включи белый шум"
            ],
            "risk": "Средняя перегрузка. Может начаться тремор."
        },
        "4": {
            "description": "Время лечь и ничего не делать, совсем. Включи тупой видос.",
            "advices": [
                "Ляг и ничего не делай",
                "Включи «тупой» видеоролик",
                "Дыхание 4-7-8 (вдох-задержка-выдох)",
                "Холодные ладони на лицо"
            ],
            "risk": "Высокая перегрузка. Риск иррациональных решений."
        },
        "5": {
            "description": "Состояние критическое. Немедленно остановись.",
            "advices": [
                "Немедленно остановись",
                "Прими успокоительное (если прописано)",
                "Вызови друга/родственника",
                "Горячее сладкое питьё"
            ],
            "risk": "Кризис. Возможны истерика, агрессия или ступор."
        }
    }
}

# Файл для статистики
STATS_FILE = "stats.json"

# Загрузка/сохранение статистики
def load_stats():
    try:
        if os.path.exists(STATS_FILE):
            with open(STATS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}
    except:
        return {}

def save_stats(stats):
    try:
        with open(STATS_FILE, "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        return True
    except:
        return False

# Клавиатуры
def main_kb():
    return ReplyKeyboardMarkup([
        ["Апатия", "Мания"],
        ["📊 Статистика"]
    ], resize_keyboard=True)

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

async def show_stats(update: Update, context: CallbackContext):
    stats = load_stats()
    if not stats:
        await update.message.reply_text("📊 Статистика пока пуста")
        return
    
    stats_text = "📊 История состояний:\n\n"
    for entry_id, entry in stats.items():
        stats_text += (
            f"📅 {entry['date']}\n"
            f"• Состояние: {entry['state']} (уровень {entry['level']})\n"
            f"• Помогло: {entry.get('helped', 'не указано')}\n"
            f"• Риск: {entry['risk']}\n\n"
        )
    
    await update.message.reply_text(stats_text)
    await update.message.reply_text(
        "Выбери состояние:",
        reply_markup=main_kb()
    )
    return SELECT_STATE

async def handle_state(update: Update, context: CallbackContext):
    text = update.message.text
    
    if text == "📊 Статистика":
        return await show_stats(update, context)
        
    if text not in ADVICES:
        await update.message.reply_text("Ошибка: выбери Апатия или Мания")
        return SELECT_STATE
    
    context.user_data['state'] = text
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
    context.user_data['current_advice'] = {
        "advice": advice,
        "state": state,
        "level": level,
        "date": datetime.now().strftime("%d.%m.%Y %H:%M")
    }
    
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
    
    current_data = context.user_data.get('current_advice', {})
    advice = current_data.get("advice", {})
    choice = query.data
    
    # Обновляем статистику
    stats = load_stats()
    entry_id = f"{current_data['state']}_{current_data['level']}_{datetime.now().timestamp()}"
    
    if choice == "help_none":
        stats[entry_id] = {
            "date": current_data["date"],
            "state": current_data["state"],
            "level": current_data["level"],
            "risk": advice["risk"],
            "helped": "ничего"
        }
        await query.edit_message_text("🔄 Попробуем другие методы в следующий раз.")
    else:
        try:
            idx = int(choice.split("_")[1])
            helped_advice = advice['advices'][idx]
            stats[entry_id] = {
                "date": current_data["date"],
                "state": current_data["state"],
                "level": current_data["level"],
                "risk": advice["risk"],
                "helped": helped_advice
            }
            await query.edit_message_text(f"✅ Запомнил: '{helped_advice}' помог.")
        except:
            await query.edit_message_text("⚠️ Ошибка обработки выбора")
    
    save_stats(stats)
    
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
    if not TOKEN or TOKEN == "7587845741:AAE54-7FfJTcECoPwfVg-rEHttFrkK9IkSM":
        print("❌ ОШИБКА: Токен не установлен!")
        return
    
    application = Application.builder().token(TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            SELECT_STATE: [
                MessageHandler(filters.TEXT & filters.Regex("^(Апатия|Мания)$"), handle_state),
                MessageHandler(filters.TEXT & filters.Regex("^📊 Статистика$"), show_stats)
            ],
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
    import json  # Добавлено для работы с JSON
    main()
