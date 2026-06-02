from peewee import *
from datetime import datetime

db = SqliteDatabase('university.db')


class BaseModel(Model):
    """Базовая модель с общими полями"""
    
    class Meta:
        database = db


class Assignment(BaseModel):
    """Модель расписания занятий согласно doc.md"""
    teacher_id = IntegerField()
    discipline_id = IntegerField()
    group_id = IntegerField()
    semester = IntegerField()
    hours = IntegerField()
    is_active = BooleanField(default=True)  # Мягкое удаление через is_active
    
    class Meta:
        table_name = 'assignments'
        # Уникальное ограничение на комбинацию полей
        indexes = (
            (('teacher_id', 'discipline_id', 'group_id', 'semester'), True),
        )
    
    def validate_for_create(self):
        """Валидация при создании (все поля обязательны)"""
        if self.teacher_id <= 0:
            raise ValueError(f"teacher_id должен быть > 0, получено: {self.teacher_id}")
        if self.discipline_id <= 0:
            raise ValueError(f"discipline_id должен быть > 0, получено: {self.discipline_id}")
        if self.group_id <= 0:
            raise ValueError(f"group_id должен быть > 0, получено: {self.group_id}")
        if not (1 <= self.semester <= 8):
            raise ValueError(f"semester должен быть от 1 до 8, получено: {self.semester}")
        if self.hours <= 0:
            raise ValueError(f"hours должен быть > 0, получено: {self.hours}")
    
    def validate_for_update(self, updated_fields):
        """Валидация только переданных полей при обновлении"""
        if 'teacher_id' in updated_fields and updated_fields['teacher_id'] <= 0:
            raise ValueError(f"teacher_id должен быть > 0, получено: {updated_fields['teacher_id']}")
        if 'discipline_id' in updated_fields and updated_fields['discipline_id'] <= 0:
            raise ValueError(f"discipline_id должен быть > 0, получено: {updated_fields['discipline_id']}")
        if 'group_id' in updated_fields and updated_fields['group_id'] <= 0:
            raise ValueError(f"group_id должен быть > 0, получено: {updated_fields['group_id']}")
        if 'semester' in updated_fields and not (1 <= updated_fields['semester'] <= 8):
            raise ValueError(f"semester должен быть от 1 до 8, получено: {updated_fields['semester']}")
        if 'hours' in updated_fields and updated_fields['hours'] <= 0:
            raise ValueError(f"hours должен быть > 0, получено: {updated_fields['hours']}")
    
    def create(self, **kwargs):
        """Создание новой записи с валидацией всех полей"""
        self.teacher_id = kwargs.get('teacher_id')
        self.discipline_id = kwargs.get('discipline_id')
        self.group_id = kwargs.get('group_id')
        self.semester = kwargs.get('semester')
        self.hours = kwargs.get('hours')
        self.is_active = kwargs.get('is_active', True)
        
        self.validate_for_create()
        return self.save()
    
    def update_fields(self, **kwargs):
        """Обновление только переданных полей с валидацией"""
        if kwargs:
            self.validate_for_update(kwargs)
            
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            
            # Обновляем только измененные поля
            return self.save(only=list(kwargs.keys()))
        return self.save()
    
    def soft_delete(self):
        """Мягкое удаление через установку is_active = False"""
        self.is_active = False
        return self.save(only=['is_active'])
    
    def restore(self):
        """Восстановление мягко удаленной записи"""
        self.is_active = True
        return self.save(only=['is_active'])
    
    def to_dict(self):
        """Сериализация модели в словарь"""
        return {
            'id': self.id,
            'teacher_id': self.teacher_id,
            'discipline_id': self.discipline_id,
            'group_id': self.group_id,
            'semester': self.semester,
            'hours': self.hours,
            'is_active': self.is_active
        }
    
    @classmethod
    def get_active(cls):
        """Получение только активных записей"""
        return cls.select().where(cls.is_active == True)


def init_db():
    db.connect()
    db.create_tables([Assignment])


if __name__ == '__main__':
    init_db()
