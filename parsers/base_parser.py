"""
Базовый парсер для файлов истории чатов Telegram.

Содержит абстрактный класс и общую логику для всех парсеров.
"""

import os
import json
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
from models.user import TelegramUser

logger = logging.getLogger(__name__)

class BaseParser(ABC):
    """Абстрактный базовый класс для парсеров."""

    def __init__(self):
        self.users = {}  # Словарь для хранения уникальных пользователей: user_id -> TelegramUser
        self.user_first_message_date = {}  # user_id -> самая ранняя дата сообщения

    @abstractmethod
    def parse(self, file_path: str) -> List[TelegramUser]:
        """Абстрактный метод для парсинга файла."""
        pass

    def _extract_user_from_message(self, message_data: Dict[str, Any], message_date: Optional[datetime] = None) -> TelegramUser:
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

            user_id = user_data.get('id', 0)
            bio = user_data.get('bio', '')
            
            # Определение наличия канала в профиле
            has_channel = self._detect_channel_in_profile(bio, user_data)

            user = TelegramUser(
                user_id=user_id,
                username=user_data.get('username'),
                first_name=user_data.get('first_name'),
                last_name=user_data.get('last_name'),
                bio=bio,
                is_bot=user_data.get('is_bot', False),
                has_channel=has_channel
            )

            # Сохранение даты первого сообщения для оценки даты регистрации
            if message_date and user_id:
                if user_id not in self.user_first_message_date:
                    self.user_first_message_date[user_id] = message_date
                elif message_date < self.user_first_message_date[user_id]:
                    self.user_first_message_date[user_id] = message_date

            return user
        except Exception as e:
            logger.error(f"Ошибка при извлечении пользователя из сообщения: {str(e)}")
            return None

    def _detect_channel_in_profile(self, bio: Optional[str], user_data: Dict[str, Any]) -> Optional[bool]:
        """Определение наличия канала в профиле пользователя."""
        if not bio:
            return None
        
        bio_lower = bio.lower()
        
        # Проверка на упоминания каналов в bio
        channel_keywords = ['канал', 'channel', 't.me/', 'telegram.me/', '@']
        
        # Проверяем наличие ссылок на каналы
        if any(keyword in bio_lower for keyword in channel_keywords):
            # Проверяем, что это не просто упоминание другого пользователя
            if 't.me/' in bio or 'telegram.me/' in bio:
                return True
        
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
            user_id = user.user_id
            # Используем user_id как уникальный идентификатор
            if user_id in self.users:
                # Обновляем существующего пользователя
                existing_user = self.users[user_id]
                # Обновляем дату регистрации если она раньше
                if user_id in self.user_first_message_date:
                    existing_user.registration_date = self.user_first_message_date[user_id]
                # Обновляем наличие канала
                if user.has_channel is not None:
                    existing_user.has_channel = user.has_channel
                # Обновляем другие поля если они отсутствуют
                if not existing_user.username and user.username:
                    existing_user.username = user.username
                if not existing_user.first_name and user.first_name:
                    existing_user.first_name = user.first_name
                if not existing_user.last_name and user.last_name:
                    existing_user.last_name = user.last_name
                if not existing_user.bio and user.bio:
                    existing_user.bio = user.bio
            else:
                # Добавляем нового пользователя
                if user_id in self.user_first_message_date:
                    user.registration_date = self.user_first_message_date[user_id]
                self.users[user_id] = user

    def get_unique_users(self) -> List[TelegramUser]:
        """Получение списка уникальных пользователей."""
        # Убеждаемся, что у всех пользователей установлена дата регистрации
        for user_id, user in self.users.items():
            if user_id in self.user_first_message_date and not user.registration_date:
                user.registration_date = self.user_first_message_date[user_id]
        return list(self.users.values())