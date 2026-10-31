"""
Скрипт для создания новых пользователей в системе банка.

Этот скрипт предназначен ТОЛЬКО для администраторов банка.
Он запускается из командной строки и запрашивает все необходимые данные
для создания учётной записи нового сотрудника.

Как использовать:
    1. Запустите скрипт: python create_user.py
    2. Введите логин нового сотрудника
    3. Введите временный пароль
    4. Укажите, будет ли сотрудник администратором
    5. Укажите, есть ли у сотрудника Telegram
    6. Скрипт создаст пользователя в базе данных

Пример сессии:
    === Создание нового пользователя ===
    (только для администраторов банка)

     Существующие пользователи:
    ------------------------------------------------------------
    ID   Логин                Админ  Telegram Создан
    ------------------------------------------------------------
    1    admin                ✅     ❌       2024-04-14 10:30:00
    ------------------------------------------------------------

     Введите данные нового сотрудника:
    ----------------------------------------
    Логин сотрудника: ivanov
    Временный пароль: temp123
    Администратор? (да/нет): нет
    Есть Telegram? (да/нет): да

     Пользователь 'ivanov' успешно создан

Примечания:
    - При первом запуске базы данных автоматически создаётся демо-администратор
      с логином 'admin' и паролем 'admin123'
    - Обязательно измените пароль демо-администратора после первого входа!
    - Пароль хранится в зашифрованном виде (хешируется)
    - Временный пароль должен быть заменён сотрудником при первом входе
"""

from backend.auth import delete_user, get_user_by_id
from backend.auth import create_user, get_all_users
from backend.db import get_connection


def _users_table_ready() -> bool:
    """Проверяет, что Postgres доступен и таблица users существует."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT to_regclass('public.users') AS exists")
        exists = cursor.fetchone()['exists'] is not None
        cursor.close()
        conn.close()
        return exists
    except Exception:
        return False


def print_header(text: str, char: str = "=", length: int = 60) -> None:
    """
    Выводит отформатированный заголовок с разделителями.

    Args:
        text: Текст заголовка
        char: Символ для разделителя (по умолчанию "=")
        length: Длина разделителя в символах (по умолчанию 60)

    Example:
          Создание пользователя
    """
    print("\n" + char * length)
    print(f"  {text}")
    print(char * length)


def print_user_list() -> None:
    """
    Выводит список всех существующих пользователей в виде таблицы.

    Функция подключается к базе данных, получает список пользователей
    и отображает их в удобном табличном формате.

    Если пользователей нет, выводится соответствующее сообщение.
    Если произошла ошибка подключения, выводится предупреждение.

    Returns:
        None
    """
    try:
        users = get_all_users()
        if users:
            print("\n Существующие пользователи:")
            print(f"{'ID':<4} {'Логин':<20} {'Админ':<6} {'Telegram':<8} {'Создан':<20}")
            for user in users:
                admin_mark = "✅" if user['is_admin'] else "❌"
                tg_mark = "✅" if user['has_telegram'] else "❌"
                # Обрезаем дату до 19 символов (YYYY-MM-DD HH:MM:SS)
                created = str(user['created_at'])[:19] if user['created_at'] else "N/A"
                print(f"{user['id']:<4} {user['username']:<20} {admin_mark:<6} {tg_mark:<8} {created:<20}")
        else:
            print("\n Пользователей пока нет. Создайте первого администратора.")
    except Exception as e:
        print(f"\n  Не удалось загрузить список пользователей: {e}")


def validate_username(username: str) -> tuple:
    """
    Проверяет корректность введённого логина.

    Правила проверки:
        - Логин не может быть пустым
        - Логин должен содержать только буквы, цифры и символ подчёркивания
        - Логин не может начинаться с цифры
        - Логин должен быть длиной от 3 до 30 символов

    Args:
        username: Логин для проверки

    Returns:
        tuple: (is_valid, error_message)
            - is_valid (bool): True если логин корректный
            - error_message (str): Описание ошибки, если есть

    """
    if not username:
        return False, "Логин не может быть пустым"

    if len(username) < 3:
        return False, "Логин должен содержать минимум 3 символа"

    if len(username) > 30:
        return False, "Логин должен содержать максимум 30 символов"

    if username[0].isdigit():
        return False, "Логин не может начинаться с цифры"

    # Разрешены: буквы (любого регистра), цифры, подчёркивание
    allowed_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_"
    for char in username:
        if char not in allowed_chars:
            return False, f"Логин содержит запрещённый символ '{char}'. Разрешены: буквы, цифры и '_'"

    return True, ""


def validate_password(password: str) -> tuple:
    """
    Проверяет надёжность введённого пароля.

    Правила проверки:
        - Пароль не может быть пустым
        - Пароль должен быть длиной минимум 4 символа (для тестовой среды)
        - Рекомендуемая длина: 8+ символов

    Args:
        password: Пароль для проверки

    Returns:
        tuple: (is_valid, warning_message)
            - is_valid (bool): True если пароль допустимый
            - warning_message (str): Предупреждение, если пароль слабый


    """
    if not password:
        return False, "Пароль не может быть пустым"

    if len(password) < 4:
        return False, "Пароль должен содержать минимум 4 символа"

    if len(password) < 8:
        return True, "  Рекомендуется использовать пароль длиннее 8 символов для безопасности"

    return True, ""


def confirm_action(prompt: str, default: str = "нет") -> bool:
    """
    Запрашивает подтверждение действия у пользователя.

    Args:
        prompt: Текст запроса
        default: Ответ по умолчанию ("да" или "нет")

    Returns:
        bool: True если пользователь ответил "да", False в остальных случаях

    Example:

        Удалить пользователя? (да/нет) [нет]:
    """
    default_text = f" [{default}]" if default else ""
    response = input(f"{prompt} (да/нет){default_text}: ").strip().lower()

    if not response and default:
        return default == "да"

    return response == "да"


def create_user_interactive() -> None:
    """
    Интерактивный процесс создания нового пользователя.

    Функция:
        1. Запрашивает у администратора данные нового сотрудника
        2. Проверяет корректность введённых данных
        3. Создаёт пользователя в базе данных
        4. Выводит результат операции

    Returns:
        None
    """
    print_header("Создание нового пользователя")
    print("(только для администраторов банка)")

    # Проверяем, что база доступна и таблица users создана
    if not _users_table_ready():
        print("\n❌ Ошибка: таблица users недоступна.")
        print("   Проверьте, что Postgres запущен, и выполните: python -m backend.db_auth")
        return

    # Показываем список существующих пользователей
    print_user_list()

    print("\n Введите данные нового сотрудника:")

    # Ввод и проверка логина
    while True:
        username = input("Логин сотрудника: ").strip()
        is_valid, error = validate_username(username)
        if is_valid:
            break
        print(f"❌ {error}")

    # Ввод и проверка пароля
    while True:
        password = input("Временный пароль: ").strip()
        is_valid, warning = validate_password(password)
        if is_valid:
            if warning:
                print(warning)
            break
        print(f"❌ {warning}")

    # Ввод роли
    is_admin = confirm_action("Администратор?", default="нет")

    # Ввод наличия Telegram
    has_telegram = confirm_action("Есть Telegram?", default="нет")

    # Показываем введённые данные для подтверждения
    print("Проверьте введённые данные:")
    print(f"  Логин:     {username}")
    print(f"  Пароль:    {'*' * len(password)}")
    print(f"  Админ:     {'Да' if is_admin else 'Нет'}")
    print(f"  Telegram:  {'Да' if has_telegram else 'Нет'}")

    # Подтверждение создания
    if not confirm_action("Создать пользователя?", default="да"):
        print("\n❌ Создание отменено.")
        return

    # Создаём пользователя
    success, message = create_user(username, password, is_admin, has_telegram)

    if success:
        print(f"✅ {message}")

        # Выводим инструкцию для сотрудника
        print("\n инструкция для сотрудника:")
        print(f"   1. Используйте логин: {username}")
        print(f"   2. Введите временный пароль при первом входе")
        print("   3. После входа смените пароль на постоянный")
    else:
        print(f"❌ {message}")


def delete_user_interactive() -> None:
    """
    Интерактивное удаление пользователя из системы.

    Функция:
        1. Показывает список существующих пользователей
        2. Запрашивает ID пользователя для удаления
        3. Подтверждает удаление
        4. Удаляет пользователя из базы данных

    Returns:
        None
    """

    print_header("Удаление пользователя")
    print("(только для администраторов банка)")

    # Проверяем, что база доступна
    if not _users_table_ready():
        print("\n База данных недоступна")
        return

    # Показываем список пользователей
    print_user_list()

    # Запрашиваем ID для удаления
    try:
        user_id = int(input("\n Введите ID пользователя для удаления: ").strip())
    except ValueError:
        print(" Неверный формат ID. Введите число.")
        return

    # Проверяем существование пользователя
    user = get_user_by_id(user_id)
    if not user:
        print(f" Пользователь с ID {user_id} не найден")
        return

    # Показываем информацию о пользователе
    print(f"\n Пользователь найден:")
    print(f"   ID: {user['id']}")
    print(f"   Логин: {user['username']}")
    print(f"   Администратор: {'Да' if user['is_admin'] else 'Нет'}")
    print(f"   Telegram: {'Да' if user['has_telegram'] else 'Нет'}")

    # Защита от удаления единственного администратора
    users = get_all_users()
    admin_count = sum(1 for u in users if u['is_admin'])

    if user['is_admin'] and admin_count <= 1:
        print("\n  НЕЛЬЗЯ УДАЛИТЬ: Это единственный администратор в системе!")
        print("   Сначала назначьте другого администратора.")
        return

    # Подтверждение удаления
    print("\n  ВНИМАНИЕ: Удаление пользователя необратимо.")
    if confirm_action(f"Удалить пользователя '{user['username']}'?", default="нет"):
        success, message = delete_user(user_id)
        if success:
            print(f"\n✅ {message}")
        else:
            print(f"\n❌ {message}")
    else:
        print("\n❌ Удаление отменено.")


def main() -> None:
    """
    Главная функция скрипта.

    Предлагает пользователю выбор действий:
        1. Создать нового пользователя
        2. Удалить существующего пользователя
        3. Выйти

    Returns:
        None
    """

    while True:
        print("Доступные действия:")
        print("  1. Создать нового пользователя")
        print("  2. Удалить пользователя")
        print("  3. Показать список пользователей")
        print("  0. Выйти")

        choice = input("Выберите действие: ").strip()

        if choice == "1":
            create_user_interactive()
        elif choice == "2":
            delete_user_interactive()
        elif choice == "3":
            print_user_list()
            input("\nНажмите Enter для продолжения...")
        elif choice == "0":
            break
        else:
            print("❌ Неверный выбор. Попробуйте снова.")


if __name__ == "__main__":
    """
    Точка входа в скрипт.
    Запуск:
        python create_user.py
    """
    main()
