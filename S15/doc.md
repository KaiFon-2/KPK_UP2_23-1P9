# Вариант 15 — Load Assignment Service

## ER-диаграмма

```mermaid
erDiagram
    LOAD_ASSIGNMENT {
        int id PK
        int teacher_id
        int discipline_id
        int group_id
        int hours_total
        bool is_active
    }
