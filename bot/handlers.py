"""
Обработчики команд и сообщений для телеграм-бота.
"""

import os
import tempfile
import logging
import zipfile
import shutil
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from config import Config
from processors.user_processor import UserProcessor
from processors.export_processor import ExportProcessor

# Настройка логирования
logger = logging.getLogger(__name__)

# Хранилище для файлов пользователя (для поддержки нескольких файлов)
user_files = {}

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

        user_id = update.effective_user.id
        
        # Инициализация списка файлов для пользователя
        if user_id not in user_files:
            user_files[user_id] = {
                'documents': [],
                'temp_dir': None,
                'processing_msg': None
            }

        # Проверка размера файла
        if document.file_size > Config.MAX_FILE_SIZE:
            await update.message.reply_text(Config.FILE_TOO_LARGE)
            return

        # Проверка формата файла
        if not (document.file_name.endswith('.json') or 
                document.file_name.endswith('.html') or 
                document.file_name.endswith('.zip')):
            await update.message.reply_text(Config.UNSUPPORTED_FORMAT)
            return

        # Добавление файла в список
        user_files[user_id]['documents'].append(document)
        
        # Проверка на максимальное количество файлов
        if len(user_files[user_id]['documents']) > Config.MAX_FILES:
            await update.message.reply_text(Config.TOO_MANY_FILES)
            user_files[user_id]['documents'].pop()  # Удаляем последний файл
            return

        # Сообщение о загрузке файла
        files_count = len(user_files[user_id]['documents'])
        if files_count == 1:
            processing_msg = await update.message.reply_text(
                f"📎 Файл загружен. Можно загрузить еще до {Config.MAX_FILES} файлов. "
                f"Отправьте команду /process для обработки или загрузите еще файлы."
            )
            user_files[user_id]['processing_msg'] = processing_msg
        else:
            await update.message.reply_text(
                f"📎 Загружено файлов: {files_count}/{Config.MAX_FILES}. "
                f"Отправьте команду /process для обработки или загрузите еще файлы."
            )

    except Exception as e:
        logger.error(f"Ошибка при загрузке документов: {str(e)}", exc_info=True)
        await update.message.reply_text(Config.ERROR_MESSAGE.format(str(e)))

async def process_files_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /process для обработки загруженных файлов."""
    try:
        user_id = update.effective_user.id
        
        # Проверка наличия файлов
        if user_id not in user_files or not user_files[user_id]['documents']:
            await update.message.reply_text(
                "❌ Нет загруженных файлов для обработки.\n\n"
                "📎 Загрузите файлы истории чата, затем отправьте команду /process"
            )
            return

        documents = user_files[user_id]['documents']
        
        # Сообщение о начале обработки
        processing_msg = await update.message.reply_text(
            f"⏳ Обработка {len(documents)} файл(ов)... Пожалуйста, подождите."
        )

        # Создание временной директории для файлов
        temp_dir = tempfile.mkdtemp(dir=Config.TEMP_DIR)
        user_files[user_id]['temp_dir'] = temp_dir
        file_paths = []

        try:
            # Загрузка и сохранение файлов
            for doc in documents:
                # Загрузка файла
                file = await doc.get_file()
                file_path = os.path.join(temp_dir, doc.file_name)
                
                # Сохранение файла
                await file.download_to_drive(file_path)
                file_paths.append(file_path)
                logger.info(f"Файл сохранен: {file_path}")

            if not file_paths:
                await update.message.reply_text("❌ Файлы не подходят для обработки.")
                return

            # Обработка файлов (включая ZIP архивы)
            user_processor = UserProcessor()
            users = user_processor.process_files(file_paths)

            # Проверка на пустой результат
            if not users:
                await update.message.reply_text(
                    "⚠️ Участники не найдены. Возможные причины:\n"
                    "• Файлы не содержат сообщений\n"
                    "• Формат файлов не соответствует экспорту Telegram\n"
                    "• Все участники были удалены\n\n"
                    "Проверьте файлы и попробуйте снова."
                )
                return

            # Формирование результата
            export_processor = ExportProcessor()
            result_file = export_processor.generate_export(users)

            # Отправка результата пользователю
            if result_file:
                try:
                    if result_file.endswith('.xlsx'):
                        with open(result_file, 'rb') as f:
                            await update.message.reply_document(
                                document=f,
                                filename=os.path.basename(result_file),
                                caption=f"{Config.RESULT_MESSAGE}\nНайдено участников: {len(users)}"
                            )
                    else:
                        with open(result_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                        await update.message.reply_text(
                            f"{Config.RESULT_MESSAGE}\nНайдено участников: {len(users)}\n\n{content}"
                        )
                    
                    # Удаление временного файла результата
                    if os.path.exists(result_file):
                        os.remove(result_file)
                except Exception as e:
                    logger.error(f"Ошибка при отправке результата: {str(e)}")
                    await update.message.reply_text(
                        f"❌ Ошибка при отправке результата: {str(e)}\n"
                        f"Найдено участников: {len(users)}"
                    )
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
                try:
                    shutil.rmtree(temp_dir)  # Используем rmtree для рекурсивного удаления
                    logger.info(f"Временная директория удалена: {temp_dir}")
                except Exception as e:
                    logger.warning(f"Не удалось удалить директорию {temp_dir}: {str(e)}")

            # Очистка данных пользователя
            if user_id in user_files:
                del user_files[user_id]

            # Удаление сообщения о обработке
            try:
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=processing_msg.message_id
                )
            except Exception as e:
                logger.warning(f"Не удалось удалить сообщение: {str(e)}")

    except Exception as e:
        logger.error(f"Ошибка при обработке документов: {str(e)}", exc_info=True)
        await update.message.reply_text(Config.ERROR_MESSAGE.format(str(e)))
        # Очистка данных пользователя в случае ошибки
        if user_id in user_files:
            del user_files[user_id]