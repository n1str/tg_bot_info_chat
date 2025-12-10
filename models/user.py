"""
Модель пользователя Telegram.

Содержит класс для представления пользователя и его данных.
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class TelegramUser(BaseModel):
    """Модель пользователя Telegram."""
    user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    bio: Optional[str] = None
    registration_date: Optional[datetime] = None
    has_channel: Optional[bool] = None
    is_bot: bool = False
    is_deleted: bool = False

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
            "user_id": self.user_id,
            "username": self.username,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "bio": self.bio,
            "registration_date": self.registration_date.isoformat() if self.registration_date else None,
            "has_channel": self.has_channel,
            "is_bot": self.is_bot,
            "is_deleted": self.is_deleted
        }