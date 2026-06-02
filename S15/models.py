"""
Модели базы данных для сервиса распределения нагрузки (Вариант 15)
Реализована валидация всех ограничений на уровне модели.
"""

import os
from peewee import (
    SqliteDatabase,
    Model,
    IntegerField,
    BooleanField,
    AutoField,
    DoesNotExist
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
    
    Ограничения (согласно doc.md):
    - teacher_id: int, > 0
    - group_id: int, > 0
    - discipline_id: int, > 0
    - semester: int, 1-8
    - hours: int, > 0
    - is_active: bool, default=True
    - Уникальность: (teacher_id, discipline_id, group_id, semester)
    """
    id = AutoField(primary_key=True, null=False, verbose_name="ID записи")
    teacher_id = IntegerField(null=False, verbose_name="ID преподавателя (>0)")
    group_id = IntegerField(null=False, verbose_name="ID группы (>0)")
    discipline_id = IntegerField(null=False, verbose_name="ID дисциплины (>0)")
    semester = IntegerField(null=False, verbose_name="Номер семестра (1-8)")
    hours = IntegerField(null=False, verbose_name="Количество часов (>0)")
    is_active = BooleanField(null=False, default=True, verbose_name="Активна ли запись")

    class Meta:
        table_name = "assignments"
        # Составной уникальный индекс для соблюдения уникальности комбинации
        indexes = (
            (("teacher_id", "discipline_id", "group_id", "semester"), True),
        )

    @staticmethod
    def _validate_positive(value: int, field_name: str) -> None:
        """Валидация: значение должно быть > 0"""
        if value <= 0:
            raise ValueError(f"{field_name} должен быть больше 0, получено {value}")

    @staticmethod
    def _validate_semester(value: int) -> None:
        """Валидация: семестр должен быть в диапазоне 1-8"""
        if not (1 <= value <= 8):
            raise ValueError(f"semester должен быть в диапазоне 1-8, получено {value}")

    def validate(self) -> None:
        """
        Выполняет валидацию всех полей согласно требованиям doc.md.
        Вызывается перед сохранением (create/update).
        """
        # teacher_id > 0
        self._validate_positive(self.teacher_id, "teacher_id")
        
        # group_id > 0
        self._validate_positive(self.group_id, "group_id")
        
        # discipline_id > 0
        self._validate_positive(self.discipline_id, "discipline_id")
        
        # semester 1-8
        self._validate_semester(self.semester)
        
        # hours > 0
        self._validate_positive(self.hours, "hours")

    def save(self, *args, **kwargs) -> int:
        """Переопределённый save с валидацией перед сохранением"""
        self.validate()
        return super().save(*args, **kwargs)

    @classmethod
    def create(cls, **kwargs) -> "Assignment":
        """Переопределённый create с валидацией"""
        instance = cls(**kwargs)
        instance.validate()
        return super().create(**kwargs)


def init_db() -> None:
    """Функция инициализации базы данных"""
    database.connect(reuse_if_open=True)
    database.create_tables([Assignment], safe=True)
    database.close()


# Точка входа, которая вызывает функцию инициализации
if __name__ == "__main__":
    init_db()
    print("Database initialized successfully")
    print(f"Database path: {DB_PATH}")
