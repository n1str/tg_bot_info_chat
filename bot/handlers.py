"""
Обработчики команд и сообщений для телеграм-бота.
"""

import os
import tempfile
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from config import Config
from processors.user_processor import UserProcessor
from processors.export_processor import ExportProcessor

# Настройка логирования
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start."""
    await update.message.reply_text(Config.WELCOME_MESSAGE)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help."""
    await update.message.reply_text(Config.HELP_MESSAGE)

async def handle_documents(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик загруженных документов."""
    try:
        # Проверка наличия документа
        document = update.message.document
        if not document:
            await update.message.reply_text("❌ Пожалуйста, загрузите файл истории чата.")
            return

        # Проверка на максимальное количество файлов (теперь обрабатываем по одному)
        documents = [document]

        # Проверка на максимальное количество файлов (теперь обрабатываем по одному)
        # if len(documents) > Config.MAX_FILES:
        #     await update.message.reply_text(Config.TOO_MANY_FILES)
        #     return

        # Сообщение о начале обработки
        processing_msg = await update.message.reply_text(Config.PROCESSING_MESSAGE)

        # Создание временной директории для файлов
        temp_dir = tempfile.mkdtemp(dir=Config.TEMP_DIR)
        file_paths = []

        try:
            # Загрузка и сохранение файла
            doc = documents[0]
            # Проверка размера файла
            if doc.file_size > Config.MAX_FILE_SIZE:
                await update.message.reply_text(Config.FILE_TOO_LARGE)
                return

            # Проверка формата файла
            if not (doc.file_name.endswith('.json') or doc.file_name.endswith('.html') or doc.file_name.endswith('.zip')):
                await update.message.reply_text(Config.UNSUPPORTED_FORMAT)
                return

            # Загрузка файла
            file = await doc.get_file()
            file_path = os.path.join(temp_dir, doc.file_name)

            # Сохранение файла
            await file.download_to_drive(file_path)
            file_paths.append(file_path)
            logger.info(f"Файл сохранен: {file_path}")

            if not file_paths:
                await update.message.reply_text("❌ Файл не подходит для обработки.")
                return

            # Обработка файлов
            user_processor = UserProcessor()
            users = user_processor.process_files(file_paths)

            # Формирование результата
            export_processor = ExportProcessor()
            result_file = export_processor.generate_export(users)

            # Отправка результата пользователю
            if result_file:
                if result_file.endswith('.xlsx'):
                    with open(result_file, 'rb') as f:
                        await update.message.reply_document(
                            document=f,
                            filename=os.path.basename(result_file),
                            caption=Config.RESULT_MESSAGE
                        )
                else:
                    with open(result_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        await update.message.reply_text(f"{Config.RESULT_MESSAGE}\n\n{content}")
            else:
                await update.message.reply_text("❌ Не удалось сформировать результат.")

        finally:
            # Удаление временных файлов
            for file_path in file_paths:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"Временный файл удален: {file_path}")

            # Удаление временной директории
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)
                logger.info(f"Временная директория удалена: {temp_dir}")

            # Удаление сообщения о обработке
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=processing_msg.message_id
            )

    except Exception as e:
        logger.error(f"Ошибка при обработке документов: {str(e)}", exc_info=True)
        await update.message.reply_text(Config.ERROR_MESSAGE.format(str(e)))