#!/usr/bin/env python3
"""
Тестовый скрипт для проверки работы HTML парсера.
"""

import logging
from parsers.html_parser import HTMLParser

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_html_parser():
    """Тестирование HTML парсера на реальном файле."""
    try:
        # Создаем экземпляр парсера
        parser = HTMLParser()

        # Путь к тестовому файлу
        test_file = "example_chats/messages.html"

        logger.info(f"Начало парсинга файла: {test_file}")

        # Выполняем парсинг
        users = parser.parse(test_file)

        logger.info(f"Парсинг завершен. Найдено {len(users)} пользователей.")

        # Выводим информацию о найденных пользователях
        for i, user in enumerate(users, 1):
            logger.info(f"Пользователь {i}: {user.full_name} (ID: {user.user_id})")
            logger.info(f"  - Username: {user.username}")
            logger.info(f"  - First name: {user.first_name}")
            logger.info(f"  - Last name: {user.last_name}")

        return users

    except Exception as e:
        logger.error(f"Ошибка при тестировании HTML парсера: {str(e)}")
        return []

if __name__ == "__main__":
    test_html_parser()