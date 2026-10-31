"""
Модуль для инициализации демо-администратора в системе.

Запуск (из корня проекта):
    python -m backend.init_admin

Назначение:
    Создаёт первого администратора в таблице users, если таблица пуста.
    Демо-администратор: логин 'admin', пароль 'admin123'
"""
import hashlib

from backend.db import get_connection

SALT = "bankguard_salt_2024"


def hash_password(password: str) -> str:
    """
    Хеширует пароль с использованием SHA-256 и соли.

    Args:
        password: Пароль в открытом виде

    Returns:
        Хешированный пароль
    """
    return hashlib.sha256((password + SALT).encode()).hexdigest()


def create_demo_admin() -> bool:
    """
    Создаёт демо-администратора, если таблица users пуста.

    Returns:
        True если администратор был создан, False если уже существовал или ошибка
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT to_regclass('public.users') AS exists
        """)
        if not cursor.fetchone()['exists']:
            print("Таблица users не существует")
            print("Запустите сначала: python -m backend.db_auth")
            cursor.close()
            conn.close()
            return False

        cursor.execute('SELECT COUNT(*) AS count FROM users')
        count = cursor.fetchone()['count']

        if count == 0:
            password_hash = hash_password("admin123")
            cursor.execute('''
                INSERT INTO users (username, password_hash, is_admin, has_telegram)
                VALUES (%s, %s, %s, %s)
            ''', ('admin', password_hash, 1, 0))
            conn.commit()
            print("Создан демо-администратор: admin / admin123")
            print("Измените пароль после первого входа!")
            cursor.close()
            conn.close()
            return True
        else:
            print(f"Таблица users не пуста ({count} записей), демо-администратор не создан")
            cursor.close()
            conn.close()
            return False

    except Exception as e:
        print(f"Ошибка при создании демо-администратора: {e}")
        return False


if __name__ == "__main__":
    create_demo_admin()
