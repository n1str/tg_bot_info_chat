#!/usr/bin/env python3
"""
Основной файл запуска телеграм-бота для извлечения участников чата.
"""

import logging
import os
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from bot.handlers import start, help_command, handle_documents, process_files_command
from config import Config

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    """Основная функция запуска бота."""
    # Проверка наличия токена
    if not Config.TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN не установлен в переменных окружения")
        exit(1)

    # Создание временной директории
    if not os.path.exists(Config.TEMP_DIR):
        os.makedirs(Config.TEMP_DIR)
        logger.info(f"Создана временная директория: {Config.TEMP_DIR}")

    # Создание приложения Telegram Bot
    application = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()

    # Регистрация обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("process", process_files_command))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_documents))

    # Запуск бота
    logger.info("Бот запущен и готов к работе...")
    application.run_polling()

if __name__ == "__main__":
    main()