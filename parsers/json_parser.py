"""
Парсер для JSON файлов истории чатов Telegram.

Обрабатывает экспортированные JSON файлы из Telegram.
"""

import json
import logging
from typing import List, Dict, Any
from parsers.base_parser import BaseParser
from models.user import TelegramUser

logger = logging.getLogger(__name__)

class JSONParser(BaseParser):
    """Парсер для JSON файлов истории чатов."""

    def parse(self, file_path: str) -> List[TelegramUser]:
        """Парсинг JSON файла истории чата."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Обработка сообщений
            messages = data.get('messages', [])
            for message in messages:
                # Извлечение автора сообщения
                if 'from' in message:
                    user = self._extract_user_from_message(message)
                    if user:
                        self._add_user(user)

                # Извлечение упомянутых пользователей
                if 'text' in message:
                    mentioned_users = self._extract_mentioned_users(message['text'])
                    for username in mentioned_users:
                        # Создаем временного пользователя для упоминаний
                        # В реальности нужно будет получить полные данные
                        temp_user = TelegramUser(
                            user_id=hash(username),  # Временный ID
                            username=username,
                            first_name=None,
                            last_name=None
                        )
                        self._add_user(temp_user)

            return self.get_unique_users()

        except json.JSONDecodeError as e:
            logger.error(f"Ошибка декодирования JSON: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Ошибка при парсинге JSON файла {file_path}: {str(e)}")
            return []

    def get_unique_users(self) -> List[TelegramUser]:
        """Получение списка уникальных пользователей из JSON."""
        # В реальной реализации нужно будет получить полные данные пользователей
        # Здесь возвращаем пустой список для демонстрации
        return []