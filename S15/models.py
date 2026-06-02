import os
from peewee import (
    SqliteDatabase,
    Model,
    IntegerField,
    BooleanField,
    AutoField
)

# Путь к файлу базы данных
DB_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DB_DIR, "load_assignment.db")

# Подключение к SQLite (без поддержки FOREIGN KEY)
database = SqliteDatabase(DB_PATH, pragmas={"foreign_keys": 0})


class BaseModel(Model):
    """Базовый класс для всех моделей"""
    class Meta:
        database = database


class LoadAssignment(BaseModel):
    """
    Модель назначения нагрузки.
    Хранит связь: преподаватель → дисциплина → группа в конкретном семестре.
    """
    id = AutoField(primary_key=True, verbose_name="ID записи")
    teacher_id = IntegerField(null=False, verbose_name="ID преподавателя")
    group_id = IntegerField(null=False, verbose_name="ID группы")
    discipline_id = IntegerField(null=False, verbose_name="ID дисциплины")
    semester = IntegerField(null=False, verbose_name="Номер семестра")
    hours = IntegerField(null=False, verbose_name="Количество часов")
    active = BooleanField(default=True, verbose_name="Активна ли запись")

    class Meta:
        table_name = "load_assignments"
        # Уникальность: один преподаватель не может вести ту же дисциплину
        # в той же группе в том же семестре дважды
        indexes = (
            (("teacher_id", "discipline_id", "group_id", "semester"), True),
        )


def init_db() -> None:
    """Инициализация базы данных: подключение и создание таблиц"""
    database.connect(reuse_if_open=True)
    database.create_tables([LoadAssignment], safe=True)
    database.close()


# Точка входа для автономной инициализации
if __name__ == "__main__":
    init_db()
    print("База данных успешно инициализирована")
    print(f"Файл БД: {DB_PATH}")
