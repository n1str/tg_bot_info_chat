"""
Парсер для HTML файлов истории чатов Telegram.

Обрабатывает экспортированные HTML файлы из Telegram.
"""

import logging
from typing import List, Optional
from datetime import datetime
from bs4 import BeautifulSoup
from parsers.base_parser import BaseParser
from models.user import TelegramUser

logger = logging.getLogger(__name__)

class HTMLParser(BaseParser):
    """Парсер для HTML файлов истории чатов."""

    def parse(self, file_path: str) -> List[TelegramUser]:
        """Парсинг HTML файла истории чата."""
        try:
            logger.info(f"Начало парсинга HTML файла: {file_path}")
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                soup = BeautifulSoup(content, 'html.parser')

            # Обработка сообщений
            messages = soup.find_all('div', class_='message')
            for message in messages:
                # Извлечение даты сообщения
                message_date = self._extract_message_date_from_html(message)
                
                # Извлечение автора сообщения из from_name
                from_name_element = message.find('div', class_='from_name')
                if from_name_element:
                    user_data = self._extract_user_from_html(from_name_element, message_date)
                    if user_data:
                        self._add_user(user_data)
                        logger.info(f"Добавлен пользователь: {user_data.full_name}")
                else:
                    logger.debug("Элемент from_name не найден в сообщении")

                # Извлечение текста сообщения для упоминаний
                text_element = message.find('div', class_='text')
                if text_element:
                    text_content = text_element.get_text()
                    mentioned_users = self._extract_mentioned_users(text_content)
                    for username in mentioned_users:
                        # Создаем временного пользователя для упоминаний
                        temp_user = TelegramUser(
                            user_id=hash(username),  # Временный ID
                            username=username,
                            first_name=None,
                            last_name=None,
                            is_mention_only=True  # Помечаем как только упомянутого
                        )
                        self._add_user(temp_user)
                        logger.info(f"Добавлен упомянутый пользователь: @{username}")

            users = self.get_unique_users()
            logger.info(f"Найдено {len(users)} уникальных пользователей")
            return users

        except Exception as e:
            logger.error(f"Ошибка при парсинге HTML файла {file_path}: {str(e)}")
            logger.error(f"Тип ошибки: {type(e).__name__}")
            return []

    def _extract_message_date_from_html(self, message_element) -> Optional[datetime]:
        """Извлечение даты сообщения из HTML элемента."""
        try:
            # Ищем элемент с датой (обычно это div с классом date или атрибут title)
            date_element = message_element.find('div', class_='date')
            if date_element:
                date_str = date_element.get('title', '') or date_element.get_text()
                if date_str:
                    # Пробуем распарсить дату
                    formats = [
                        '%d.%m.%Y %H:%M:%S',
                        '%Y-%m-%d %H:%M:%S',
                        '%d.%m.%Y %H:%M',
                        '%Y-%m-%d %H:%M'
                    ]
                    for fmt in formats:
                        try:
                            return datetime.strptime(date_str.strip(), fmt)
                        except ValueError:
                            continue
        except Exception as e:
            logger.debug(f"Не удалось извлечь дату из HTML: {str(e)}")
        return None

    def _extract_user_from_html(self, from_name_element, message_date: Optional[datetime] = None) -> TelegramUser:
        """Извлечение данных пользователя из HTML элемента from_name."""
        try:
            # Извлечение полного имени из from_name
            full_name = from_name_element.get_text().strip()

            # Проверка на пустое имя
            if not full_name:
                logger.warning("Пустое имя пользователя в from_name")
                return None

            # Генерируем user_id на основе имени (в реальности это должен быть уникальный ID)
            user_id = hash(full_name)

            # Разделение на имя и фамилию (простая логика)
            name_parts = full_name.split(maxsplit=1)
            first_name = name_parts[0] if name_parts else "Unknown"
            last_name = name_parts[1] if len(name_parts) > 1 else None

            # Создаем словарь с данными пользователя для использования базового метода
            user_data = {
                'id': user_id,
                'username': None,  # В HTML экспорте Telegram username не доступен
                'first_name': first_name,
                'last_name': last_name,
                'bio': None
            }

            # Используем базовый метод для создания пользователя
            # В HTML нет ID сообщения, передаем None
            user = self._extract_user_from_message({'from': user_data}, message_date, None)

            logger.info(f"Извлечен пользователь: {user.full_name if user else 'None'} (ID: {user_id})")
            return user
        except Exception as e:
            logger.error(f"Ошибка при извлечении пользователя из HTML: {str(e)}")
            return None

    def get_unique_users(self) -> List[TelegramUser]:
        """Получение списка уникальных пользователей из HTML."""
        return super().get_unique_users()