from peewee import *
import logging
from typing import Optional, List, Dict, Any

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
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_values = {}
    
    def _save_original_values(self):
        """Сохраняет оригинальные значения полей"""
        self._original_values = {
            'teacher_id': self.teacher_id,
            'discipline_id': self.discipline_id,
            'group_id': self.group_id,
            'semester': self.semester
        }
    
    def validate_positive(self, value: int, field_name: str) -> None:
        """Валидация положительных чисел"""
        if value <= 0:
            raise ValidationError(f"{field_name} должен быть > 0, получено: {value}")
    
    def validate_semester(self, value: int) -> None:
        """Валидация семестра"""
        if not (1 <= value <= 8):
            raise ValidationError(f"semester должен быть от 1 до 8, получено: {value}")
    
    def validate_for_create(self, teacher_id: int, discipline_id: int, 
                           group_id: int, semester: int, hours: int) -> None:
        """
        Валидация всех полей при создании
        
        Args:
            teacher_id: ID преподавателя
            discipline_id: ID дисциплины
            group_id: ID группы
            semester: номер семестра (1-8)
            hours: количество часов
        
        Raises:
            ValidationError: если какое-либо поле не проходит валидацию
        """
        self.validate_positive(teacher_id, "teacher_id")
        self.validate_positive(discipline_id, "discipline_id")
        self.validate_positive(group_id, "group_id")
        self.validate_semester(semester)
        self.validate_positive(hours, "hours")
    
    def validate_for_update(self, **kwargs) -> None:
        """
        Валидация только переданных полей при обновлении
        
        Args:
            **kwargs: обновляемые поля и их значения
        
        Raises:
            ValidationError: если какое-либо поле не проходит валидацию
        """
        if 'teacher_id' in kwargs:
            self.validate_positive(kwargs['teacher_id'], "teacher_id")
        if 'discipline_id' in kwargs:
            self.validate_positive(kwargs['discipline_id'], "discipline_id")
        if 'group_id' in kwargs:
            self.validate_positive(kwargs['group_id'], "group_id")
        if 'semester' in kwargs:
            self.validate_semester(kwargs['semester'])
        if 'hours' in kwargs:
            self.validate_positive(kwargs['hours'], "hours")
    
    def validate_uniqueness(self, exclude_id: Optional[int] = None) -> None:
        """
        Проверка уникальности комбинации полей
        
        Args:
            exclude_id: ID записи, которую нужно исключить из проверки
        
        Raises:
            AssignmentDuplicateError: если запись с такой комбинацией уже существует
        """
        query = Assignment.select().where(
            (Assignment.teacher_id == self.teacher_id) &
            (Assignment.discipline_id == self.discipline_id) &
            (Assignment.group_id == self.group_id) &
            (Assignment.semester == self.semester) &
            (Assignment.is_active == True)
        )
        
        if exclude_id:
            query = query.where(Assignment.id != exclude_id)
        
        if query.exists():
            raise AssignmentDuplicateError(
                f"Assignment с комбинацией teacher_id={self.teacher_id}, "
                f"discipline_id={self.discipline_id}, group_id={self.group_id}, "
                f"semester={self.semester} уже существует"
            )
    
    def create_assignment(self, teacher_id: int, discipline_id: int, 
                          group_id: int, semester: int, hours: int) -> Dict[str, Any]:
        """
        Создание новой записи Assignment
        
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
        self.validate_for_create(teacher_id, discipline_id, group_id, semester, hours)
        
        # Заполнение полей
        self.teacher_id = teacher_id
        self.discipline_id = discipline_id
        self.group_id = group_id
        self.semester = semester
        self.hours = hours
        self.is_active = True
        
        # Проверка уникальности
        self.validate_uniqueness()
        
        # Сохранение
        try:
            self.save()
            logger.info(f"Создан Assignment с id={self.id}")
            return self.to_dict()
        except Exception as e:
            logger.error(f"Ошибка при создании Assignment: {e}")
            raise
    
    def update_assignment(self, assignment_id: int, **kwargs) -> Dict[str, Any]:
        """
        Обновление существующей записи Assignment
        
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
        # Проверка существования записи
        existing = Assignment.get_assignment_by_id(assignment_id)
        if not existing:
            raise AssignmentNotFoundError(f"Assignment с id={assignment_id} не найден")
        
        # Обновляем текущий объект данными из БД
        self.id = existing['id']
        self.teacher_id = existing['teacher_id']
        self.discipline_id = existing['discipline_id']
        self.group_id = existing['group_id']
        self.semester = existing['semester']
        self.hours = existing['hours']
        self.is_active = existing['is_active']
        
        # Сохраняем оригинальные значения
        self._save_original_values()
        
        # Валидация обновляемых полей
        self.validate_for_update(**kwargs)
        
        # Сохраняем старые значения для ключевых полей
        old_key_values = {
            'teacher_id': self.teacher_id,
            'discipline_id': self.discipline_id,
            'group_id': self.group_id,
            'semester': self.semester
        }
        
        # Обновление полей
        updated_fields = []
        for key, value in kwargs.items():
            if hasattr(self, key) and value is not None:
                # Проверяем, действительно ли изменилось значение
                if getattr(self, key) != value:
                    setattr(self, key, value)
                    updated_fields.append(key)
        
        if not updated_fields:
            logger.info(f"Нет изменений для Assignment с id={assignment_id}")
            return self.to_dict()
        
        # Проверка уникальности, если изменились ключевые поля
        key_fields_changed = any(
            field in updated_fields and 
            getattr(self, field) != old_key_values[field]
            for field in ['teacher_id', 'discipline_id', 'group_id', 'semester']
        )
        
        if key_fields_changed:
            self.validate_uniqueness(exclude_id=assignment_id)
        
        # Сохранение
        try:
            self.save(only=updated_fields)
            logger.info(f"Обновлен Assignment с id={self.id}, поля: {updated_fields}")
            return self.to_dict()
        except Exception as e:
            logger.error(f"Ошибка при обновлении Assignment: {e}")
            raise
    
    def soft_delete(self, assignment_id: int) -> bool:
        """
        Мягкое удаление записи (установка is_active = False)
        
        Args:
            assignment_id: ID записи для удаления
        
        Returns:
            bool: True если удаление успешно, False если запись уже удалена
        
        Raises:
            AssignmentNotFoundError: если запись не найдена
        """
        # Проверка существования записи
        existing = Assignment.get_assignment_by_id(assignment_id)
        if not existing:
            raise AssignmentNotFoundError(f"Assignment с id={assignment_id} не найден")
        
        # Обновляем текущий объект
        self.id = existing['id']
        self.is_active = existing['is_active']
        
        if not self.is_active:
            logger.warning(f"Assignment с id={assignment_id} уже удален")
            return False
        
        try:
            self.is_active = False
            result = self.save(only=['is_active'])
            success = bool(result)
            if success:
                logger.info(f"Удален Assignment с id={assignment_id}")
            return success
        except Exception as e:
            logger.error(f"Ошибка при удалении Assignment с id={assignment_id}: {e}")
            raise
    
    def restore(self, assignment_id: int) -> bool:
        """
        Восстановление мягко удаленной записи (установка is_active = True)
        
        Args:
            assignment_id: ID записи для восстановления
        
        Returns:
            bool: True если восстановление успешно, False если запись уже активна
        
        Raises:
            AssignmentNotFoundError: если запись не найдена
        """
        # Проверка существования записи
        existing = Assignment.get_assignment_by_id(assignment_id)
        if not existing:
            raise AssignmentNotFoundError(f"Assignment с id={assignment_id} не найден")
        
        # Обновляем текущий объект
        self.id = existing['id']
        self.is_active = existing['is_active']
        
        if self.is_active:
            logger.warning(f"Assignment с id={assignment_id} уже активен")
            return False
        
        try:
            self.is_active = True
            result = self.save(only=['is_active'])
            success = bool(result)
            if success:
                logger.info(f"Восстановлен Assignment с id={assignment_id}")
            return success
        except Exception as e:
            logger.error(f"Ошибка при восстановлении Assignment с id={assignment_id}: {e}")
            raise
    
    @classmethod
    def get_assignment_by_id(cls, assignment_id: int) -> Optional[Dict[str, Any]]:
        """
        Получение Assignment по ID
        
        Args:
            assignment_id: ID записи
        
        Returns:
            Optional[Dict[str, Any]]: словарь с данными записи или None, если запись не найдена
        """
        try:
            assignment = cls.get_by_id(assignment_id)
            return assignment.to_dict()
        except cls.DoesNotExist:
            logger.debug(f"Assignment с id={assignment_id} не найден")
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
            ValidationError: если limit или offset отрицательные
        """
        # Валидация параметров пагинации
        if limit is not None and limit < 0:
            raise ValidationError(f"limit должен быть >= 0, получено: {limit}")
        if offset is not None and offset < 0:
            raise ValidationError(f"offset должен быть >= 0, получено: {offset}")
        
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
        
        # Сортировка по ID
        query = query.order_by(cls.id)
        
        return [assignment.to_dict() for assignment in query]
    
    @classmethod
    def get_active(cls) -> List[Dict[str, Any]]:
        """
        Получение только активных записей
        
        Returns:
            List[Dict[str, Any]]: список активных записей
        """
        return cls.get_filtered(is_active=True)
    
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
        # Создание записи
        assignment = Assignment()
        result = assignment.create_assignment(
            teacher_id=1,
            discipline_id=1,
            group_id=1,
            semester=3,
            hours=36
        )
        print(f"Создано: {result}")
        
        # Обновление записи
        assignment = Assignment()
        updated = assignment.update_assignment(
            assignment_id=result['id'],
            hours=40,
            semester=4
        )
        print(f"Обновлено: {updated}")
        
        # Мягкое удаление
        assignment = Assignment()
        deleted = assignment.soft_delete(assignment_id=result['id'])
        print(f"Удалено: {deleted}")
        
        # Получение по ID
        found = Assignment.get_assignment_by_id(result['id'])
        print(f"Найдено: {found}")
        
        # Фильтрация
        filtered = Assignment.get_filtered(is_active=True)
        print(f"Активные записи: {filtered}")
        
    except (ValidationError, AssignmentDuplicateError, AssignmentNotFoundError) as e:
        print(f"Ошибка: {e}")
    except Exception as e:
        print(f"Неожиданная ошибка: {e}")
        logger.error(f"Неожиданная ошибка: {e}", exc_info=True)
    finally:
        close_db()
