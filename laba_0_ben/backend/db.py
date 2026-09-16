"""Общее подключение к PostgreSQL для всего backend'а BEN.

Раньше проект использовал россыпь sqlite-файлов (users.db, ecosystem_data.db).
Теперь всё лежит в одной базе Postgres — двух отдельных БД (auth + ecosystem)
не делаем, чтобы не плодить сервисы: в реальном банке это тоже обычно один
кластер с разными схемами/таблицами.
"""

import os
import psycopg2
import psycopg2.extras

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://ben:ben@localhost:5432/ben_db",
)


def get_connection():
    """Возвращает новое соединение с БД, строки отдаются как dict (RealDictRow)."""
    return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
