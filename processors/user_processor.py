"""
Процессор пользовательских данных.

Обрабатывает файлы истории чатов и извлекает уникальных пользователей.
"""

import os
import logging
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
            for file_path in file_paths:
                if not os.path.exists(file_path):
                    logger.warning(f"Файл не найден: {file_path}")
                    continue

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
                self._merge_users(users)

            # Преобразование в список и удаление дублей
            return list(self.users.values())

        except Exception as e:
            logger.error(f"Ошибка при обработке файлов: {str(e)}", exc_info=True)
            return []

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
                if user.username and not existing_user.username:
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