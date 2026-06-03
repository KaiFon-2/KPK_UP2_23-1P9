"""
Модели базы данных для сервиса распределения нагрузки (Вариант 15)
Сервис хранит только связи между преподавателями, группами и дисциплинами.
Справочные данные (преподаватели, группы, дисциплины) находятся в других сервисах.
"""

import os
import sys
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


class LoadAssignment(BaseModel):
    """
    Модель назначения нагрузки.
    Связывает преподавателя, группу и дисциплину в конкретном семестре.
    
    Поля teacher_id, group_id, discipline_id являются ссылками на записи
    в других сервисах (Teacher Service, Group Service, Discipline Service).
    
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
        table_name = "load_assignments"
        # Составной уникальный индекс для соблюдения уникальности комбинации
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
        """Полная валидация всех полей. Используется при создании новой записи."""
        self._validate_positive(self.teacher_id, "teacher_id")
        self._validate_positive(self.group_id, "group_id")
        self._validate_positive(self.discipline_id, "discipline_id")
        self._validate_semester(self.semester)
        self._validate_positive(self.hours, "hours")

    def validate_partial(self, fields: Dict[str, Any]) -> None:
        """Частичная валидация только переданных полей. Используется при обновлении."""
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

    def _check_active_record_exists(self, teacher_id: int, discipline_id: int, group_id: int, semester: int) -> bool:
        """
        Проверяет, существует ли уже активная запись с такой комбинацией полей.
        Используется при создании новой записи.
        """
        return self.select().where(
            self.teacher_id == teacher_id,
            self.discipline_id == discipline_id,
            self.group_id == group_id,
            self.semester == semester,
            self.is_active == True
        ).exists()

    def _check_unique_excluding_self(self, teacher_id: int, discipline_id: int, group_id: int, semester: int) -> bool:
        """
        Проверяет уникальность комбинации полей, исключая текущую запись.
        Используется при обновлении.
        """
        query = self.select().where(
            self.teacher_id == teacher_id,
            self.discipline_id == discipline_id,
            self.group_id == group_id,
            self.semester == semester
        )
        if self.id is not None:
            query = query.where(self.id != self.id)
        return query.exists()

    # ==================== CRUD ОПЕРАЦИИ ====================

    @classmethod
    def create_assignment(cls, **kwargs) -> Optional["LoadAssignment"]:
        """
        Создание нового назначения нагрузки.
        Возвращает созданный объект или None при ошибке.
        """
        try:
            # Извлекаем значения для проверки уникальности
            teacher_id = kwargs.get("teacher_id")
            discipline_id = kwargs.get("discipline_id")
            group_id = kwargs.get("group_id")
            semester = kwargs.get("semester")
            
            # Проверяем, не существует ли уже активной записи с такой комбинацией
            temp_check = cls()
            if temp_check._check_active_record_exists(teacher_id, discipline_id, group_id, semester):
                print(f"Ошибка уникальности: активная запись с комбинацией "
                      f"(teacher_id={teacher_id}, discipline_id={discipline_id}, "
                      f"group_id={group_id}, semester={semester}) уже существует")
                return None
            
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
            print(f"Ошибка уникальности (IntegrityError): {e}")
            return None
        except Exception as e:
            print(f"Неизвестная ошибка при создании: {e}")
            return None

    def update_assignment(self, **kwargs) -> Optional["LoadAssignment"]:
        """
        Обновление назначения нагрузки.
        Валидирует только переданные поля.
        Возвращает обновлённый объект или None при ошибке.
        """
        try:
            # Сохраняем старые значения для проверки уникальности
            old_teacher_id = self.teacher_id
            old_discipline_id = self.discipline_id
            old_group_id = self.group_id
            old_semester = self.semester
            
            # Валидируем только переданные поля
            self.validate_partial(kwargs)
            
            # Определяем новые значения (старые, если не переданы)
            new_teacher_id = kwargs.get("teacher_id", old_teacher_id)
            new_discipline_id = kwargs.get("discipline_id", old_discipline_id)
            new_group_id = kwargs.get("group_id", old_group_id)
            new_semester = kwargs.get("semester", old_semester)
            
            # Проверяем уникальность новой комбинации
            if (new_teacher_id != old_teacher_id or 
                new_discipline_id != old_discipline_id or 
                new_group_id != old_group_id or 
                new_semester != old_semester):
                
                # Проверяем, не существует ли уже активной записи с новой комбинацией
                if self._check_active_record_exists(new_teacher_id, new_discipline_id, new_group_id, new_semester):
                    print(f"Ошибка уникальности: активная запись с комбинацией "
                          f"(teacher_id={new_teacher_id}, discipline_id={new_discipline_id}, "
                          f"group_id={new_group_id}, semester={new_semester}) уже существует")
                    return None
            
            # Выполняем обновление
            update_query = LoadAssignment.update(**kwargs).where(LoadAssignment.id == self.id)
            update_query.execute()
            
            # Обновляем текущий экземпляр
            for key, value in kwargs.items():
                setattr(self, key, value)
            
            return self
        except ValueError as e:
            print(f"Ошибка валидации: {e}")
            return None
        except IntegrityError as e:
            print(f"Ошибка уникальности (IntegrityError): {e}")
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
    def get_by_id(cls, assignment_id: int) -> Optional["LoadAssignment"]:
        """Получение LoadAssignment по ID. Возвращает объект или None."""
        try:
            return cls.get_or_none(cls.id == assignment_id)
        except Exception as e:
            print(f"Ошибка при получении записи по ID {assignment_id}: {e}")
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
    ) -> List["LoadAssignment"]:
        """
        Получение списка LoadAssignment с фильтрацией и пагинацией.
        
        Параметры:
        - teacher_id: фильтр по ID преподавателя (None = без фильтра)
        - group_id: фильтр по ID группы (None = без фильтра)
        - discipline_id: фильтр по ID дисциплины (None = без фильтра)
        - semester: фильтр по семестру (None = без фильтра)
        - is_active: фильтр по активности (None = без фильтра)
        - limit: максимальное количество записей
        - offset: количество пропускаемых записей
        """
        try:
            query = cls.select()
            
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
            
            query = query.limit(limit).offset(offset)
            return list(query)
        except Exception as e:
            print(f"Ошибка при получении списка: {e}")
            return []

    @classmethod
    def get_active_assignments(cls) -> List["LoadAssignment"]:
        """Получение всех активных назначений"""
        return cls.get_list(is_active=True)

    @classmethod
    def get_by_teacher(cls, teacher_id: int, only_active: bool = True) -> List["LoadAssignment"]:
        """Получение всех назначений для конкретного преподавателя"""
        return cls.get_list(
            teacher_id=teacher_id,
            is_active=only_active if only_active else None
        )

    @classmethod
    def get_by_group(cls, group_id: int, only_active: bool = True) -> List["LoadAssignment"]:
        """Получение всех назначений для конкретной группы"""
        return cls.get_list(
            group_id=group_id,
            is_active=only_active if only_active else None
        )

    @classmethod
    def get_by_discipline(cls, discipline_id: int, only_active: bool = True) -> List["LoadAssignment"]:
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
        return f"<LoadAssignment id={self.id} teacher={self.teacher_id} group={self.group_id} discipline={self.discipline_id}>"


# ==================== ИНИЦИАЛИЗАЦИЯ БД ====================

def init_db() -> bool:
    """
    Функция инициализации базы данных.
    Создаёт таблицы, если они не существуют.
    Возвращает True при успехе, False при ошибке.
    """
    try:
        database.connect(reuse_if_open=True)
        database.create_tables([LoadAssignment], safe=True)
        print("Таблица load_assignments успешно создана или уже существует")
        database.close()
        return True
    except Exception as e:
        print(f"КРИТИЧЕСКАЯ ОШИБКА при инициализации БД: {e}")
        return False


# Точка входа
if __name__ == "__main__":
    success = init_db()
    if success:
        print(f"База данных успешно инициализирована")
        print(f"Путь к БД: {DB_PATH}")
    else:
        print("ОШИБКА: не удалось инициализировать базу данных")
        sys.exit(1)
