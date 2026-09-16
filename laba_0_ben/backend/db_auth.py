"""
Модуль для создания таблицы сотрудников (users) в общей базе Postgres.
"""

from backend.db import get_connection


def create_users_table() -> None:
    """
    Создаёт таблицу users, если её ещё нет.
    Поля: id, username, password_hash, is_admin, has_telegram, created_at.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0,
            has_telegram INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT NOW()
        )
    ''')

    conn.commit()
    cursor.close()
    conn.close()
    print("Таблица users создана (или уже существовала) в Postgres")


if __name__ == "__main__":
    create_users_table()
