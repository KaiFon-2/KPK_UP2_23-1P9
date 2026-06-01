import os
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


class Assignment(BaseModel):
    """
    Модель назначения нагрузки.
    Связывает преподавателя, группу и дисциплину в конкретном семестре.
    """
    id = AutoField(primary_key=True, null=False)
    teacher_id = IntegerField(null=False)      # ID из Teacher Service
    group_id = IntegerField(null=False)        # ID из Group Service
    discipline_id = IntegerField(null=False)   # ID из Discipline Service
    semester = IntegerField(null=False)        # Номер семестра 1-8
    hours = IntegerField(null=False)           # Количество часов
    is_active = BooleanField(null=False, default=True)  # Логическое удаление

    class Meta:
        table_name = "assignments"
        # Составной уникальный индекс для соблюдения уникальности комбинации
        indexes = (
            (("teacher_id", "discipline_id", "group_id", "semester"), True),
        )


def init_db() -> None:
    """Функция инициализации базы данных"""
    database.connect(reuse_if_open=True)
    database.create_tables([Assignment], safe=True)
    database.close()


# Точка входа, которая вызывает функцию инициализации
if __name__ == "__main__":
    init_db()
    print("Database initialized successfully")
