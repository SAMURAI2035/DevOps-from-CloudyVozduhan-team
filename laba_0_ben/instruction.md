# laba 0 BEN — инструкция по запуску
Тут будет небольшая инструкция по запуску нашего проекта для последующийх лаб. 
В обсуждении с командой было принято решение взять мой проект с дисциплины Программирование, и я знатно намучался переносить его на postgres. 
Такое, занятное дело было, но как видите, все получилось. Проект зовут ben, дальше будем так его и называть в отчете, наверное.
## Требования

- Python 3.10+
- PostgreSQL 14+ (установлен и запущен локально)

## 1. Настройка базы данных

Устанавливаем PostgreSQL, если ещё не установлен: [postgresql.org/download](https://www.postgresql.org/download/)

Создем пользователя и базу через `psql`:

```sql
CREATE USER ben WITH PASSWORD 'ben';
CREATE DATABASE ben_db OWNER ben;
```

На всякий случай можно проверить подключение (из обычного терминала, не изнутри psql):

```bash
psql -U ben -d ben_db -h localhost -c "SELECT 1;"
```

По умолчанию приложение подключается к `postgresql://ben:ben@localhost:5432/ben_db`. Если нужны другие данные — задай переменную окружения:

```bash
# Linux/macOS
export DATABASE_URL="postgresql://user:password@localhost:5432/db_name"

# Windows (PowerShell)
$env:DATABASE_URL="postgresql://user:password@localhost:5432/db_name"
```

## 2. Установка зависимостей

Все команды выполняются **из корня проекта** (там, где лежит папка `backend/`).

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
python -m pip install -r requirements.txt
```

## 3. Инициализация базы данных

```bash
# Создать схему таблиц и сгенерировать тестовые данные
python -m backend.db_creator

# Создать таблицу пользователей системы
python -m backend.db_auth

# Создать демо-администратора (admin / admin123)
python -m backend.init_admin
```

## 4. Запуск сервера

```bash
python -m uvicorn backend.api:app --reload --port 8000
```

Приложение само вам напишет в терминале ссылку, где оно запустится

Проверка живости API:

```bash
curl http://localhost:8000/api/health
# {"status":"ok"}
```

## Демо-доступ

| Логин | Пароль    |
|-------|-----------|
| admin | admin123  |

---

