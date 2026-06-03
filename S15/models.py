"""
Модели базы данных для сервиса распределения нагрузки (Вариант 15)
Сервис хранит только связи между преподавателями, группами и дисциплинами.
Справочные данные (преподаватели, группы, дисциплины) находятся в других сервисах.
Содержит ТОЛЬКО модели и инициализацию БД. Без бизнес-логики.
"""

import os
import sys
from peewee import (
    SqliteDatabase,
    Model,
    IntegerField,
    BooleanField,
    AutoField
)

# Путь к базе данных
DB_PATH = os.path.join(os.path.dirname(__file__), "load_assignment.db")
database = SqliteDatabase(DB_PATH, pragmas={"foreign_keys": 0})


class BaseModel(Model):
    class Meta:
        database = database


class LoadAssignment(BaseModel):
    """
    Модель назначения нагрузки.
    Связывает преподавателя, группу и дисциплину в конкретном семестре.
    
    Поля teacher_id, group_id, discipline_id являются ссылками на записи
    в других сервисах (Teacher Service, Group Service, Discipline Service).
    Валидация ограничений (teacher_id > 0, semester 1-8, hours > 0 и т.д.)
    должна выполняться на уровне API, а не в модели.
    """
    id = AutoField(primary_key=True, null=False)
    teacher_id = IntegerField(null=False)
    group_id = IntegerField(null=False)
    discipline_id = IntegerField(null=False)
    semester = IntegerField(null=False)
    hours = IntegerField(null=False)
    is_active = BooleanField(null=False, default=True)

    class Meta:
        table_name = "load_assignment"
        # Составной уникальный индекс для связи "многие ко многим"
        indexes = (
            (("teacher_id", "discipline_id", "group_id", "semester"), True),
        )


def init_db() -> None:
    """Функция инициализации базы данных: создание таблиц"""
    database.connect(reuse_if_open=True)
    database.create_tables([LoadAssignment], safe=True)
    database.close()


# Точка входа для автономной инициализации
if __name__ == "__main__":
    init_db()
    print("Database initialized successfully")
    print(f"Database path: {DB_PATH}")
