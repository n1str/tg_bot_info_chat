"""
Скрипт для генерации примера экспорта данных.

Создает примерные данные для демонстрации работы бота.
"""

import os
import tempfile
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font
from models.user import TelegramUser
from processors.export_processor import ExportProcessor

def generate_sample_data():
    """Генерация примерных данных пользователей."""
    users = []

    # Создание примерных пользователей
    sample_users = [
        {
            "user_id": 123456789,
            "username": "john_doe",
            "first_name": "John",
            "last_name": "Doe",
            "is_bot": False
        },
        {
            "user_id": 987654321,
            "username": "jane_smith",
            "first_name": "Jane",
            "last_name": "Smith",
            "is_bot": False
        },
        {
            "user_id": 555777999,
            "username": "alex_tech",
            "first_name": "Alex",
            "last_name": None,
            "is_bot": False
        },
        {
            "user_id": 111222333,
            "username": None,  # Пользователь без username
            "first_name": "Maria",
            "last_name": "Garcia",
            "is_bot": False
        },
        {
            "user_id": 999888777,
            "username": "dev_bot",
            "first_name": "Dev",
            "last_name": "Bot",
            "is_bot": True
        },
        # Добавляем дубликат для проверки дедупликации
        {
            "user_id": 123456789,  # Дубликат первого пользователя
            "username": "john_doe",
            "first_name": "John",
            "last_name": "Doe",
            "is_bot": False
        }
    ]

    for user_data in sample_users:
        user = TelegramUser(**user_data)
        users.append(user)

    return users

def create_example_files():
    """Создание примерных файлов экспорта."""
    # Генерация примерных данных
    users = generate_sample_data()

    # Создание процессора экспорта
    processor = ExportProcessor()

    # Генерация текстового экспорта (для небольшого количества)
    text_file = processor._generate_text_export(users[:3])  # Только 3 пользователя для текстового формата
    print(f"Создан текстовый экспорт: {text_file}")

    # Генерация Excel экспорта (для большого количества)
    excel_file = processor._generate_excel_export(users)
    print(f"Создан Excel экспорт: {excel_file}")

    return text_file, excel_file

if __name__ == "__main__":
    print("Генерация примерных файлов экспорта...")
    text_file, excel_file = create_example_files()
    print("Готово!")