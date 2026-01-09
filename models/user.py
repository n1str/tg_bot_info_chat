"""
Модель пользователя Telegram.

Содержит класс для представления пользователя и его данных.
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date

class TelegramUser(BaseModel):
    """Модель пользователя Telegram."""
    user_id: int  # Внутренний ID (telegram_id в экспорте)
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    birth_date: Optional[date] = None
    bio: Optional[str] = None
    registration_date: Optional[datetime] = None
    has_channel: Optional[bool] = None
    is_bot: bool = False
    is_deleted: bool = False
    mention: Optional[str] = None  # Упоминание пользователя
    first_message_date: Optional[datetime] = None  # Дата первого сообщения
    first_message_id: Optional[int] = None  # ID первого сообщения
    first_reaction_date: Optional[datetime] = None  # Дата первой реакции
    first_reaction_emoji: Optional[str] = None  # Эмодзи первой реакции
    is_mention_only: bool = False  # Флаг для пользователей, которые только упомянуты

    @property
    def full_name(self) -> str:
        """Полное имя пользователя."""
        parts = []
        if self.first_name:
            parts.append(self.first_name)
        if self.last_name:
            parts.append(self.last_name)
        return " ".join(parts) if parts else "Unknown"

    @property
    def display_name(self) -> str:
        """Отображаемое имя (username или full_name)."""
        return f"@{self.username}" if self.username else self.full_name

    def to_dict(self) -> dict:
        """Преобразование в словарь для экспорта."""
        return {
            "telegram_id": self.user_id,
            "username": self.username,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "phone_number": self.phone_number,
            "birth_date": self.birth_date.isoformat() if self.birth_date else None,
            "registration_date": self.registration_date.isoformat() if self.registration_date else None,
            "is_bot": self.is_bot,
            "has_channel": self.has_channel
        }