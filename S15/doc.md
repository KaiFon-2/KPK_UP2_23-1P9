**Вариант:** 15  
**Название сервиса:** Load Assignment Service (Сервис распределения нагрузки)

erDiagram
    TEACHER {
        int id PK "Первичный ключ"
        varchar full_name "ФИО преподавателя"
        varchar email "Email"
        boolean is_active "Активен"
    }

    DISCIPLINE {
        int id PK "Первичный ключ"
        varchar name "Название дисциплины"
        int hours_per_semester "Часов в семестре"
        boolean is_active "Активна"
    }

    GROUP {
        int id PK "Первичный ключ"
        varchar name "Название группы"
        int year_formed "Год формирования"
        boolean is_active "Активна"
    }

    LOAD_ASSIGNMENT {
        int id PK "Первичный ключ"
        int teacher_id FK "Ссылка на TEACHER.id"
        int discipline_id FK "Ссылка на DISCIPLINE.id"
        int group_id FK "Ссылка на GROUP.id"
        varchar semester "Семестр"
        int hours_assigned "Назначенные часы"
        boolean is_active "Активна запись"
    }

    TEACHER ||--o{ LOAD_ASSIGNMENT : teaches
    DISCIPLINE ||--o{ LOAD_ASSIGNMENT : taught_in
    GROUP ||--o{ LOAD_ASSIGNMENT : assigned_to
