"""
Модуль аутентификации и авторизации для банковской системы.

Этот модуль предоставляет полный набор функций для управления пользователями:
- Хеширование и верификация паролей
- Создание, чтение, удаление пользователей
- Управление сессиями
- Проверка прав доступа

Раньше принимал db_path (файл sqlite). Теперь база одна — Postgres,
адрес берётся из переменной окружения DATABASE_URL (см. backend/db.py),
поэтому db_path из сигнатур функций убран.

Зависимости:
    - psycopg2: для работы с базой данных
    - hashlib: для хеширования паролей
    - secrets: для генерации безопасных токенов
"""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple, List, Callable

from backend.db import get_connection

SALT = "bankguard_salt_2024"  # Соль для хеширования паролей
TOKEN_EXPIRY_HOURS = 24  # Срок действия токена в часах


def hash_password(password: str) -> str:
    """
    Хеширует пароль с использованием SHA-256 и соли.

    Args:
        password (str): Исходный пароль в открытом виде

    Returns:
        str: Хешированный пароль (64 символа в шестнадцатеричном формате)
    """
    return hashlib.sha256((password + SALT).encode()).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    """
    Проверяет соответствие пароля сохранённому хешу.

    Args:
        password (str): Пароль для проверки (введённый пользователем)
        password_hash (str): Хеш пароля из базы данных

    Returns:
        bool: True, если пароль верен, иначе False
    """
    return hash_password(password) == password_hash


def create_user(username: str, password: str,
                 is_admin: bool = False, has_telegram: bool = False) -> Tuple[bool, str]:
    """
    Создаёт нового пользователя в системе.

    Args:
        username (str): Уникальный логин сотрудника
        password (str): Временный пароль (должен быть заменён при первом входе)
        is_admin (bool, optional): Флаг администратора. Defaults to False.
        has_telegram (bool, optional): Наличие Telegram. Defaults to False.

    Returns:
        Tuple[bool, str]: (успех, сообщение)
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        password_hash = hash_password(password)
        is_admin_int = 1 if is_admin else 0
        has_telegram_int = 1 if has_telegram else 0

        cursor.execute('''
            INSERT INTO users (username, password_hash, is_admin, has_telegram)
            VALUES (%s, %s, %s, %s)
        ''', (username, password_hash, is_admin_int, has_telegram_int))

        conn.commit()
        cursor.close()
        conn.close()
        return True, f" Пользователь '{username}' успешно создан"

    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
            return False, f" Ошибка, пользователь '{username}' уже существует"
        return False, f"❌ Ошибка, {str(e)}"


def authenticate_user(username: str, password: str) -> Tuple[bool, Optional[str], Optional[Dict]]:
    """
    Аутентифицирует пользователя по логину и паролю.

    При успешной аутентификации генерирует новый токен сессии.

    Args:
        username (str): Логин сотрудника
        password (str): Пароль для проверки

    Returns:
        Tuple[bool, Optional[str], Optional[Dict]]: (успех, токен, данные пользователя)

    Note:
        Токен не сохраняется в базу данных. Сессия создаётся отдельным вызовом create_session().
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if user and verify_password(password, user['password_hash']):
        token = secrets.token_urlsafe(32)
        user_data = {
            'id': user['id'],
            'username': user['username'],
            'is_admin': bool(user['is_admin']),
            'has_telegram': bool(user['has_telegram'])
        }
        return True, token, user_data

    return False, None, None


# Хранилище активных сессий (in-memory — как и в исходной версии;
# для настоящего продакшена стоит вынести в Redis, но это не задача этой лабы)
_active_tokens: Dict[str, Tuple[Dict, datetime]] = {}


def create_session(token: str, user_data: Dict) -> None:
    """
    Создаёт новую сессию для пользователя с ограниченным временем жизни.

    Args:
        token (str): Уникальный токен сессии
        user_data (Dict): Данные пользователя (id, username, is_admin, has_telegram)
    """
    expires_at = datetime.now() + timedelta(hours=TOKEN_EXPIRY_HOURS)
    _active_tokens[token] = (user_data, expires_at)


def validate_token(token: str) -> Optional[Dict]:
    """
    Проверяет валидность токена и возвращает данные пользователя.

    Args:
        token (str): Токен для проверки

    Returns:
        Optional[Dict]: Данные пользователя, если токен валиден, иначе None
    """
    if token in _active_tokens:
        user_data, expires_at = _active_tokens[token]
        if datetime.now() < expires_at:
            return user_data
        else:
            del _active_tokens[token]
    return None


def get_token_expiry(token: str) -> Optional[datetime]:
    """Возвращает время истечения токена, или None если токен не найден."""
    if token in _active_tokens:
        _, expires_at = _active_tokens[token]
        return expires_at
    return None


def logout(token: str) -> bool:
    """Завершает сессию пользователя (удаляет токен)."""
    if token in _active_tokens:
        del _active_tokens[token]
        return True
    return False


def get_all_users() -> List[Dict]:
    """
    Возвращает список всех пользователей системы (без password_hash).
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, username, is_admin, has_telegram, created_at
        FROM users
        ORDER BY created_at DESC
    ''')
    users = [dict(row) for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return users


def get_user_by_id(user_id: int) -> Optional[Dict]:
    """Получает информацию о пользователе по его ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, username, is_admin, has_telegram, created_at
        FROM users
        WHERE id = %s
    ''', (user_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return dict(user) if user else None


def delete_user(user_id: int) -> Tuple[bool, str]:
    """Удаляет пользователя из системы по его ID. Удаление необратимо."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT username FROM users WHERE id = %s', (user_id,))
        user = cursor.fetchone()

        if not user:
            cursor.close()
            conn.close()
            return False, f" Пользователь с ID {user_id} не найден"

        cursor.execute('DELETE FROM users WHERE id = %s', (user_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return True, f" Пользователь '{user['username']}' (ID: {user_id}) удалён"

    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        return False, f" Ошибка при удалении, {str(e)}"


def update_user_password(user_id: int, new_password: str) -> Tuple[bool, str]:
    """Обновляет пароль пользователя."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        password_hash = hash_password(new_password)
        cursor.execute('UPDATE users SET password_hash = %s WHERE id = %s', (password_hash, user_id))

        if cursor.rowcount == 0:
            conn.close()
            return False, f" Пользователь с ID {user_id} не найден"

        conn.commit()
        cursor.close()
        conn.close()
        return True, f" Пароль для пользователя ID {user_id} обновлён"

    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        return False, f" Ошибка: {str(e)}"


def is_token_valid(token: str) -> bool:
    """Быстрая проверка валидности токена."""
    return validate_token(token) is not None


def get_active_sessions_count() -> int:
    """Возвращает количество активных сессий."""
    return len(_active_tokens)


def clear_expired_tokens() -> int:
    """Очищает хранилище от истёкших токенов, возвращает их количество."""
    now = datetime.now()
    expired_tokens = [t for t, (_, exp) in _active_tokens.items() if now >= exp]
    for token in expired_tokens:
        del _active_tokens[token]
    return len(expired_tokens)


def require_auth(func: Callable) -> Callable:
    """Декоратор для проверки авторизации перед выполнением функции."""

    def wrapper(token: str, *args, **kwargs):
        user = validate_token(token)
        if not user:
            return {"error": "Не авторизован. Требуется вход в систему."}, 401
        return func(user, *args, **kwargs)

    return wrapper


def require_admin(func: Callable) -> Callable:
    """Декоратор для проверки прав администратора."""

    def wrapper(token: str, *args, **kwargs):
        user = validate_token(token)
        if not user:
            return {"error": "Не авторизован. Требуется вход в систему."}, 401
        if not user.get('is_admin'):
            return {"error": "Доступ запрещён. Требуются права администратора."}, 403
        return func(user, *args, **kwargs)

    return wrapper


ROLE_DESCRIPTIONS = {
    'admin': {
        'name': 'Администратор',
        'description': 'Полный доступ к системе. Может создавать и удалять пользователей, '
                       'назначать роли, просматривать все отчёты.',
        'permissions': ['create_user', 'delete_user', 'view_all_reports', 'view_calls', 'export_data']
    },
    'investigator': {
        'name': 'Следователь',
        'description': 'Может просматривать жалобы, звонки и выгружать отчёты.',
        'permissions': ['view_complaints', 'view_calls', 'export_data']
    },
    'observer': {
        'name': 'Наблюдатель',
        'description': 'Может только просматривать список жалоб без деталей.',
        'permissions': ['view_complaints_list']
    }
}
