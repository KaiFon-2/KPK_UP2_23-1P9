from peewee import *
import logging
from typing import Optional, List, Dict, Any, Union
from playhouse.shortcuts import model_to_dict

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db = SqliteDatabase('university.db')


class AssignmentNotFoundError(Exception):
    """Исключение при отсутствии записи"""
    pass


class AssignmentDuplicateError(Exception):
    """Исключение при нарушении уникальности"""
    pass


class ValidationError(Exception):
    """Исключение при ошибке валидации"""
    pass


class Assignment(Model):
    """Модель расписания занятий согласно doc.md"""
    
    id = AutoField()
    teacher_id = IntegerField()
    discipline_id = IntegerField()
    group_id = IntegerField()
    semester = IntegerField()
    hours = IntegerField()
    is_active = BooleanField(default=True)
    
    class Meta:
        database = db
        table_name = 'assignments'
        indexes = (
            (('teacher_id', 'discipline_id', 'group_id', 'semester'), True),
        )
    
    @staticmethod
    def validate_positive(value: int, field_name: str) -> None:
        """Валидация положительных чисел"""
        if not isinstance(value, int):
            raise ValidationError(f"{field_name} должен быть целым числом, получено: {type(value).__name__}")
        if value <= 0:
            raise ValidationError(f"{field_name} должен быть > 0, получено: {value}")
    
    @staticmethod
    def validate_semester(value: int) -> None:
        """Валидация семестра"""
        if not isinstance(value, int):
            raise ValidationError(f"semester должен быть целым числом, получено: {type(value).__name__}")
        if not (1 <= value <= 8):
            raise ValidationError(f"semester должен быть от 1 до 8, получено: {value}")
    
    @classmethod
    def validate_pagination_params(cls, limit: Optional[int], offset: Optional[int]) -> None:
        """Валидация параметров пагинации"""
        if limit is not None:
            if not isinstance(limit, int):
                raise ValidationError(f"limit должен быть целым числом, получено: {type(limit).__name__}")
            if limit < 0:
                raise ValidationError(f"limit должен быть >= 0, получено: {limit}")
        if offset is not None:
            if not isinstance(offset, int):
                raise ValidationError(f"offset должен быть целым числом, получено: {type(offset).__name__}")
            if offset < 0:
                raise ValidationError(f"offset должен быть >= 0, получено: {offset}")
    
    @classmethod
    def check_uniqueness(cls, teacher_id: int, discipline_id: int, 
                         group_id: int, semester: int, 
                         exclude_id: Optional[int] = None) -> None:
        """
        Проверка уникальности комбинации полей
        
        Args:
            teacher_id: ID преподавателя
            discipline_id: ID дисциплины
            group_id: ID группы
            semester: номер семестра
            exclude_id: ID записи, которую нужно исключить из проверки
        
        Raises:
            AssignmentDuplicateError: если запись с такой комбинацией уже существует
        """
        query = cls.select().where(
            (cls.teacher_id == teacher_id) &
            (cls.discipline_id == discipline_id) &
            (cls.group_id == group_id) &
            (cls.semester == semester) &
            (cls.is_active == True)
        )
        
        if exclude_id:
            query = query.where(cls.id != exclude_id)
        
        if query.exists():
            raise AssignmentDuplicateError(
                f"Assignment с комбинацией teacher_id={teacher_id}, "
                f"discipline_id={discipline_id}, group_id={group_id}, "
                f"semester={semester} уже существует"
            )
    
    @classmethod
    def create_assignment(cls, teacher_id: int, discipline_id: int, 
                          group_id: int, semester: int, hours: int) -> Dict[str, Any]:
        """
        Создание новой записи Assignment (классовый метод)
        
        Args:
            teacher_id: ID преподавателя (>0)
            discipline_id: ID дисциплины (>0)
            group_id: ID группы (>0)
            semester: номер семестра (1-8)
            hours: количество часов (>0)
        
        Returns:
            Dict[str, Any]: словарь с данными созданной записи
        
        Raises:
            ValidationError: при ошибках валидации полей
            AssignmentDuplicateError: при нарушении уникальности
        """
        # Валидация
        cls.validate_positive(teacher_id, "teacher_id")
        cls.validate_positive(discipline_id, "discipline_id")
        cls.validate_positive(group_id, "group_id")
        cls.validate_semester(semester)
        cls.validate_positive(hours, "hours")
        
        # Проверка уникальности
        cls.check_uniqueness(teacher_id, discipline_id, group_id, semester)
        
        # Создание записи
        try:
            assignment = cls.create(
                teacher_id=teacher_id,
                discipline_id=discipline_id,
                group_id=group_id,
                semester=semester,
                hours=hours,
                is_active=True
            )
            logger.info(f"Создан Assignment с id={assignment.id}")
            return assignment.to_dict()
        except Exception as e:
            logger.error(f"Ошибка при создании Assignment: {e}")
            raise
    
    @classmethod
    def update_assignment(cls, assignment_id: int, **kwargs) -> Dict[str, Any]:
        """
        Обновление существующей записи Assignment (классовый метод)
        
        Args:
            assignment_id: ID записи для обновления
            **kwargs: обновляемые поля (teacher_id, discipline_id, group_id, semester, hours)
        
        Returns:
            Dict[str, Any]: словарь с обновленными данными
        
        Raises:
            AssignmentNotFoundError: если запись не найдена
            ValidationError: при ошибках валидации полей
            AssignmentDuplicateError: при нарушении уникальности
        """
        # Получение существующей записи
        try:
            assignment = cls.get_by_id(assignment_id)
        except cls.DoesNotExist:
            raise AssignmentNotFoundError(f"Assignment с id={assignment_id} не найден")
        
        # Сохраняем старые значения ключевых полей
        old_values = {
            'teacher_id': assignment.teacher_id,
            'discipline_id': assignment.discipline_id,
            'group_id': assignment.group_id,
            'semester': assignment.semester
        }
        
        # Применяем изменения к объекту
        updated_fields = []
        for key, value in kwargs.items():
            if hasattr(assignment, key) and value is not None:
                # Проверяем, действительно ли изменилось значение
                if getattr(assignment, key) != value:
                    setattr(assignment, key, value)
                    updated_fields.append(key)
        
        if not updated_fields:
            logger.info(f"Нет изменений для Assignment с id={assignment_id}")
            return assignment.to_dict()
        
        # Валидация обновленных полей (после применения изменений)
        if 'teacher_id' in updated_fields:
            cls.validate_positive(assignment.teacher_id, "teacher_id")
        if 'discipline_id' in updated_fields:
            cls.validate_positive(assignment.discipline_id, "discipline_id")
        if 'group_id' in updated_fields:
            cls.validate_positive(assignment.group_id, "group_id")
        if 'semester' in updated_fields:
            cls.validate_semester(assignment.semester)
        if 'hours' in updated_fields:
            cls.validate_positive(assignment.hours, "hours")
        
        # Проверка уникальности, если изменились ключевые поля
        key_fields_changed = any(
            field in updated_fields and 
            getattr(assignment, field) != old_values[field]
            for field in ['teacher_id', 'discipline_id', 'group_id', 'semester']
        )
        
        if key_fields_changed:
            cls.check_uniqueness(
                assignment.teacher_id,
                assignment.discipline_id,
                assignment.group_id,
                assignment.semester,
                exclude_id=assignment_id
            )
        
        # Сохранение изменений
        try:
            assignment.save(only=updated_fields)
            logger.info(f"Обновлен Assignment с id={assignment_id}, поля: {updated_fields}")
            return assignment.to_dict()
        except Exception as e:
            logger.error(f"Ошибка при обновлении Assignment: {e}")
            raise
    
    @classmethod
    def soft_delete(cls, assignment_id: int) -> bool:
        """
        Мягкое удаление записи (установка is_active = False)
        
        Args:
            assignment_id: ID записи для удаления
        
        Returns:
            bool: True если удаление успешно, False если запись уже удалена
        
        Raises:
            AssignmentNotFoundError: если запись не найдена
        """
        # Получение существующей записи
        try:
            assignment = cls.get_by_id(assignment_id)
        except cls.DoesNotExist:
            raise AssignmentNotFoundError(f"Assignment с id={assignment_id} не найден")
        
        if not assignment.is_active:
            logger.warning(f"Assignment с id={assignment_id} уже удален")
            return False
        
        try:
            assignment.is_active = False
            assignment.save(only=['is_active'])
            logger.info(f"Удален Assignment с id={assignment_id}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при удалении Assignment с id={assignment_id}: {e}")
            raise
    
    @classmethod
    def restore(cls, assignment_id: int) -> bool:
        """
        Восстановление мягко удаленной записи (установка is_active = True)
        
        Args:
            assignment_id: ID записи для восстановления
        
        Returns:
            bool: True если восстановление успешно, False если запись уже активна
        
        Raises:
            AssignmentNotFoundError: если запись не найдена
            AssignmentDuplicateError: если активная запись с такой комбинацией уже существует
        """
        # Получение существующей записи
        try:
            assignment = cls.get_by_id(assignment_id)
        except cls.DoesNotExist:
            raise AssignmentNotFoundError(f"Assignment с id={assignment_id} не найден")
        
        if assignment.is_active:
            logger.warning(f"Assignment с id={assignment_id} уже активен")
            return False
        
        # Проверка уникальности перед восстановлением
        cls.check_uniqueness(
            assignment.teacher_id,
            assignment.discipline_id,
            assignment.group_id,
            assignment.semester,
            exclude_id=assignment_id
        )
        
        try:
            assignment.is_active = True
            assignment.save(only=['is_active'])
            logger.info(f"Восстановлен Assignment с id={assignment_id}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при восстановлении Assignment с id={assignment_id}: {e}")
            raise
    
    @classmethod
    def get_by_id(cls, assignment_id: int) -> Optional['Assignment']:
        """
        Получение Assignment по ID (переопределение метода Peewee)
        
        Args:
            assignment_id: ID записи
        
        Returns:
            Optional[Assignment]: объект Assignment или None, если запись не найдена
        """
        try:
            return super().get_by_id(assignment_id)
        except cls.DoesNotExist:
            return None
    
    @classmethod
    def get_filtered(cls, teacher_id: Optional[int] = None, 
                     group_id: Optional[int] = None,
                     discipline_id: Optional[int] = None,
                     semester: Optional[int] = None, 
                     is_active: Optional[bool] = None,
                     limit: Optional[int] = None, 
                     offset: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Получение списка Assignment с фильтрацией и пагинацией
        
        Args:
            teacher_id: ID преподавателя (опционально)
            group_id: ID группы (опционально)
            discipline_id: ID дисциплины (опционально)
            semester: номер семестра (опционально)
            is_active: статус активности (опционально)
            limit: ограничение количества записей (>=0)
            offset: смещение для пагинации (>=0)
        
        Returns:
            List[Dict[str, Any]]: список словарей с данными записей
        
        Raises:
            ValidationError: если limit или offset некорректны
        """
        # Валидация параметров пагинации
        cls.validate_pagination_params(limit, offset)
        
        query = cls.select()
        
        # Применение фильтров
        if teacher_id is not None:
            cls.validate_positive(teacher_id, "teacher_id")
            query = query.where(cls.teacher_id == teacher_id)
        if group_id is not None:
            cls.validate_positive(group_id, "group_id")
            query = query.where(cls.group_id == group_id)
        if discipline_id is not None:
            cls.validate_positive(discipline_id, "discipline_id")
            query = query.where(cls.discipline_id == discipline_id)
        if semester is not None:
            cls.validate_semester(semester)
            query = query.where(cls.semester == semester)
        if is_active is not None:
            query = query.where(cls.is_active == is_active)
        
        # Пагинация
        if limit is not None:
            query = query.limit(limit)
        if offset is not None:
            query = query.offset(offset)
        
        # Сортировка по ID
        query = query.order_by(cls.id)
        
        return [assignment.to_dict() for assignment in query]
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Сериализация модели в словарь
        
        Returns:
            Dict[str, Any]: словарь с полями модели
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
    try:
        db.connect()
        db.create_tables([Assignment])
        logger.info("База данных успешно инициализирована")
    except Exception as e:
        logger.error(f"Ошибка при инициализации БД: {e}")
        raise


def close_db():
    """Закрытие соединения с БД"""
    if not db.is_closed():
        db.close()
        logger.info("Соединение с БД закрыто")


if __name__ == '__main__':
    init_db()
    
    try:
        # Создание записи (классовый метод)
        result = Assignment.create_assignment(
            teacher_id=1,
            discipline_id=1,
            group_id=1,
            semester=3,
            hours=36
        )
        print(f"Создано: {result}")
        
        # Обновление записи (классовый метод)
        updated = Assignment.update_assignment(
            assignment_id=result['id'],
            hours=40,
            semester=4
        )
        print(f"Обновлено: {updated}")
        
        # Мягкое удаление (классовый метод)
        deleted = Assignment.soft_delete(assignment_id=result['id'])
        print(f"Удалено: {deleted}")
        
        # Восстановление (классовый метод с проверкой уникальности)
        restored = Assignment.restore(assignment_id=result['id'])
        print(f"Восстановлено: {restored}")
        
        # Получение по ID
        found = Assignment.get_by_id(result['id'])
        if found:
            print(f"Найдено: {found.to_dict()}")
        
        # Фильтрация
        filtered = Assignment.get_filtered(is_active=True)
        print(f"Активные записи: {filtered}")
        
        # Попытка создания дубликата (должна выбросить ошибку)
        try:
            duplicate = Assignment.create_assignment(
                teacher_id=1,
                discipline_id=1,
                group_id=1,
                semester=4,
                hours=30
            )
            print(f"Дубликат: {duplicate}")
        except AssignmentDuplicateError as e:
            print(f"Ожидаемая ошибка уникальности: {e}")
        
    except (ValidationError, AssignmentDuplicateError, AssignmentNotFoundError) as e:
        print(f"Ошибка: {e}")
    except Exception as e:
        print(f"Неожиданная ошибка: {e}")
        logger.error(f"Неожиданная ошибка: {e}", exc_info=True)
    finally:
        close_db()
