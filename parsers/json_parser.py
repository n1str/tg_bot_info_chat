"""
Парсер для JSON файлов истории чатов Telegram.

Обрабатывает экспортированные JSON файлы из Telegram.
"""

import json
import logging
from typing import List, Dict, Any, Union, Optional
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
                # Извлечение даты и ID сообщения
                message_date = self._extract_message_date(message)
                message_id = message.get('id')
                
                # Извлечение телефона и упоминания из текста сообщения
                phone_number = self._extract_phone_from_message(message)
                mention = self._extract_mention_from_message(message)
                
                # Извлечение автора сообщения
                if 'from' in message:
                    user = self._extract_user_from_message(message, message_date, message_id)
                    if user:
                        # Добавляем телефон и упоминание если они найдены
                        if phone_number and not user.phone_number:
                            user.phone_number = phone_number
                        if mention and not user.mention:
                            user.mention = mention
                        self._add_user(user)

                # Извлечение упомянутых пользователей через entities
                # НЕ передаем message_date и message_id для упомянутых пользователей
                mentioned_users = self._extract_mentioned_users_from_message(message, None)
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
                
                # Извлечение пользователей из реакций
                # Извлекаем дату и эмодзи для первой реакции каждого пользователя
                reactions = message.get('reactions', [])
                for reaction in reactions:
                    emoji = reaction.get('emoji', '')
                    recent_reactions = reaction.get('recent', [])
                    for reaction_user in recent_reactions:
                        # Формат: {"from": "Олег", "from_id": "user824757016", "date": "2025-12-26T21:36:58"}
                        reaction_date = self._extract_reaction_date(reaction_user)
                        user = self._extract_user_from_message(reaction_user, None, None)
                        if user:
                            # Сохраняем информацию о первой реакции
                            self._save_first_reaction(user.user_id, reaction_date, emoji)
                            self._add_user(user)

            return self.get_unique_users()

        except json.JSONDecodeError as e:
            logger.error(f"Ошибка декодирования JSON: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Ошибка при парсинге JSON файла {file_path}: {str(e)}")
            return []

    def _extract_message_date(self, message: Dict[str, Any]) -> Optional[datetime]:
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

    def _extract_mentioned_users_from_message(self, message: Dict[str, Any], message_date: Optional[datetime] = None) -> List[TelegramUser]:
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
                # НЕ передаем message_date и message_id для упомянутых пользователей
                user_data = entity.get('user', {})
                if user_data:
                    user = self._extract_user_from_message({'from': user_data}, None, None)
                    if user:
                        mentioned_users.append(user)
        
        return mentioned_users

    def _extract_mentioned_usernames_from_text(self, text: str) -> List[str]:
        """Извлечение упомянутых username из текста."""
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

    def _extract_phone_from_message(self, message: Dict[str, Any]) -> Optional[str]:
        """Извлечение номера телефона из сообщения."""
        try:
            # Проверяем прямое поле phone_number в сообщении
            phone_number = message.get('phone_number')
            if phone_number:
                return str(phone_number)
            
            # Проверяем в тексте сообщения: "text": [{"type": "phone", "text": "ТУТ НОМЕР"}]
            text = message.get('text', '')
            if isinstance(text, list):
                for item in text:
                    if isinstance(item, dict):
                        item_type = item.get('type', '')
                        if item_type == 'phone':
                            phone_text = item.get('text', '')
                            if phone_text:
                                return str(phone_text)
            
            # Проверяем в контактных карточках (contact_info)
            contact_info = message.get('contact_info')
            if contact_info:
                if isinstance(contact_info, dict):
                    phone = contact_info.get('phone_number')
                    if phone:
                        return str(phone)
            
            # Проверяем в других возможных местах (contact)
            if 'contact' in message:
                contact = message['contact']
                if isinstance(contact, dict):
                    phone = contact.get('phone_number')
                    if phone:
                        return str(phone)
            
            # Проверяем в медиа-объектах (media)
            media = message.get('media')
            if media and isinstance(media, dict):
                phone = media.get('phone_number')
                if phone:
                    return str(phone)
        except Exception as e:
            logger.debug(f"Ошибка при извлечении телефона: {str(e)}")
        return None

    def _extract_mention_from_message(self, message: Dict[str, Any]) -> Optional[str]:
        """Извлечение упоминания из сообщения."""
        try:
            text = message.get('text', '')
            if isinstance(text, list):
                for item in text:
                    if isinstance(item, dict):
                        item_type = item.get('type', '')
                        if item_type == 'mention':
                            mention_text = item.get('text', '')
                            if mention_text:
                                # Убираем @ если есть
                                if mention_text.startswith('@'):
                                    return mention_text
                                else:
                                    return f"@{mention_text}"
        except Exception as e:
            logger.debug(f"Ошибка при извлечении упоминания: {str(e)}")
        return None

    def _extract_reaction_date(self, reaction_user: Dict[str, Any]) -> Optional[datetime]:
        """Извлечение даты реакции из данных пользователя реакции."""
        try:
            date_str = reaction_user.get('date', '')
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
            logger.debug(f"Не удалось извлечь дату реакции: {str(e)}")
        return None

    def _save_first_reaction(self, user_id: int, reaction_date: Optional[datetime], emoji: str):
        """Сохранение информации о первой реакции пользователя."""
        if not reaction_date or not user_id:
            return
        
        # Сохраняем дату первой реакции (самую раннюю)
        if user_id not in self.user_first_reaction_date:
            self.user_first_reaction_date[user_id] = reaction_date
            if emoji:
                self.user_first_reaction_emoji[user_id] = emoji
        elif reaction_date < self.user_first_reaction_date[user_id]:
            self.user_first_reaction_date[user_id] = reaction_date
            if emoji:
                self.user_first_reaction_emoji[user_id] = emoji