"""
Модели базы данных для сервиса распределения нагрузки (Вариант 15)
Реализована полная валидация, мягкое удаление, методы получения данных.
"""

import os
from typing import List, Optional, Dict, Any
from peewee import (
    SqliteDatabase,
    Model,
    IntegerField,
    BooleanField,
    AutoField,
    DoesNotExist,
    IntegrityError
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
        indexes = (
            (("teacher_id", "discipline_id", "group_id", "semester"), True),
        )

    # ==================== ВАЛИДАЦИЯ ====================

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

    def validate_full(self) -> None:
        """
        Полная валидация всех полей.
        Используется при создании новой записи.
        """
        self._validate_positive(self.teacher_id, "teacher_id")
        self._validate_positive(self.group_id, "group_id")
        self._validate_positive(self.discipline_id, "discipline_id")
        self._validate_semester(self.semester)
        self._validate_positive(self.hours, "hours")

    def validate_partial(self, fields: Dict[str, Any]) -> None:
        """
        Частичная валидация только переданных полей.
        Используется при обновлении.
        """
        if "teacher_id" in fields:
            self._validate_positive(fields["teacher_id"], "teacher_id")
        if "group_id" in fields:
            self._validate_positive(fields["group_id"], "group_id")
        if "discipline_id" in fields:
            self._validate_positive(fields["discipline_id"], "discipline_id")
        if "semester" in fields:
            self._validate_semester(fields["semester"])
        if "hours" in fields:
            self._validate_positive(fields["hours"], "hours")

    # ==================== CRUD ОПЕРАЦИИ ====================

    @classmethod
    def create_assignment(cls, **kwargs) -> Optional["Assignment"]:
        """
        Создание нового назначения нагрузки.
        Возвращает созданный объект или None при ошибке.
        """
        try:
            # Создаём временный экземпляр для валидации
            temp = cls(**kwargs)
            temp.validate_full()
            
            # Создаём запись в БД
            instance = cls.create(**kwargs)
            return instance
        except ValueError as e:
            print(f"Ошибка валидации: {e}")
            return None
        except IntegrityError as e:
            print(f"Ошибка уникальности: запись с такой комбинацией уже существует - {e}")
            return None
        except Exception as e:
            print(f"Неизвестная ошибка при создании: {e}")
            return None

    def update_assignment(self, **kwargs) -> Optional["Assignment"]:
        """
        Обновление назначения нагрузки.
        Валидирует только переданные поля.
        Возвращает обновлённый объект или None при ошибке.
        """
        try:
            # Валидируем только переданные поля
            self.validate_partial(kwargs)
            
            # Выполняем обновление
            query = Assignment.update(**kwargs).where(Assignment.id == self.id)
            query.execute()
            
            # Обновляем текущий экземпляр
            for key, value in kwargs.items():
                setattr(self, key, value)
            
            return self
        except ValueError as e:
            print(f"Ошибка валидации: {e}")
            return None
        except IntegrityError as e:
            print(f"Ошибка уникальности: нарушение уникального индекса - {e}")
            return None
        except Exception as e:
            print(f"Неизвестная ошибка при обновлении: {e}")
            return None

    def soft_delete(self) -> bool:
        """
        Мягкое удаление: устанавливает is_active = False.
        Возвращает True, если запись была деактивирована,
        False, если запись уже неактивна или произошла ошибка.
        """
        try:
            if not self.is_active:
                return False
            
            self.is_active = False
            self.save()
            return True
        except Exception as e:
            print(f"Ошибка при мягком удалении: {e}")
            return False

    # ==================== МЕТОДЫ ПОЛУЧЕНИЯ ДАННЫХ ====================

    @classmethod
    def get_by_id(cls, assignment_id: int) -> Optional["Assignment"]:
        """
        Получение Assignment по ID.
        Возвращает объект или None, если запись не найдена.
        """
        try:
            return cls.get_by_id(assignment_id)
        except DoesNotExist:
            print(f"Запись с id={assignment_id} не найдена")
            return None
        except Exception as e:
            print(f"Ошибка при получении записи: {e}")
            return None

    @classmethod
    def get_list(
        cls,
        teacher_id: Optional[int] = None,
        group_id: Optional[int] = None,
        discipline_id: Optional[int] = None,
        semester: Optional[int] = None,
        is_active: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List["Assignment"]:
        """
        Получение списка Assignment с фильтрацией и пагинацией.
        
        Параметры:
        - teacher_id: фильтр по ID преподавателя
        - group_id: фильтр по ID группы
        - discipline_id: фильтр по ID дисциплины
        - semester: фильтр по семестру
        - is_active: фильтр по активности
        - limit: максимальное количество записей
        - offset: количество пропускаемых записей
        
        Возвращает список объектов Assignment.
        """
        try:
            query = cls.select()
            
            # Применяем фильтры
            if teacher_id is not None:
                query = query.where(cls.teacher_id == teacher_id)
            if group_id is not None:
                query = query.where(cls.group_id == group_id)
            if discipline_id is not None:
                query = query.where(cls.discipline_id == discipline_id)
            if semester is not None:
                query = query.where(cls.semester == semester)
            if is_active is not None:
                query = query.where(cls.is_active == is_active)
            
            # Применяем пагинацию
            query = query.limit(limit).offset(offset)
            
            return list(query)
        except Exception as e:
            print(f"Ошибка при получении списка: {e}")
            return []

    @classmethod
    def get_active_assignments(cls) -> List["Assignment"]:
        """Получение всех активных назначений (удобный метод-обёртка)"""
        return cls.get_list(is_active=True)

    @classmethod
    def get_by_teacher(cls, teacher_id: int, only_active: bool = True) -> List["Assignment"]:
        """Получение всех назначений для конкретного преподавателя"""
        return cls.get_list(
            teacher_id=teacher_id,
            is_active=only_active if only_active else None
        )

    @classmethod
    def get_by_group(cls, group_id: int, only_active: bool = True) -> List["Assignment"]:
        """Получение всех назначений для конкретной группы"""
        return cls.get_list(
            group_id=group_id,
            is_active=only_active if only_active else None
        )

    @classmethod
    def get_by_discipline(cls, discipline_id: int, only_active: bool = True) -> List["Assignment"]:
        """Получение всех назначений для конкретной дисциплины"""
        return cls.get_list(
            discipline_id=discipline_id,
            is_active=only_active if only_active else None
        )

    def to_dict(self) -> Dict[str, Any]:
        """Преобразование объекта в словарь для API ответов"""
        return {
            "id": self.id,
            "teacher_id": self.teacher_id,
            "group_id": self.group_id,
            "discipline_id": self.discipline_id,
            "semester": self.semester,
            "hours": self.hours,
            "is_active": self.is_active
        }

    def __repr__(self) -> str:
        return f"<Assignment id={self.id} teacher={self.teacher_id} group={self.group_id} discipline={self.discipline_id}>"


# ==================== ИНИЦИАЛИЗАЦИЯ БД ====================

def init_db() -> bool:
    """
    Функция инициализации базы данных.
    Создаёт таблицы, если они не существуют.
    Возвращает True при успехе, False при ошибке.
    """
    try:
        database.connect(reuse_if_open=True)
        
        # Проверяем, существует ли уже таблица
        tables_before = database.get_tables()
        
        # Создаём таблицу (без safe=True для явной обработки ошибок)
        database.create_tables([Assignment])
        
        tables_after = database.get_tables()
        
        if "assignments" in tables_after:
            print("Таблица assignments успешно создана или уже существует")
        else:
            print("Предупреждение: таблица assignments не была создана")
            
        database.close()
        return True
        
    except Exception as e:
        print(f"КРИТИЧЕСКАЯ ОШИБКА при инициализации БД: {e}")
        return False


# Точка входа для автономной инициализации
if __name__ == "__main__":
    success = init_db()
    if success:
        print("База данных успешно инициализирована")
        print(f"Путь к БД: {DB_PATH}")
        
        # Демонстрация работы методов
        print("\n--- Демонстрация работы ---")
        
        # Создание
        assignment = Assignment.create_assignment(
            teacher_id=1,
            group_id=1,
            discipline_id=1,
            semester=1,
            hours=72
        )
        if assignment:
            print(f"Создано: {assignment.to_dict()}")
        
        # Получение по ID
        found = Assignment.get_by_id(1)
        if found:
            print(f"Найдено по ID 1: {found.to_dict()}")
        
        # Обновление
        if assignment:
            updated = assignment.update_assignment(hours=80)
            if updated:
                print(f"Обновлено: {updated.to_dict()}")
        
        # Мягкое удаление
        if assignment:
            result = assignment.soft_delete()
            print(f"Мягкое удаление: {result}")
        
        # Список с фильтрацией
        active_list = Assignment.get_list(is_active=True)
        print(f"Активных записей: {len(active_list)}")
        
    else:
        print("ОШИБКА: не удалось инициализировать базу данных")
