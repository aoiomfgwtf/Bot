import os
import logging
import json
from datetime import datetime, timezone, timedelta
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
SELECT_TIMEZONE, SELECT_STATE, SELECT_LEVEL, FEEDBACK = range(4)

# Получаем токен из переменных окружения
TOKEN = os.environ.get('TOKEN')
if not TOKEN:
    logger.error("❌ Токен не найден в переменных окружения!")
    raise ValueError("Токен бота не установлен. Добавьте переменную TOKEN в настройки Railway")

# Проверка формата токена
if ':' not in TOKEN:
    logger.error(f"❌ Неверный формат токена: {TOKEN[:5]}...")
    raise ValueError("Неверный формат токена. Должен быть в формате '123456789:ABCdefGHIJK...'")

logger.info(f"✅ Токен получен (первые 5 символов): {TOKEN[:5]}...")

# Полные данные для всех состояний с улучшенными советами
ADVICES = {
    "Апатия": {
        "1": {
            "description": "Отличное состояние! Поддержи его легкой активностью.",
            "advices": ["Короткая прогулка", "Прослушивание бодрой музыки", "Легкая растяжка"],
            "risk": "Риск минимален. Состояние близко к балансу."
        },
        "2": {
            "description": "Выпей воды. Послушай музыку. Включи смешное видео. Есть риск провалиться глубже в мысли.",
            "advices": ["Выпить воды", "Послушать музыку", "Посмотреть смешное видео", "Позвонить другу"],
            "risk": "Начинается потеря энергии. Важно мягкое вовлечение."
        },
        "3": {
            "description": "Выпей кофе или энергетик. Прими горячий душ. Сделай что-то руками (уборка).",
            "advices": ["Выпить кофе/энергетик", "Принять горячий душ", "Заняться уборкой", "Написать поток сознания на бумагу"],
            "risk": "Средняя перегрузка. Тело сопротивляется действиям."
        },
        "4": {
            "description": "Необходимо с кем-то поговорить. Выйди на улицу и уйди далеко от дома.",
            "advices": ["Поговорить с кем-то", "Пройтись на улице", "Крикнуть в подушку", "Принять контрастный душ"],
            "risk": "Высокая перегрузка. Возможны суицидальные мысли."
        },
        "5": {
            "description": "Настало время выплакаться и выплеснуть эмоции. Состояние критическое, но в этом и выход.",
            "advices": ["Выплакаться", "Выплеснуть злость (подушка, бумага)", "Экстренный звонок доверенному лицу", "Принять прописанные препараты"],
            "risk": "Кризис. Требуется внешняя помощь."
        }
    },
    "Мания": {
        "1": {
            "description": "Легкое возбуждение - может быть полезно для работы.",
            "advices": ["Направить энергию на важное дело", "Записать идеи", "Сделать разминку"],
            "risk": "Риск минимален. Энергия под контролем."
        },
        "2": {
            "description": "Сфокусируй энергию на одном деле, избегай многозадачности.",
            "advices": ["Сфокусироваться на одном деле", "Выпить воды", "Съесть что-то вкусное"],
            "risk": "Лёгкая перегрузка. Возможна тревожность."
        },
        "3": {
            "description": "Выпей воды. Поешь вкусняшек. Просто приляг и ничего не делай.",
            "advices": ["Выпить воды", "Съесть что-то вкусное", "Прилечь на 10 минут", "Включить белый шум"],
            "risk": "Средняя перегрузка. Может начаться тремор."
        },
        "4": {
            "description": "Время лечь и ничего не делать, совсем. Включи тупой видос.",
            "advices": ["Лечь и ничего не делать", "Посмотреть простой видеоролик", "Дыхание 4-7-8", "Охладить лицо"],
            "risk": "Высокая перегрузка. Риск иррациональных решений."
        },
        "5": {
            "description": "Состояние критическое. Немедленно остановись.",
            "advices": ["Немедленно остановиться", "Принять успокоительное", "Вызвать друга/родственника", "Выпить горячий сладкий напиток"],
            "risk": "Кризис. Возможны истерика, агрессия или ступор."
        }
    }
}

# Файлы для данных
STATS_FILE = "/data/stats.json"
ADVICE_STATS_FILE = "/data/advice_stats.json"

def ensure_data_dir():
    """Создаем директорию для данных, если ее нет"""
    os.makedirs(os.path.dirname(STATS_FILE), exist_ok=True)

def load_stats():
    ensure_data_dir()
    try:
        if os.path.exists(STATS_FILE):
            with open(STATS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}
    except Exception as e:
        logger.error(f"Ошибка загрузки статистики: {e}")
        return {}

def save_stats(stats):
    try:
        ensure_data_dir()
        with open(STATS_FILE, "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Ошибка сохранения статистики: {e}")
        return False

def load_advice_stats():
    ensure_data_dir()
    try:
        if os.path.exists(ADVICE_STATS_FILE):
            with open(ADVICE_STATS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        
        # Инициализация статистики советов, если файла нет
        stats = {}
        for state, levels in ADVICES.items():
            stats[state] = {}
            for level, data in levels.items():
                stats[state][level] = {advice: 100 for advice in data["advices"]}
        return stats
    except Exception as e:
        logger.error(f"Ошибка загрузки статистики советов: {e}")
        return {}

def save_advice_stats(stats):
    try:
        ensure_data_dir()
        with open(ADVICE_STATS_FILE, "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Ошибка сохранения статистики советов: {e}")
        return False

def update_advice_stats(state, level, selected_index=None):
    """Обновляет статистику советов"""
    stats = load_advice_stats()
    
    try:
        if state not in stats:
            stats[state] = {}
        if level not in stats[state]:
            stats[state][level] = {a: 100 for a in ADVICES[state][level]["advices"]}
        
        current_stats = stats[state][level]
        
        if selected_index is not None:
            # Пользователь выбрал конкретный совет
            selected_advice = ADVICES[state][level]["advices"][selected_index]
            
            # Увеличиваем рейтинг выбранного совета (+10%, но не более 100)
            current_stats[selected_advice] = min(100, current_stats.get(selected_advice, 100) + 10)
            
            # Уменьшаем рейтинг остальных советов (-10%, но не менее 0)
            for advice in current_stats:
                if advice != selected_advice:
                    current_stats[advice] = max(0, current_stats.get(advice, 100) - 10)
        else:
            # Пользователь выбрал "Ничего не помогло"
            # Уменьшаем рейтинг всех советов (-10%, но не менее 0)
            for advice in current_stats:
                current_stats[advice] = max(0, current_stats.get(advice, 100) - 10
        
        stats[state][level] = current_stats
        save_advice_stats(stats)
        return True
    except Exception as e:
        logger.error(f"Ошибка обновления статистики советов: {e}")
        return False

# Клавиатуры
def main_kb():
    return ReplyKeyboardMarkup([
        ["Апатия", "Мания"],
        ["📊 Статистика"]
    ], resize_keyboard=True)

def timezone_kb():
    return ReplyKeyboardMarkup([
        ["+3 (Москва)", "+5 (Екатеринбург)"],
        ["0 (Лондон)", "-4 (Нью-Йорк)"],
        ["+8 (Пекин)", "+10 (Сидней)"]
    ], resize_keyboard=True)

def level_kb():
    return ReplyKeyboardMarkup([[str(i) for i in range(1, 6)]], resize_keyboard=True)

def feedback_kb(state, level):
    advice_stats = load_advice_stats()
    advices = ADVICES[state][level]["advices"]
    
    buttons = []
    for i, advice in enumerate(advices):
        effectiveness = advice_stats.get(state, {}).get(level, {}).get(advice, 100)
        text = f"{advice} ({effectiveness}%)"
        buttons.append([InlineKeyboardButton(text, callback_data=f"help_{i}")])
    
    buttons.append([InlineKeyboardButton("❌ Ничего не помогло", callback_data="help_none")])
    return InlineKeyboardMarkup(buttons)

# Обработчики команд
async def start(update: Update, context: CallbackContext):
    try:
        if 'timezone' not in context.user_data:
            await update.message.reply_text(
                "⏰ Пожалуйста, укажите ваш часовой пояс:",
                reply_markup=timezone_kb()
            )
            return SELECT_TIMEZONE
        
        await update.message.reply_text(
            "📊 Выбери текущее состояние:",
            reply_markup=main_kb()
        )
        return SELECT_STATE
    except Exception as e:
        logger.error(f"Ошибка в start: {e}")
        raise

async def handle_timezone(update: Update, context: CallbackContext):
    try:
        tz_text = update.message.text
        # Извлекаем число из текста (например, "+3 (Москва)" -> 3)
        tz = int(''.join(filter(str.isdigit, tz_text.split()[0])))
        if not -12 <= tz <= 14:
            raise ValueError
        
        context.user_data['timezone'] = tz
        await update.message.reply_text(
            f"⏰ Часовой пояс GMT{tz} сохранён!",
            reply_markup=main_kb()
        )
        return SELECT_STATE
    except (ValueError, TypeError):
        await update.message.reply_text(
            "❌ Неверный формат. Пожалуйста, выберите часовой пояс из предложенных:",
            reply_markup=timezone_kb()
        )
        return SELECT_TIMEZONE

async def show_stats(update: Update, context: CallbackContext):
    try:
        stats = load_stats()
        advice_stats = load_advice_stats()
        
        if not stats:
            await update.message.reply_text("📊 Статистика пока пуста")
            return SELECT_STATE
        
        stats_text = "📊 История состояний:\n\n"
        for entry_id, entry in stats.items():
            stats_text += (
                f"📅 {entry['date']}\n"
                f"• Состояние: {entry['state']} (уровень {entry['level']})\n"
                f"• Помогло: {entry.get('helped', 'не указано')}\n"
                f"• Риск: {entry['risk']}\n\n"
            )
        
        await update.message.reply_text(stats_text)
        
        # Показываем эффективность советов
        advice_text = "📊 Эффективность советов:\n\n"
        for state, levels in advice_stats.items():
            advice_text += f"🔹 {state}:\n"
            for level, advices in levels.items():
                advice_text += f"  Уровень {level}:\n"
                for advice, eff in advices.items():
                    advice_text += f"    • {advice}: {eff}%\n"
            advice_text += "\n"
        
        await update.message.reply_text(advice_text)
        
        await update.message.reply_text(
            "Выбери состояние:",
            reply_markup=main_kb()
        )
        return SELECT_STATE
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка загрузки статистики: {e}")
        logger.error(f"Ошибка в show_stats: {e}")
        return SELECT_STATE

async def handle_state(update: Update, context: CallbackContext):
    try:
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
    except Exception as e:
        logger.error(f"Ошибка в handle_state: {e}")
        await update.message.reply_text("⚠️ Произошла ошибка. Попробуй еще раз.")
        return SELECT_STATE

async def handle_level(update: Update, context: CallbackContext):
    try:
        level = update.message.text
        state = context.user_data.get('state')
        
        if not state or state not in ADVICES:
            await update.message.reply_text("Ошибка: состояние не выбрано. Начни с /start")
            return ConversationHandler.END
        
        if level not in ADVICES[state]:
            await update.message.reply_text("Ошибка: выбери уровень от 1 до 5")
            return SELECT_LEVEL
        
        advice = ADVICES[state][level]
        tz = context.user_data.get('timezone', 0)
        now = datetime.now(timezone(timedelta(hours=tz)))
        
        context.user_data['current_advice'] = {
            "advice": advice,
            "state": state,
            "level": level,
            "date": now.strftime("%d.%m.%Y %H:%M (GMT%z)")
        }
        
        # Загружаем статистику эффективности для этих советов
        advice_stats = load_advice_stats()
        current_stats = advice_stats.get(state, {}).get(level, {})
        
        # Формируем текст с эффективностью
        advice_text = (
            f"📌 {advice['description']}\n\n"
            f"⚠️ Уровень перегрузки: {advice['risk']}\n\n"
            "💡 Советы (эффективность):\n"
        )
        
        for a in advice['advices']:
            eff = current_stats.get(a, 100)
            advice_text += f"• {a} ({eff}%)\n"
        
        await update.message.reply_text(advice_text)
        await update.message.reply_text(
            "Что из этого помогло?",
            reply_markup=feedback_kb(state, level)
        )
        return FEEDBACK
    except Exception as e:
        logger.error(f"Ошибка в handle_level: {e}")
        await update.message.reply_text("⚠️ Произошла ошибка. Попробуй еще раз.")
        return SELECT_STATE

async def handle_feedback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    try:
        current_data = context.user_data.get('current_advice', {})
        advice = current_data.get("advice", {})
        choice = query.data
        
        # Обновляем основную статистику
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
            
            # Обновляем статистику советов (ничего не помогло)
            update_advice_stats(current_data['state'], current_data['level'])
            
            await query.edit_message_text("🔄 Попробуем другие методы в следующий раз.")
        else:
            idx = int(choice.split("_")[1])
            helped_advice = advice['advices'][idx]
            stats[entry_id] = {
                "date": current_data["date"],
                "state": current_data["state"],
                "level": current_data["level"],
                "risk": advice["risk"],
                "helped": helped_advice
            }
            
            # Обновляем статистику советов (выбранный совет помог)
            update_advice_stats(current_data['state'], current_data['level'], idx)
            
            await query.edit_message_text(f"✅ Запомнил: '{helped_advice}' помог.")
        
        save_stats(stats)
        
        # Возвращаем к началу
        await query.message.reply_text(
            "🔄 Хочешь проанализировать состояние снова?",
            reply_markup=main_kb()
        )
        return SELECT_STATE
    except Exception as e:
        logger.error(f"Ошибка в handle_feedback: {e}")
        await query.edit_message_text("⚠️ Произошла ошибка. Попробуй еще раз.")
        return SELECT_STATE

async def cancel(update: Update, context: CallbackContext):
    await update.message.reply_text("Диалог прерван. Нажми /start чтобы начать заново.")
    return ConversationHandler.END

def main():
    try:
        application = Application.builder().token(TOKEN).build()
        
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', start)],
            states={
                SELECT_TIMEZONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_timezone)],
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
        
        logger.info("✅ Бот запускается...")
        application.run_polling()
    except Exception as e:
        logger.critical(f"❌ Критическая ошибка: {e}")
        raise

if __name__ == '__main__':
    main()
