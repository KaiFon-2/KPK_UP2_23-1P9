from peewee import *
from datetime import datetime
from playhouse.shortcuts import model_to_dict

db = SqliteDatabase('university.db')


class Assignment(Model):
    """Модель расписания занятий согласно doc.md"""
    
    # Явное объявление первичного ключа
    id = AutoField()
    
    # Основные поля с ограничениями
    teacher_id = IntegerField()
    discipline_id = IntegerField()
    group_id = IntegerField()
    semester = IntegerField()
    hours = IntegerField()
    is_active = BooleanField(default=True)  # Мягкое удаление
    
    class Meta:
        database = db
        table_name = 'assignments'
        # Уникальное ограничение на комбинацию полей
        indexes = (
            (('teacher_id', 'discipline_id', 'group_id', 'semester'), True),
        )
        # Ограничения на уровне БД (SQLite поддерживает CHECK через constraints)
        constraints = [
            Check('teacher_id > 0'),
            Check('discipline_id > 0'),
            Check('group_id > 0'),
            Check('semester BETWEEN 1 AND 8'),
            Check('hours > 0')
        ]
    
    def validate_for_create(self):
        """Валидация при создании (все поля обязательны)"""
        errors = []
        
        if self.teacher_id <= 0:
            errors.append(f"teacher_id должен быть > 0, получено: {self.teacher_id}")
        if self.discipline_id <= 0:
            errors.append(f"discipline_id должен быть > 0, получено: {self.discipline_id}")
        if self.group_id <= 0:
            errors.append(f"group_id должен быть > 0, получено: {self.group_id}")
        if not (1 <= self.semester <= 8):
            errors.append(f"semester должен быть от 1 до 8, получено: {self.semester}")
        if self.hours <= 0:
            errors.append(f"hours должен быть > 0, получено: {self.hours}")
        
        if errors:
            raise ValueError(f"Ошибки валидации: {'; '.join(errors)}")
    
    def validate_for_update(self, updated_fields):
        """Валидация только переданных полей при обновлении"""
        errors = []
        
        if 'teacher_id' in updated_fields:
            if updated_fields['teacher_id'] <= 0:
                errors.append(f"teacher_id должен быть > 0, получено: {updated_fields['teacher_id']}")
        
        if 'discipline_id' in updated_fields:
            if updated_fields['discipline_id'] <= 0:
                errors.append(f"discipline_id должен быть > 0, получено: {updated_fields['discipline_id']}")
        
        if 'group_id' in updated_fields:
            if updated_fields['group_id'] <= 0:
                errors.append(f"group_id должен быть > 0, получено: {updated_fields['group_id']}")
        
        if 'semester' in updated_fields:
            if not (1 <= updated_fields['semester'] <= 8):
                errors.append(f"semester должен быть от 1 до 8, получено: {updated_fields['semester']}")
        
        if 'hours' in updated_fields:
            if updated_fields['hours'] <= 0:
                errors.append(f"hours должен быть > 0, получено: {updated_fields['hours']}")
        
        if errors:
            raise ValueError(f"Ошибки валидации: {'; '.join(errors)}")
    
    def validate_uniqueness(self, exclude_id=None):
        """Проверка уникальности комбинации полей"""
        query = Assignment.select().where(
            (Assignment.teacher_id == self.teacher_id) &
            (Assignment.discipline_id == self.discipline_id) &
            (Assignment.group_id == self.group_id) &
            (Assignment.semester == self.semester)
        )
        
        if exclude_id:
            query = query.where(Assignment.id != exclude_id)
        
        if query.exists():
            raise ValueError("Assignment с такой комбинацией teacher_id, discipline_id, group_id и semester уже существует")
    
    def create_assignment(self, **kwargs):
        """Создание новой записи"""
        self.teacher_id = kwargs.get('teacher_id')
        self.discipline_id = kwargs.get('discipline_id')
        self.group_id = kwargs.get('group_id')
        self.semester = kwargs.get('semester')
        self.hours = kwargs.get('hours')
        self.is_active = kwargs.get('is_active', True)
        
        # Валидация
        self.validate_for_create()
        self.validate_uniqueness()
        
        # Сохранение
        self.save()
        return self.to_dict()
    
    def update_assignment(self, **kwargs):
        """Обновление только переданных полей"""
        if not kwargs:
            return self.to_dict()
        
        # Сохраняем старые значения для проверки уникальности
        old_values = {
            'teacher_id': self.teacher_id,
            'discipline_id': self.discipline_id,
            'group_id': self.group_id,
            'semester': self.semester
        }
        
        # Валидация обновляемых полей
        self.validate_for_update(kwargs)
        
        # Обновление полей
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        
        # Проверка уникальности, если изменились ключевые поля
        key_fields_changed = any(
            kwargs.get(field) is not None and kwargs[field] != old_values[field]
            for field in ['teacher_id', 'discipline_id', 'group_id', 'semester']
        )
        
        if key_fields_changed:
            self.validate_uniqueness(exclude_id=self.id)
        
        # Сохранение только измененных полей
        self.save(only=list(kwargs.keys()))
        return self.to_dict()
    
    def soft_delete(self):
        """Мягкое удаление: установка is_active = False"""
        self.is_active = False
        result = self.save(only=['is_active'])
        return bool(result)  # Возвращаем True/False согласно спецификации
    
    def restore(self):
        """Восстановление мягко удаленной записи"""
        self.is_active = True
        result = self.save(only=['is_active'])
        return bool(result)
    
    @classmethod
    def get_assignment_by_id(cls, assignment_id):
        """Получение Assignment по ID"""
        try:
            return cls.get_by_id(assignment_id)
        except cls.DoesNotExist:
            return None
    
    @classmethod
    def get_filtered(cls, teacher_id=None, group_id=None, discipline_id=None,
                     semester=None, is_active=None, limit=None, offset=None):
        """
        Получение списка Assignment с фильтрацией и пагинацией
        Согласно требованиям doc.md
        """
        query = cls.select()
        
        # Применение фильтров
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
        
        # Пагинация
        if limit is not None:
            query = query.limit(limit)
        if offset is not None:
            query = query.offset(offset)
        
        # Возвращаем список словарей
        return [assignment.to_dict() for assignment in query]
    
    @classmethod
    def get_active(cls):
        """Получение только активных записей"""
        return cls.select().where(cls.is_active == True)
    
    def to_dict(self):
        """
        Сериализация модели в словарь с полным набором полей
        Согласно требованиям doc.md к возвращаемым данным
        """
        return {
            'id': self.id,
            'teacher_id': self.teacher_id,
            'discipline_id': self.discipline_id,
            'group_id': self.group_id,
            'semester': self.semester,
            'hours': self.hours,
            'is_active': self.is_active
        }


def init_db():
    """Инициализация базы данных"""
    db.connect()
    db.create_tables([Assignment])


def close_db():
    """Закрытие соединения с БД"""
    if not db.is_closed():
        db.close()


if __name__ == '__main__':
    init_db()
    print("База данных успешно инициализирована")
    
    # Пример использования
    try:
        # Создание
        assignment = Assignment()
        result = assignment.create_assignment(
            teacher_id=1,
            discipline_id=1,
            group_id=1,
            semester=3,
            hours=36
        )
        print(f"Создано: {result}")
        
        # Обновление только некоторых полей
        updated = assignment.update_assignment(hours=40, semester=4)
        print(f"Обновлено: {updated}")
        
        # Мягкое удаление
        deleted = assignment.soft_delete()
        print(f"Удалено: {deleted}")
        
        # Фильтрация
        filtered = Assignment.get_filtered(is_active=True)
        print(f"Активные записи: {filtered}")
        
    except ValueError as e:
        print(f"Ошибка: {e}")
    finally:
        close_db()
