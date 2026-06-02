from peewee import *
import logging
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
import sys

# Проверка версии Python для гарантии порядка в словарях
if sys.version_info < (3, 7):
    raise RuntimeError("Требуется Python 3.7 или выше для гарантии порядка полей в словарях")

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
    
    Примечание: Порядок ключей гарантирован в Python 3.7+
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
    def validate_not_none(value, field_name: str) -> None:
        """Проверка, что значение не None"""
        if value is None:
            raise ValidationError(f"{field_name} не может быть None")
    
    @staticmethod
    def validate_positive(value: int, field_name: str) -> None:
        """Валидация положительных чисел"""
        Assignment.validate_not_none(value, field_name)
        if not isinstance(value, int):
            raise ValidationError(f"{field_name} должен быть целым числом, получено: {type(value).__name__}")
        if value <= 0:
            raise ValidationError(f"{field_name} должен быть > 0, получено: {value}")
    
    @staticmethod
    def validate_semester(value: int) -> None:
        """Валидация семестра"""
        Assignment.validate_not_none(value, "semester")
        if not isinstance(value, int):
            raise ValidationError(f"semester должен быть целым числом, получено: {type(value).__name__}")
        if not (1 <= value <= 8):
            raise ValidationError(f"semester должен быть от 1 до 8, получено: {value}")
    
    @staticmethod
    def validate_id(value: int, field_name: str = "assignment_id") -> None:
        """Валидация ID (должен быть целым числом > 0)"""
        if value is None:
            return  # None допустим только для опциональных параметров
        if not isinstance(value, int):
            raise ValidationError(f"{field_name} должен быть целым числом, получено: {type(value).__name__}")
        if value <= 0:
            raise ValidationError(f"{field_name} должен быть > 0, получено: {value}")
    
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
                               semester: Optional[int] = None,
                               is_active: Optional[bool] = None) -> None:
        """
        Валидация параметров фильтрации согласно требованиям doc.md
        
        Примечание: Значения None игнорируются (означают "не фильтровать по этому полю")
        
        Args:
            teacher_id: ID преподавателя (должен быть > 0 если указан)
            group_id: ID группы (должен быть > 0 если указан)
            discipline_id: ID дисциплины (должен быть > 0 если указан)
            semester: номер семестра (должен быть 1-8 если указан)
            is_active: статус активности (должен быть булевым если указан)
        
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
        if is_active is not None and not isinstance(is_active, bool):
            raise ValidationError(f"is_active должен быть булевым значением, получено: {type(is_active).__name__}")
    
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
        # Валидация (включая проверку на None)
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
                     для этого используются отдельные методы delete() и restore()
        
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
                                "Используйте методы delete() или restore()")
        
        # Валидация ID
        cls.validate_id(assignment_id, "assignment_id")
        
        # 1. Сначала валидируем все переданные значения
        validation_errors = []
        for key, value in kwargs.items():
            if value is not None:
                try:
                    if key == 'teacher_id':
                        cls.validate_positive(value, "teacher_id")
                    elif key == 'discipline_id':
                        cls.validate_positive(value, "discipline_id")
                    elif key == 'group_id':
                        cls.validate_positive(value, "group_id")
                    elif key == 'semester':
                        cls.validate_semester(value)
                    elif key == 'hours':
                        cls.validate_positive(value, "hours")
                except ValidationError as e:
                    validation_errors.append(str(e))
        
        if validation_errors:
            raise ValidationError("; ".join(validation_errors))
        
        # 2. Получение существующей записи
        try:
            assignment = cls.get(cls.id == assignment_id)
        except cls.DoesNotExist:
            raise AssignmentNotFoundError(f"Assignment с id={assignment_id} не найден")
        
        # Сохраняем старые значения ключевых полей для проверки уникальности
        old_key_values = {
            'teacher_id': assignment.teacher_id,
            'discipline_id': assignment.discipline_id,
            'group_id': assignment.group_id,
            'semester': assignment.semester
        }
        
        # 3. Применяем изменения к объекту
        updated_fields = []
        key_fields_changed = []
        
        for key, value in kwargs.items():
            if hasattr(assignment, key) and value is not None:
                if getattr(assignment, key) != value:
                    setattr(assignment, key, value)
                    updated_fields.append(key)
                    if key in ['teacher_id', 'discipline_id', 'group_id', 'semester']:
                        key_fields_changed.append(key)
        
        if not updated_fields:
            logger.info(f"Нет изменений для Assignment с id={assignment_id}")
            return assignment.to_dict()
        
        # 4. Проверка уникальности, если изменились ключевые поля
        # Примечание: проверка выполняется только при изменении ключевых полей,
        # так как только они влияют на уникальность комбинации (teacher_id, 
        # discipline_id, group_id, semester)
        if key_fields_changed:
            # Проверяем, действительно ли изменились значения
            actually_changed = any(
                getattr(assignment, field) != old_key_values[field]
                for field in key_fields_changed
            )
            if actually_changed:
                cls.check_uniqueness(
                    assignment.teacher_id,
                    assignment.discipline_id,
                    assignment.group_id,
                    assignment.semester,
                    exclude_id=assignment_id
                )
        
        # 5. Сохранение изменений (только измененных полей)
        # Безопасно, так как поле is_active защищено отдельной проверкой
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
    def delete(cls, assignment_id: int) -> bool:
        """
        Мягкое удаление записи (установка is_active = False)
        
        Соответствует методу "Удалить Assignment по ID" из doc.md
        
        Args:
            assignment_id: ID записи для удаления (>0)
        
        Returns:
            bool: True если удаление успешно, False в противном случае
        
        Примечание: Ожидаемые ошибки (невалидный ID, запись не найдена, уже удалена)
        логируются и возвращают False. Критические ошибки БД также возвращают False,
        но логируются с более высоким уровнем.
        """
        # Валидация ID
        try:
            cls.validate_id(assignment_id, "assignment_id")
        except ValidationError as e:
            logger.warning(f"Ошибка валидации ID {assignment_id}: {e}")
            return False
        
        # Получение существующей записи
        try:
            assignment = cls.get(cls.id == assignment_id)
        except cls.DoesNotExist:
            logger.warning(f"Assignment с id={assignment_id} не найден")
            return False
        
        if not assignment.is_active:
            logger.warning(f"Assignment с id={assignment_id} уже удален")
            return False
        
        try:
            assignment.is_active = False
            assignment.save(only=['is_active'])
            logger.info(f"Удален Assignment с id={assignment_id}")
            return True
        except Exception as e:
            # Критическая ошибка БД - логируем и возвращаем False
            logger.error(f"Критическая ошибка при удалении Assignment с id={assignment_id}: {e}", 
                        exc_info=True)
            return False
    
    @classmethod
    def restore(cls, assignment_id: int) -> bool:
        """
        Восстановление мягко удаленной записи (установка is_active = True)
        
        Примечание: Проверка уникальности не выполняется, так как запись уже существует в БД
        и была просто деактивирована. Её комбинация полей уже гарантированно уникальна.
        
        Args:
            assignment_id: ID записи для восстановления (>0)
        
        Returns:
            bool: True если восстановление успешно, False в противном случае
        
        Примечание: Ожидаемые ошибки (невалидный ID, запись не найдена, уже активна)
        логируются и возвращают False. Критические ошибки БД также возвращают False,
        но логируются с более высоким уровнем.
        """
        # Валидация ID
        try:
            cls.validate_id(assignment_id, "assignment_id")
        except ValidationError as e:
            logger.warning(f"Ошибка валидации ID {assignment_id}: {e}")
            return False
        
        # Получение существующей записи
        try:
            assignment = cls.get(cls.id == assignment_id)
        except cls.DoesNotExist:
            logger.warning(f"Assignment с id={assignment_id} не найден")
            return False
        
        if assignment.is_active:
            logger.warning(f"Assignment с id={assignment_id} уже активен")
            return False
        
        try:
            assignment.is_active = True
            assignment.save(only=['is_active'])
            logger.info(f"Восстановлен Assignment с id={assignment_id}")
            return True
        except Exception as e:
            # Критическая ошибка БД - логируем и возвращаем False
            logger.error(f"Критическая ошибка при восстановлении Assignment с id={assignment_id}: {e}", 
                        exc_info=True)
            return False
    
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
            assignment = cls.get(cls.id == assignment_id)
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
                     offset: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Получение списка Assignment с фильтрацией и пагинацией
        
        Args:
            teacher_id: ID преподавателя (опционально, с валидацией >0, None = не фильтровать)
            group_id: ID группы (опционально, с валидацией >0, None = не фильтровать)
            discipline_id: ID дисциплины (опционально, с валидацией >0, None = не фильтровать)
            semester: номер семестра (опционально, с валидацией 1-8, None = не фильтровать)
            is_active: статус активности (опционально, None = не фильтровать)
            limit: ограничение количества записей (>=0)
            offset: смещение для пагинации (>=0)
        
        Returns:
            List[Dict[str, Any]]: список словарей с данными записей (сортировка по id)
        
        Raises:
            ValidationError: если параметры фильтрации или пагинации некорректны
            DatabaseError: при ошибке базы данных
        """
        # Валидация параметров фильтрации (включая is_active)
        cls.validate_filter_params(teacher_id, group_id, discipline_id, semester, is_active)
        
        # Валидация параметров пагинации
        cls.validate_pagination_params(limit, offset)
        
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
        
        # Сортировка по id (как указано в doc.md)
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
                
        Примечание: Порядок ключей гарантирован в Python 3.7+
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
        # Используем safe=True для безопасного создания таблиц
        db.create_tables([Assignment], safe=True)
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
        print("4. Мягкое удаление (метод delete)")
        deleted = Assignment.delete(assignment_id=result['id'])
        print(f"Удалено: {deleted}")
        
        print("\n" + "=" * 60)
        print("5. Попытка удаления несуществующей записи")
        deleted_not_found = Assignment.delete(assignment_id=99999)
        print(f"Результат удаления несуществующей записи: {deleted_not_found} (ожидается False)")
        
        print("\n" + "=" * 60)
        print("6. Восстановление записи")
        restored = Assignment.restore(assignment_id=result['id'])
        print(f"Восстановлено: {restored}")
        
        print("\n" + "=" * 60)
        print("7. Фильтрация")
        filtered = Assignment.get_filtered(teacher_id=1, is_active=True)
        print(f"Результат фильтрации: {filtered}")
        
        print("\n" + "=" * 60)
        print("8. Проверка валидации is_active в фильтрации")
        try:
            invalid_filter = Assignment.get_filtered(is_active="true")
        except ValidationError as e:
            print(f"Ожидаемая ошибка валидации is_active: {e}")
        
        print("\n" + "=" * 60)
        print("9. Проверка предварительной валидации в update_assignment")
        try:
            invalid_update = Assignment.update_assignment(
                assignment_id=result['id'],
                teacher_id=-1
            )
        except ValidationError as e:
            print(f"Ожидаемая ошибка валидации: {e}")
        
    except (ValidationError, AssignmentDuplicateError, AssignmentNotFoundError, DatabaseError) as e:
        print(f"Ошибка: {e}")
    except Exception as e:
        print(f"Неожиданная ошибка: {e}")
        logger.error(f"Неожиданная ошибка: {e}", exc_info=True)
    finally:
        close_db()
