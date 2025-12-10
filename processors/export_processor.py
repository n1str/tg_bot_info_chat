"""
Процессор экспорта данных.

Формирует результаты в виде списка или Excel-файла.
"""

import os
import tempfile
from datetime import datetime
from typing import List
from openpyxl import Workbook
from openpyxl.styles import Font
from config import Config
from models.user import TelegramUser

class ExportProcessor:
    """Процессор для формирования результатов экспорта."""

    def __init__(self):
        self.export_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def generate_export(self, users: List[TelegramUser]) -> str:
        """Генерация экспорта в зависимости от количества пользователей."""
        if len(users) < Config.EXPORT_THRESHOLD:
            return self._generate_text_export(users)
        else:
            return self._generate_excel_export(users)

    def _generate_text_export(self, users: List[TelegramUser]) -> str:
        """Генерация текстового экспорта для небольшого количества пользователей."""
        try:
            # Создание временного файла
            temp_file = tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.txt',
                encoding='utf-8',
                delete=False
            )

            # Запись заголовка
            temp_file.write(f"Список участников чата ({len(users)} пользователей)\n")
            temp_file.write(f"Дата экспорта: {self.export_date}\n\n")

            # Запись пользователей
            for i, user in enumerate(users, 1):
                temp_file.write(f"{i}. {user.display_name}\n")
                if user.bio:
                    temp_file.write(f"   Описание: {user.bio}\n")

            temp_file.close()
            return temp_file.name

        except Exception as e:
            raise Exception(f"Ошибка при генерации текстового экспорта: {str(e)}")

    def _generate_excel_export(self, users: List[TelegramUser]) -> str:
        """Генерация Excel экспорта для большого количества пользователей."""
        try:
            # Создание временного файла
            temp_file = tempfile.NamedTemporaryFile(
                suffix='.xlsx',
                delete=False
            )
            temp_file.close()

            # Создание книги Excel
            wb = Workbook()
            ws = wb.active
            ws.title = "Участники чата"

            # Запись заголовков
            headers = Config.EXCEL_COLUMNS
            for col_num, header in enumerate(headers, 1):
                cell = ws.cell(row=1, column=col_num, value=header)
                cell.font = Font(bold=True)

            # Запись данных
            for row_num, user in enumerate(users, 2):
                ws.cell(row=row_num, column=1, value=self.export_date)
                ws.cell(row=row_num, column=2, value=user.username)
                ws.cell(row=row_num, column=3, value=user.full_name)
                ws.cell(row=row_num, column=4, value=user.bio)
                ws.cell(row=row_num, column=5, value=user.registration_date.isoformat() if user.registration_date else None)
                ws.cell(row=row_num, column=6, value="Да" if user.has_channel else "Нет")

            # Авторазмер колонок
            for column in ws.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = (max_length + 2) * 1.2
                ws.column_dimensions[column_letter].width = adjusted_width

            # Сохранение файла
            wb.save(temp_file.name)
            return temp_file.name

        except Exception as e:
            raise Exception(f"Ошибка при генерации Excel экспорта: {str(e)}")

    def cleanup(self, file_path: str):
        """Удаление временного файла."""
        if os.path.exists(file_path):
            os.remove(file_path)