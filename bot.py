import os
import logging
import json
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

# Полные данные для всех состояний
ADVICES = {
    "Апатия": {
        "1": {
            "description": "Отличное состояние! Поддержи его легкой активностью.",
            "advices": ["Прогулка", "Музыка", "Вода"],
            "risk": "Низкий риск"
        },
        # ... остальные уровни апатии
    },
    "Мания": {
        "1": {
            "description": "Легкое возбуждение - может быть полезно для работы.",
            "advices": ["Фокусировка", "Запись идей", "Разминка"],
            "risk": "Низкий риск"
        },
        # ... остальные уровни мании
    }
}

# Файл для статистики
STATS_FILE = "/data/stats.json"  # Используем /data для Railway

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

# ... (остальные функции: main_kb, level_kb, feedback_kb)

async def start(update: Update, context: CallbackContext):
    try:
        await update.message.reply_text(
            "📊 Выбери текущее состояние:",
            reply_markup=main_kb()
        )
        return SELECT_STATE
    except Exception as e:
        logger.error(f"Ошибка в start: {e}")
        raise

# ... (остальные обработчики: handle_state, handle_level, handle_feedback)

def main():
    try:
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
        
        logger.info("✅ Бот запускается...")
        application.run_polling()
    except Exception as e:
        logger.critical(f"❌ Критическая ошибка: {e}")
        raise

if __name__ == '__main__':
    main()
