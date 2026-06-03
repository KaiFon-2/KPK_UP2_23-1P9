# Вариант 15: Load Assignment Service (Сервис распределения нагрузки)

## Номер варианта и название сервиса

**Вариант:** 15  
**Название сервиса:** Load Assignment Service (Сервис распределения нагрузки)

Сервис не хранит сведения о преподавателях, группах и дисциплинах — эти данные управляются в других сервисах (Teacher Service, Group Service, Discipline Service). Сервис хранит только связи между ними.

---

## ER-диаграмма (Mermaid)

```mermaid
erDiagram
    LOAD_ASSIGNMENT {
        int id PK
        int teacher_id
        int group_id
        int discipline_id
        int semester
        int hours
        bool is_active
    }
