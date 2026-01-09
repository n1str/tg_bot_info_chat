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
        self.user_first_message_id = {}  # user_id -> ID первого сообщения
        self.user_first_reaction_date = {}  # user_id -> самая ранняя дата реакции
        self.user_first_reaction_emoji = {}  # user_id -> эмодзи первой реакции

    @abstractmethod
    def parse(self, file_path: str) -> List[TelegramUser]:
        """Абстрактный метод для парсинга файла."""
        pass

    def _extract_user_from_message(self, message_data: Dict[str, Any], message_date: Optional[datetime] = None, message_id: Optional[int] = None) -> TelegramUser:
        """Извлечение пользователя из данных сообщения."""
        try:
            # Поле from может быть строкой или объектом
            from_field = message_data.get('from')
            from_id_field = message_data.get('from_id')
            
            # Если from - строка, это имя пользователя, нужно получить ID из from_id
            if isinstance(from_field, str):
                # from - это имя пользователя (строка)
                full_name = from_field
                
                # Извлекаем ID из from_id
                if isinstance(from_id_field, str):
                    # Формат: "user710608950" или "channel1679993617"
                    if from_id_field.startswith('user'):
                        user_id = int(from_id_field.replace('user', ''))
                        is_bot = False
                    elif from_id_field.startswith('channel'):
                        # Это канал, пропускаем
                        return None
                    else:
                        user_id = hash(from_id_field)
                        is_bot = False
                else:
                    user_id = hash(full_name)
                    is_bot = False
                
                # Разделяем имя на first_name и last_name
                name_parts = full_name.split(maxsplit=1)
                first_name = name_parts[0] if name_parts else full_name
                last_name = name_parts[1] if len(name_parts) > 1 else None
                
                user = TelegramUser(
                    user_id=user_id,
                    username=None,
                    first_name=first_name,
                    last_name=last_name,
                    is_bot=is_bot
                )
                
            else:
                # from - это объект (старый формат)
                user_data = from_field if isinstance(from_field, dict) else {}

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

            # Сохранение даты и ID первого сообщения
            if message_date and user.user_id:
                if user.user_id not in self.user_first_message_date:
                    self.user_first_message_date[user.user_id] = message_date
                    if message_id:
                        self.user_first_message_id[user.user_id] = message_id
                elif message_date < self.user_first_message_date[user.user_id]:
                    self.user_first_message_date[user.user_id] = message_date
                    if message_id:
                        self.user_first_message_id[user.user_id] = message_id

            return user
        except Exception as e:
            logger.error(f"Ошибка при извлечении пользователя из сообщения: {str(e)}", exc_info=True)
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
        import re
        mentioned = []
        if not text:
            return mentioned

        # Поиск упоминаний в формате @username
        # Username в Telegram может содержать буквы, цифры и подчеркивания, длина 5-32 символа
        pattern = r'@([a-zA-Z0-9_]{5,32})'
        matches = re.findall(pattern, text)
        
        for username in matches:
            if username not in mentioned:
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
                # Если новый пользователь не mention_only, сбрасываем флаг
                if not user.is_mention_only:
                    existing_user.is_mention_only = False
                # Обновляем дату регистрации если она раньше
                if user_id in self.user_first_message_date:
                    existing_user.registration_date = self.user_first_message_date[user_id]
                # Обновляем дату и ID первого сообщения ТОЛЬКО если они еще не установлены или новая дата раньше
                if user_id in self.user_first_message_date:
                    new_date = self.user_first_message_date[user_id]
                    if not existing_user.first_message_date or (new_date and existing_user.first_message_date and new_date < existing_user.first_message_date):
                        existing_user.first_message_date = new_date
                        if user_id in self.user_first_message_id:
                            existing_user.first_message_id = self.user_first_message_id[user_id]
                elif user_id in self.user_first_message_id and not existing_user.first_message_id:
                    # Если есть только ID, но нет даты, сохраняем ID только если его еще нет
                    existing_user.first_message_id = self.user_first_message_id[user_id]
                # Обновляем дату и эмодзи первой реакции ТОЛЬКО если они еще не установлены или новая дата раньше
                if user_id in self.user_first_reaction_date:
                    new_reaction_date = self.user_first_reaction_date[user_id]
                    if not existing_user.first_reaction_date or (new_reaction_date and existing_user.first_reaction_date and new_reaction_date < existing_user.first_reaction_date):
                        existing_user.first_reaction_date = new_reaction_date
                        if user_id in self.user_first_reaction_emoji:
                            existing_user.first_reaction_emoji = self.user_first_reaction_emoji[user_id]
                elif user_id in self.user_first_reaction_emoji and not existing_user.first_reaction_emoji:
                    # Если есть только эмодзи, но нет даты, сохраняем эмодзи только если его еще нет
                    existing_user.first_reaction_emoji = self.user_first_reaction_emoji[user_id]
                # Обновляем наличие канала
                if user.has_channel is not None:
                    existing_user.has_channel = user.has_channel
                # ВСЕГДА обновляем username если он есть в новых данных
                if user.username:
                    existing_user.username = user.username
                # Обновляем телефон если он отсутствует
                if not existing_user.phone_number and user.phone_number:
                    existing_user.phone_number = user.phone_number
                # Обновляем упоминание если оно отсутствует
                if not existing_user.mention and user.mention:
                    existing_user.mention = user.mention
                # Обновляем другие поля если они отсутствуют
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
                    user.first_message_date = self.user_first_message_date[user_id]
                if user_id in self.user_first_message_id:
                    user.first_message_id = self.user_first_message_id[user_id]
                if user_id in self.user_first_reaction_date:
                    user.first_reaction_date = self.user_first_reaction_date[user_id]
                if user_id in self.user_first_reaction_emoji:
                    user.first_reaction_emoji = self.user_first_reaction_emoji[user_id]
                self.users[user_id] = user

    def get_unique_users(self) -> List[TelegramUser]:
        """Получение списка уникальных пользователей."""
        # Убеждаемся, что у всех пользователей установлена дата регистрации, первого сообщения и первой реакции
        for user_id, user in self.users.items():
            if user_id in self.user_first_message_date:
                if not user.registration_date:
                    user.registration_date = self.user_first_message_date[user_id]
                if not user.first_message_date:
                    user.first_message_date = self.user_first_message_date[user_id]
            if user_id in self.user_first_message_id and not user.first_message_id:
                user.first_message_id = self.user_first_message_id[user_id]
            if user_id in self.user_first_reaction_date and not user.first_reaction_date:
                user.first_reaction_date = self.user_first_reaction_date[user_id]
            if user_id in self.user_first_reaction_emoji and not user.first_reaction_emoji:
                user.first_reaction_emoji = self.user_first_reaction_emoji[user_id]
        return list(self.users.values())