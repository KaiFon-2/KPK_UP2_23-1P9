from peewee import *

db = SqliteDatabase('load_assignment.db')

class BaseModel(Model):
    class Meta:
        database = db

class Teacher(BaseModel):
    id = AutoField(primary_key=True)
    full_name = CharField(max_length=100)  # ФИО преподавателя
    email = CharField(unique=True, max_length=100)  # Email
    is_active = BooleanField(default=True)  # Логическое удаление


class Discipline(BaseModel):
    id = AutoField(primary_key=True)
    name = CharField(max_length=100)  # Название дисциплины (Математика, Физика и т.д.)
    hours_per_semester = IntegerField()  # Количество часов в семестре
    is_active = BooleanField(default=True)

class Group(BaseModel):
    id = AutoField(primary_key=True)
    name = CharField(unique=True, max_length=50)  # Название группы (101-ИСТ)
    year_formed = IntegerField()  # Год формирования
    is_active = BooleanField(default=True)

class LoadAssignment(BaseModel):  # Основная таблица распределения нагрузки
    id = AutoField(primary_key=True)
    teacher = ForeignKeyField(Teacher, backref='assignments')
    discipline = ForeignKeyField(Discipline, backref='assignments')
    group = ForeignKeyField(Group, backref='assignments')
    semester = CharField(max_length=20)  # Семестр (Осенний 2024, Весенний 2025)
    hours_assigned = IntegerField()  # Назначенные часы
    is_active = BooleanField(default=True)  # Логическое удаление
