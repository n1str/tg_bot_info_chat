"""
Парсер для JSON файлов истории чатов Telegram.

Обрабатывает экспортированные JSON файлы из Telegram.
"""

import json
import logging
from typing import List, Dict, Any, Union
from datetime import datetime
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
                # Извлечение даты сообщения
                message_date = self._extract_message_date(message)
                
                # Извлечение автора сообщения
                if 'from' in message:
                    user = self._extract_user_from_message(message, message_date)
                    if user:
                        self._add_user(user)

                # Извлечение упомянутых пользователей через entities
                mentioned_users = self._extract_mentioned_users_from_message(message, message_date)
                for mentioned_user in mentioned_users:
                    if mentioned_user:
                        self._add_user(mentioned_user)

                # Также извлекаем упоминания из текста (на случай если entities нет)
                text = self._extract_text_from_message(message)
                if text:
                    mentioned_usernames = self._extract_mentioned_usernames_from_text(text)
                    for username in mentioned_usernames:
                        # Создаем временного пользователя для упоминаний без полных данных
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

    def _extract_message_date(self, message: Dict[str, Any]) -> datetime:
        """Извлечение даты сообщения."""
        try:
            date_str = message.get('date', '')
            if isinstance(date_str, str):
                # Пробуем разные форматы даты
                formats = [
                    '%Y-%m-%dT%H:%M:%S',
                    '%Y-%m-%d %H:%M:%S',
                    '%Y-%m-%dT%H:%M:%S%z',
                    '%Y-%m-%dT%H:%M:%S.%f%z'
                ]
                for fmt in formats:
                    try:
                        return datetime.strptime(date_str, fmt)
                    except ValueError:
                        continue
            elif isinstance(date_str, (int, float)):
                # Unix timestamp
                return datetime.fromtimestamp(date_str)
        except Exception as e:
            logger.debug(f"Не удалось извлечь дату сообщения: {str(e)}")
        return None

    def _extract_text_from_message(self, message: Dict[str, Any]) -> str:
        """Извлечение текста из сообщения (может быть строкой или массивом)."""
        text = message.get('text', '')
        if isinstance(text, str):
            return text
        elif isinstance(text, list):
            # Текст может быть массивом объектов с type и text
            text_parts = []
            for item in text:
                if isinstance(item, str):
                    text_parts.append(item)
                elif isinstance(item, dict):
                    text_parts.append(item.get('text', ''))
            return ' '.join(text_parts)
        return ''

    def _extract_mentioned_users_from_message(self, message: Dict[str, Any], message_date: datetime = None) -> List[TelegramUser]:
        """Извлечение упомянутых пользователей через entities."""
        mentioned_users = []
        
        # Проверяем entities в сообщении
        entities = message.get('entities', []) or message.get('text_entities', [])
        
        for entity in entities:
            entity_type = entity.get('type', '')
            if entity_type == 'mention':
                # Извлекаем username из текста
                text = self._extract_text_from_message(message)
                if text:
                    offset = entity.get('offset', 0)
                    length = entity.get('length', 0)
                    mention_text = text[offset:offset + length]
                    if mention_text.startswith('@'):
                        username = mention_text[1:]
                        # Создаем пользователя с упоминанием
                        temp_user = TelegramUser(
                            user_id=hash(username),
                            username=username,
                            first_name=None,
                            last_name=None
                        )
                        mentioned_users.append(temp_user)
            elif entity_type == 'text_mention':
                # Прямое упоминание с данными пользователя
                user_data = entity.get('user', {})
                if user_data:
                    user = self._extract_user_from_message({'from': user_data}, message_date)
                    if user:
                        mentioned_users.append(user)
        
        return mentioned_users

    def _extract_mentioned_usernames_from_text(self, text: str) -> List[str]:
        """Извлечение упомянутых username из текста."""
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