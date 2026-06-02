from peewee import *
from datetime import datetime

db = SqliteDatabase('university.db')

class BaseModel(Model):
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)
    is_deleted = BooleanField(default=False)
    deleted_at = DateTimeField(null=True)
    
    def soft_delete(self):
        self.is_deleted = True
        self.deleted_at = datetime.now()
        self.save()
    
    def save(self, *args, **kwargs):
        if self.id:
            self.updated_at = datetime.now()
        else:
            self.created_at = datetime.now()
        return super().save(*args, **kwargs)
    
    class Meta:
        database = db

class Schedule(BaseModel):
    teacher_id = IntegerField()
    group_id = IntegerField()
    discipline_id = IntegerField()
    semester = IntegerField()
    hours = IntegerField()
    schedule_date = DateField()
    
    def validate(self):
        if self.teacher_id <= 0:
            raise ValueError(f"teacher_id должен быть > 0, получено: {self.teacher_id}")
        if self.group_id <= 0:
            raise ValueError(f"group_id должен быть > 0, получено: {self.group_id}")
        if self.discipline_id <= 0:
            raise ValueError(f"discipline_id должен быть > 0, получено: {self.discipline_id}")
        if not (1 <= self.semester <= 8):
            raise ValueError(f"semester должен быть от 1 до 8, получено: {self.semester}")
        if self.hours <= 0:
            raise ValueError(f"hours должен быть > 0, получено: {self.hours}")
    
    def save(self, *args, **kwargs):
        self.validate()
        return super().save(*args, **kwargs)
    
    class Meta:
        table_name = 'schedule'

def init_db():
    db.connect()
    db.create_tables([Schedule])

if __name__ == '__main__':
    init_db()
