"""
Процессор пользовательских данных.

Обрабатывает файлы истории чатов и извлекает уникальных пользователей.
"""

import os
import logging
import zipfile
import tempfile
from typing import List, Dict
from parsers.json_parser import JSONParser
from parsers.html_parser import HTMLParser
from models.user import TelegramUser

logger = logging.getLogger(__name__)

class UserProcessor:
    """Процессор для извлечения пользователей из файлов истории чатов."""

    def __init__(self):
        self.users = {}  # user_id -> TelegramUser
        self.mentioned_users = set()  # username упомянутых пользователей

    def process_files(self, file_paths: List[str]) -> List[TelegramUser]:
        """Обработка списка файлов и извлечение пользователей."""
        try:
            extracted_files = []
            
            for file_path in file_paths:
                if not os.path.exists(file_path):
                    logger.warning(f"Файл не найден: {file_path}")
                    continue

                # Обработка ZIP архивов
                if file_path.endswith('.zip'):
                    extracted = self._extract_zip(file_path)
                    extracted_files.extend(extracted)
                else:
                    extracted_files.append(file_path)

            # Проверка на наличие файлов для обработки
            if not extracted_files:
                logger.warning("Нет файлов для обработки")
                return []

            # Обработка всех файлов (включая извлеченные из ZIP)
            for file_path in extracted_files:
                try:
                    # Определение типа файла и выбор парсера
                    if file_path.endswith('.json'):
                        parser = JSONParser()
                    elif file_path.endswith('.html'):
                        parser = HTMLParser()
                    else:
                        logger.warning(f"Неподдерживаемый формат файла: {file_path}")
                        continue

                    # Парсинг файла
                    users = parser.parse(file_path)
                    if users:
                        self._merge_users(users)
                        logger.info(f"Обработан файл {file_path}: найдено {len(users)} пользователей")
                    else:
                        logger.warning(f"Файл {file_path} не содержит пользователей")
                except Exception as e:
                    logger.error(f"Ошибка при обработке файла {file_path}: {str(e)}")
                    continue

            # Преобразование в список и удаление дублей
            result = list(self.users.values())
            logger.info(f"Всего найдено уникальных пользователей: {len(result)}")
            return result

        except Exception as e:
            logger.error(f"Ошибка при обработке файлов: {str(e)}", exc_info=True)
            return []

    def _extract_zip(self, zip_path: str) -> List[str]:
        """Извлечение файлов из ZIP архива."""
        extracted_files = []
        extract_dir = None
        try:
            # Создаем временную директорию для извлечения
            extract_dir = tempfile.mkdtemp()
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Проверка на пустой архив
                if not zip_ref.namelist():
                    logger.warning(f"ZIP архив пуст: {zip_path}")
                    return []
                
                # Извлекаем все файлы
                zip_ref.extractall(extract_dir)
                
                # Находим все JSON и HTML файлы
                for root, dirs, files in os.walk(extract_dir):
                    for file in files:
                        if file.endswith('.json') or file.endswith('.html'):
                            file_path = os.path.join(root, file)
                            extracted_files.append(file_path)
                            logger.info(f"Извлечен файл из ZIP: {file_path}")
                
                if not extracted_files:
                    logger.warning(f"В ZIP архиве {zip_path} не найдено JSON или HTML файлов")
            
            return extracted_files
            
        except zipfile.BadZipFile:
            logger.error(f"Некорректный ZIP архив: {zip_path}")
            return []
        except zipfile.LargeZipFile:
            logger.error(f"ZIP архив слишком большой: {zip_path}")
            return []
        except Exception as e:
            logger.error(f"Ошибка при извлечении ZIP архива {zip_path}: {str(e)}")
            return []
        finally:
            # Очистка временной директории будет выполнена в handlers.py
            pass

    def _merge_users(self, users: List[TelegramUser]):
        """Объединение пользователей с удалением дублей."""
        for user in users:
            if not user or user.is_deleted:
                continue

            # Используем user_id как уникальный ключ
            if user.user_id not in self.users:
                self.users[user.user_id] = user
            else:
                # Обновление существующего пользователя
                existing_user = self.users[user.user_id]
                # ВСЕГДА обновляем username если он есть
                if user.username:
                    existing_user.username = user.username
                if user.first_name and not existing_user.first_name:
                    existing_user.first_name = user.first_name
                if user.last_name and not existing_user.last_name:
                    existing_user.last_name = user.last_name

    def get_unique_users(self) -> List[TelegramUser]:
        """Получение списка уникальных пользователей."""
        return list(self.users.values())

    def get_mentioned_users(self) -> List[str]:
        """Получение списка упомянутых пользователей."""
        return list(self.mentioned_users)