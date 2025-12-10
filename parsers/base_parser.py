"""
Базовый парсер для файлов истории чатов Telegram.

Содержит абстрактный класс и общую логику для всех парсеров.
"""

import os
import json
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from models.user import TelegramUser

logger = logging.getLogger(__name__)

class BaseParser(ABC):
    """Абстрактный базовый класс для парсеров."""

    def __init__(self):
        self.users = {}  # Словарь для хранения уникальных пользователей: user_id -> TelegramUser

    @abstractmethod
    def parse(self, file_path: str) -> List[TelegramUser]:
        """Абстрактный метод для парсинга файла."""
        pass

    def _extract_user_from_message(self, message_data: Dict[str, Any]) -> TelegramUser:
        """Извлечение пользователя из данных сообщения."""
        try:
            user_data = message_data.get('from', {})

            # Проверка на удаленный аккаунт
            if user_data.get('id') == 'deleted_account':
                return TelegramUser(
                    user_id=0,
                    is_deleted=True,
                    username=None,
                    first_name="Deleted Account",
                    last_name=None
                )

            user = TelegramUser(
                user_id=user_data.get('id', 0),
                username=user_data.get('username'),
                first_name=user_data.get('first_name'),
                last_name=user_data.get('last_name'),
                bio=user_data.get('bio'),
                is_bot=user_data.get('is_bot', False)
            )

            return user
        except Exception as e:
            logger.error(f"Ошибка при извлечении пользователя из сообщения: {str(e)}")
            return None

    def _extract_mentioned_users(self, text: str) -> List[str]:
        """Извлечение упомянутых пользователей из текста."""
        mentioned = []
        if not text:
            return mentioned

        # Поиск упоминаний в формате @username
        words = text.split()
        for word in words:
            if word.startswith('@') and len(word) > 1:
                username = word[1:]
                # Простая проверка на валидность username (только буквы, цифры и подчеркивания)
                if username.replace('_', '').isalnum():
                    mentioned.append(username)

        return mentioned

    def _add_user(self, user: TelegramUser):
        """Добавление пользователя в словарь (без дублей)."""
        if user and not user.is_deleted:
            # Используем user_id как уникальный идентификатор
            self.users[user.user_id] = user

    def get_unique_users(self) -> List[TelegramUser]:
        """Получение списка уникальных пользователей."""
        return list(self.users.values())