from peewee import *
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

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


class DatabaseError(Exception):
    """Исключение при ошибке базы данных"""
    pass


class Assignment(Model):
    """
    Модель расписания занятий согласно doc.md
    
    Формат возвращаемых данных (to_dict):
    {
        'id': int,
        'teacher_id': int,
        'group_id': int,
        'discipline_id': int,
        'semester': int,
        'hours': int,
        'is_active': bool
    }
    """
    
    id = AutoField()
    teacher_id = IntegerField()
    group_id = IntegerField()
    discipline_id = IntegerField()
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
    
    @staticmethod
    def validate_id(value: int, field_name: str = "assignment_id") -> None:
        """Валидация ID (должен быть целым числом > 0)"""
        if not isinstance(value, int):
            raise ValidationError(f"{field_name} должен быть целым числом, получено: {type(value).__name__}")
        if value <= 0:
            raise ValidationError(f"{field_name} должен быть > 0, получено: {value}")
    
    @staticmethod
    def validate_boolean(value: bool, field_name: str) -> None:
        """Валидация булевых значений"""
        if not isinstance(value, bool):
            raise ValidationError(f"{field_name} должен быть булевым значением, получено: {type(value).__name__}")
    
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
    def validate_filter_params(cls, teacher_id: Optional[int] = None,
                               group_id: Optional[int] = None,
                               discipline_id: Optional[int] = None,
                               semester: Optional[int] = None) -> None:
        """
        Валидация параметров фильтрации согласно требованиям doc.md
        
        Примечание: Значения None игнорируются (означают "не фильтровать по этому полю")
        
        Args:
            teacher_id: ID преподавателя (должен быть > 0 если указан)
            group_id: ID группы (должен быть > 0 если указан)
            discipline_id: ID дисциплины (должен быть > 0 если указан)
            semester: номер семестра (должен быть 1-8 если указан)
        
        Raises:
            ValidationError: если какой-либо параметр не соответствует ограничениям
        """
        if teacher_id is not None:
            cls.validate_positive(teacher_id, "teacher_id")
        if group_id is not None:
            cls.validate_positive(group_id, "group_id")
        if discipline_id is not None:
            cls.validate_positive(discipline_id, "discipline_id")
        if semester is not None:
            cls.validate_semester(semester)
    
    @classmethod
    def check_uniqueness(cls, teacher_id: int, discipline_id: int, 
                         group_id: int, semester: int, 
                         exclude_id: Optional[int] = None) -> None:
        """
        Проверка уникальности комбинации полей (среди ВСЕХ записей)
        
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
            (cls.semester == semester)
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
            DatabaseError: при ошибке базы данных
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
        except IntegrityError as e:
            # Универсальная обработка ошибок уникальности (работает с разными СУБД)
            error_msg = str(e).lower()
            if "unique" in error_msg or "duplicate" in error_msg:
                raise AssignmentDuplicateError("Нарушение уникальности комбинации полей")
            raise DatabaseError(f"Ошибка целостности БД: {e}")
        except Exception as e:
            logger.error(f"Ошибка при создании Assignment: {e}")
            raise DatabaseError(f"Ошибка при создании записи: {e}")
    
    @classmethod
    def update_assignment(cls, assignment_id: int, **kwargs) -> Dict[str, Any]:
        """
        Обновление существующей записи Assignment
        
        Args:
            assignment_id: ID записи для обновления (>0)
            **kwargs: обновляемые поля (teacher_id, discipline_id, group_id, semester, hours)
                     Значения None игнорируются (не обновляются)
                     
                     Важно: Поле is_active нельзя обновить через этот метод,
                     для этого используются отдельные методы soft_delete() и restore()
        
        Returns:
            Dict[str, Any]: словарь с обновленными данными
        
        Raises:
            ValidationError: при ошибках валидации полей или невалидном ID
            AssignmentNotFoundError: если запись не найдена
            AssignmentDuplicateError: при нарушении уникальности
            DatabaseError: при ошибке базы данных
        """
        # Запрещаем обновление is_active через этот метод
        if 'is_active' in kwargs:
            raise ValidationError("Поле is_active нельзя обновить через update_assignment. "
                                "Используйте методы soft_delete() или restore()")
        
        # Валидация ID
        cls.validate_id(assignment_id, "assignment_id")
        
        # Получение существующей записи
        try:
            assignment = cls.get_by_id(assignment_id)
        except cls.DoesNotExist:
            raise AssignmentNotFoundError(f"Assignment с id={assignment_id} не найден")
        
        # Фильтруем только ключевые поля для проверки уникальности
        key_fields = ['teacher_id', 'discipline_id', 'group_id', 'semester']
        
        # Применяем изменения к объекту (игнорируем None значения)
        updated_fields = []
        changed_key_fields = []
        
        for key, value in kwargs.items():
            if hasattr(assignment, key) and value is not None:
                # Проверяем, действительно ли изменилось значение
                if getattr(assignment, key) != value:
                    setattr(assignment, key, value)
                    updated_fields.append(key)
                    if key in key_fields:
                        changed_key_fields.append(key)
        
        if not updated_fields:
            logger.info(f"Нет изменений для Assignment с id={assignment_id}")
            return assignment.to_dict()
        
        # Валидация обновленных полей (только измененных)
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
        
        # Проверка уникальности, если изменились любые ключевые поля
        if changed_key_fields:
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
        except IntegrityError as e:
            error_msg = str(e).lower()
            if "unique" in error_msg or "duplicate" in error_msg:
                raise AssignmentDuplicateError("Нарушение уникальности комбинации полей")
            raise DatabaseError(f"Ошибка целостности БД: {e}")
        except Exception as e:
            logger.error(f"Ошибка при обновлении Assignment: {e}")
            raise DatabaseError(f"Ошибка при обновлении записи: {e}")
    
    @classmethod
    def soft_delete(cls, assignment_id: int) -> bool:
        """
        Мягкое удаление записи (установка is_active = False)
        
        Args:
            assignment_id: ID записи для удаления (>0)
        
        Returns:
            bool: True если удаление успешно, False если запись уже удалена
        
        Raises:
            ValidationError: при невалидном assignment_id
            AssignmentNotFoundError: если запись не найдена
            DatabaseError: при ошибке базы данных
        """
        # Валидация ID
        cls.validate_id(assignment_id, "assignment_id")
        
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
            raise DatabaseError(f"Ошибка при удалении записи: {e}")
    
    @classmethod
    def restore(cls, assignment_id: int) -> bool:
        """
        Восстановление мягко удаленной записи (установка is_active = True)
        
        Примечание: Проверка уникальности не выполняется, так как запись уже существует в БД
        и была просто деактивирована. Её комбинация полей уже гарантированно уникальна.
        
        Args:
            assignment_id: ID записи для восстановления (>0)
        
        Returns:
            bool: True если восстановление успешно, False если запись уже активна
        
        Raises:
            ValidationError: при невалидном assignment_id
            AssignmentNotFoundError: если запись не найдена
            DatabaseError: при ошибке базы данных
        """
        # Валидация ID
        cls.validate_id(assignment_id, "assignment_id")
        
        # Получение существующей записи
        try:
            assignment = cls.get_by_id(assignment_id)
        except cls.DoesNotExist:
            raise AssignmentNotFoundError(f"Assignment с id={assignment_id} не найден")
        
        if assignment.is_active:
            logger.warning(f"Assignment с id={assignment_id} уже активен")
            return False
        
        # Проверка уникальности не требуется, так как запись уже существует
        # и её комбинация полей гарантированно уникальна среди всех записей
        
        try:
            assignment.is_active = True
            assignment.save(only=['is_active'])
            logger.info(f"Восстановлен Assignment с id={assignment_id}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при восстановлении Assignment с id={assignment_id}: {e}")
            raise DatabaseError(f"Ошибка при восстановлении записи: {e}")
    
    @classmethod
    def get_by_id(cls, assignment_id: int) -> Dict[str, Any]:
        """
        Получение Assignment по ID
        
        Args:
            assignment_id: ID записи (>0)
        
        Returns:
            Dict[str, Any]: словарь с данными записи
        
        Raises:
            ValidationError: при невалидном assignment_id
            AssignmentNotFoundError: если запись не найдена
            DatabaseError: при ошибке базы данных
        """
        cls.validate_id(assignment_id, "assignment_id")
        
        try:
            assignment = super().get_by_id(assignment_id)
            return assignment.to_dict()
        except cls.DoesNotExist:
            raise AssignmentNotFoundError(f"Assignment с id={assignment_id} не найден")
        except Exception as e:
            logger.error(f"Ошибка при получении Assignment с id={assignment_id}: {e}")
            raise DatabaseError(f"Ошибка при получении записи: {e}")
    
    @classmethod
    def get_filtered(cls, teacher_id: Optional[int] = None, 
                     group_id: Optional[int] = None,
                     discipline_id: Optional[int] = None,
                     semester: Optional[int] = None, 
                     is_active: Optional[bool] = None,
                     limit: Optional[int] = None, 
                     offset: Optional[int] = None,
                     order_by: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Получение списка Assignment с фильтрацией и пагинацией
        
        Args:
            teacher_id: ID преподавателя (опционально, с валидацией >0, None = не фильтровать)
            group_id: ID группы (опционально, с валидацией >0, None = не фильтровать)
            discipline_id: ID дисциплины (опционально, с валидацией >0, None = не фильтровать)
            semester: номер семестра (опционально, с валидацией 1-8, None = не фильтровать)
            is_active: статус активности (опционально, булевый тип, None = не фильтровать)
            limit: ограничение количества записей (>=0)
            offset: смещение для пагинации (>=0)
            order_by: поле для сортировки (опционально, например 'id', 'teacher_id', 'semester')
        
        Returns:
            List[Dict[str, Any]]: список словарей с данными записей
        
        Raises:
            ValidationError: если параметры фильтрации или пагинации некорректны
            DatabaseError: при ошибке базы данных
        """
        # Валидация параметров фильтрации (None игнорируется)
        cls.validate_filter_params(teacher_id, group_id, discipline_id, semester)
        
        # Валидация is_active типа (если указан)
        if is_active is not None:
            cls.validate_boolean(is_active, "is_active")
        
        # Валидация параметров пагинации
        cls.validate_pagination_params(limit, offset)
        
        # Валидация параметра сортировки
        valid_sort_fields = ['id', 'teacher_id', 'group_id', 'discipline_id', 'semester', 'hours', 'is_active']
        if order_by is not None and order_by not in valid_sort_fields:
            raise ValidationError(f"order_by должен быть одним из: {', '.join(valid_sort_fields)}")
        
        query = cls.select()
        
        # Применение фильтров (после валидации)
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
        
        # Сортировка (по умолчанию по id, если не указана)
        if order_by is not None:
            query = query.order_by(getattr(cls, order_by))
        else:
            query = query.order_by(cls.id)
        
        try:
            return [assignment.to_dict() for assignment in query]
        except Exception as e:
            logger.error(f"Ошибка при получении списка Assignment: {e}")
            raise DatabaseError(f"Ошибка при получении данных: {e}")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Сериализация модели в словарь в порядке, соответствующем doc.md
        
        Returns:
            Dict[str, Any]: словарь с полями модели в порядке:
                id, teacher_id, group_id, discipline_id, semester, hours, is_active
        """
        return {
            'id': self.id,
            'teacher_id': self.teacher_id,
            'group_id': self.group_id,
            'discipline_id': self.discipline_id,
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
        print("=" * 60)
        print("1. Создание записи")
        result = Assignment.create_assignment(
            teacher_id=1,
            discipline_id=1,
            group_id=1,
            semester=3,
            hours=36
        )
        print(f"Создано: {result}")
        
        print("\n" + "=" * 60)
        print("2. Получение по ID")
        found = Assignment.get_by_id(result['id'])
        print(f"Найдено: {found}")
        
        print("\n" + "=" * 60)
        print("3. Обновление записи")
        updated = Assignment.update_assignment(
            assignment_id=result['id'],
            hours=40,
            semester=4
        )
        print(f"Обновлено: {updated}")
        
        print("\n" + "=" * 60)
        print("4. Мягкое удаление")
        deleted = Assignment.soft_delete(assignment_id=result['id'])
        print(f"Удалено: {deleted}")
        
        print("\n" + "=" * 60)
        print("5. Восстановление (без проверки уникальности)")
        restored = Assignment.restore(assignment_id=result['id'])
        print(f"Восстановлено: {restored}")
        
        print("\n" + "=" * 60)
        print("6. Фильтрация с сортировкой")
        filtered = Assignment.get_filtered(
            teacher_id=1, 
            is_active=True,
            order_by='semester'
        )
        print(f"Результат фильтрации: {filtered}")
        
        print("\n" + "=" * 60)
        print("7. Попытка обновления is_active через update_assignment")
        try:
            invalid = Assignment.update_assignment(
                assignment_id=result['id'],
                is_active=False
            )
        except ValidationError as e:
            print(f"Ожидаемая ошибка: {e}")
        
    except (ValidationError, AssignmentDuplicateError, AssignmentNotFoundError, DatabaseError) as e:
        print(f"Ошибка: {e}")
    except Exception as e:
        print(f"Неожиданная ошибка: {e}")
        logger.error(f"Неожиданная ошибка: {e}", exc_info=True)
    finally:
        close_db()
