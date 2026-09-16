import os
import random
import re
from typing import Optional, Any

import pandas as pd
from faker import Faker

from backend.db import get_connection

fake = Faker('ru_RU')

# Путь строится от расположения файла, а не от текущей директории запуска —
# так скрипт работает что при `python -m backend.db_creator` из корня проекта,
# что при прямом запуске.
COMPLAINTS_TSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'bank_complaints.tsv')


def normalize_phone(phone: Any) -> Optional[str]:
    """Нормализует номер телефона, удаляя все нецифровые символы.

    Args:
        phone: Номер телефона в любом формате (строка, число или NaN).

    Returns:
        Строка, состоящая только из цифр, или None, если входное значение пустое.
    """
    if pd.isna(phone):
        return None
    return re.sub(r'\D', '', str(phone))


class DataPopulator:
    """Класс для наполнения базы данных экосистемы синтетическими данными.

    Этот класс отвечает за создание схемы таблиц, генерацию профилей пользователей,
    имитацию транзакций, звонков и сценариев мошенничества.

    Attributes:
        conn: Подключение к базе данных PostgreSQL.
        cursor: Объект курсора для выполнения SQL-запросов.
    """

    def __init__(self) -> None:
        """Инициализирует подключение к базе данных."""
        self.conn = get_connection()
        self.cursor = self.conn.cursor()

    def setup_schema(self) -> None:
        """Создает структуру таблиц в базе данных.

        Удаляет существующие таблицы, если они есть, и создает новые согласно
        схеме экосистемы (unified_users, bank_clients, transactions и др.).
        """
        self.cursor.execute("""
            DROP TABLE IF EXISTS unified_users;
            DROP TABLE IF EXISTS bank_clients;
            DROP TABLE IF EXISTS bank_transactions;
            DROP TABLE IF EXISTS market_place_delivery;
            DROP TABLE IF EXISTS mobile_build;
            DROP TABLE IF EXISTS mobile_clients;
            DROP TABLE IF EXISTS ecosystem_mapping;
            DROP TABLE IF EXISTS audit_log;

            CREATE TABLE unified_users (
                unique_id TEXT, mobile_id TEXT, bank_id TEXT, marketplace_id TEXT,
                phone_mobile DOUBLE PRECISION, fio_mobile TEXT, address TEXT, account TEXT,
                phone_bank DOUBLE PRECISION, fio_bank TEXT, event_date TEXT, contact_fio TEXT,
                contact_phone DOUBLE PRECISION, address_market TEXT
            );
            CREATE TABLE bank_clients (userId TEXT, account TEXT, phone BIGINT, fio TEXT);
            CREATE TABLE bank_transactions (event_date TEXT, account_out TEXT, account_in TEXT, value DOUBLE PRECISION);
            CREATE TABLE market_place_delivery (event_date TEXT, user_id TEXT, contact_fio TEXT, contact_phone BIGINT,
            address TEXT);
            CREATE TABLE mobile_build (event_date TEXT, from_call BIGINT, to_call BIGINT, duration_sec INTEGER);
            CREATE TABLE mobile_clients (client_id TEXT, phone BIGINT, fio TEXT, address TEXT);
            CREATE TABLE ecosystem_mapping (unique_id TEXT, mobile_id TEXT, bank_id TEXT, marketplace_id TEXT);

            -- Новая таблица: раньше audit_log просто печатался в консоль,
            -- теперь это реальная запись в БД (эндпоинт /investigate пишет сюда,
            -- эндпоинт /audit-log читает).
            CREATE TABLE audit_log (
                id SERIAL PRIMARY KEY,
                user_id TEXT NOT NULL,
                action TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)
        self.conn.commit()

    def generate_data(self, n_users: int = 100, n_frauds: int = 10) -> None:
        """Генерирует синтетические данные и наполняет ими таблицы.

        Процесс включает создание "мастер-данных" пользователей, наполнение
        источников (банк, мобильный оператор, маркетплейс), имитацию звонков
        злоумышленников и последующих подозрительных транзакций.

        Args:
            n_users: Общее количество уникальных пользователей для генерации.
            n_frauds: Количество генерируемых сценариев мошенничества.
        """
        users_pool = []
        for i in range(n_users):
            phone = int(f"79{random.randint(100000000, 999999999)}")
            user = {
                'unique_id': f"UID_{i + 1:03d}",
                'fio': fake.name(),
                'phone': phone,
                'address': fake.address(),
                'bank_id': f"B_{fake.unique.random_int(1000, 9999)}",
                'mobile_id': f"MOB_{fake.unique.random_int(1000, 9999)}",
                'market_id': f"MKT_{fake.unique.random_int(1000, 9999)}",
                'account': f"40817810{random.randint(100000000000, 999999999999)}",
                'is_fraudster': False
            }
            users_pool.append(user)

        fraudsters = random.sample(users_pool, n_frauds)
        for f in fraudsters:
            f['is_fraudster'] = True

        complaints = []

        for u in users_pool:
            self.cursor.execute("INSERT INTO bank_clients VALUES (%s,%s,%s,%s)",
                                 (u['bank_id'], u['account'], u['phone'], u['fio']))
            self.cursor.execute("INSERT INTO mobile_clients VALUES (%s,%s,%s,%s)",
                                 (u['mobile_id'], u['phone'], u['fio'], u['address']))
            self.cursor.execute("INSERT INTO ecosystem_mapping VALUES (%s,%s,%s,%s)",
                                 (u['unique_id'], u['mobile_id'], u['bank_id'], u['market_id']))

            if random.random() > 0.3:
                self.cursor.execute("INSERT INTO market_place_delivery VALUES (%s,%s,%s,%s,%s)",
                                     (fake.date_this_month().strftime('%Y-%m-%d'), u['market_id'],
                                      u['fio'], u['phone'], u['address']))

            self.cursor.execute("""
                INSERT INTO unified_users VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (u['unique_id'], u['mobile_id'], u['bank_id'], u['market_id'],
                  u['phone'], u['fio'], u['address'], u['account'],
                  u['phone'], u['fio'], fake.date_this_month().strftime('%Y-%m-%d'),
                  u['fio'], u['phone'], u['address']))

        victims = [u for u in users_pool if not u['is_fraudster']]

        for fraudster in fraudsters:
            victim = random.choice(victims)
            amount = random.choice([1500, 5000, 12000, 45000, 90000])
            dt_call = fake.date_time_this_month()
            dt_trans = dt_call + pd.Timedelta(minutes=random.randint(5, 30))

            self.cursor.execute("INSERT INTO mobile_build VALUES (%s,%s,%s,%s)",
                                 (dt_call.strftime('%Y-%m-%d %H:%M:%S'),
                                  fraudster['phone'], victim['phone'], random.randint(30, 300)))

            self.cursor.execute("INSERT INTO bank_transactions VALUES (%s,%s,%s,%s)",
                                 (dt_trans.strftime('%Y-%m-%d %H:%M:%S'),
                                  victim['account'], fraudster['account'], amount))

            complaints.append({
                'userId': victim['bank_id'],
                'text': f"Помогите! {amount} руб. украли со счета после звонка.",
                'event_date': (dt_trans + pd.Timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')
            })

        for _ in range(n_users * 2):
            u1, u2 = random.sample(users_pool, 2)
            self.cursor.execute("INSERT INTO bank_transactions VALUES (%s,%s,%s,%s)",
                                 (fake.date_time_this_month().strftime('%Y-%m-%d %H:%M:%S'),
                                  u1['account'], u2['account'], random.randint(100, 2000)))
            self.cursor.execute("INSERT INTO mobile_build VALUES (%s,%s,%s,%s)",
                                 (fake.date_time_this_month().strftime('%Y-%m-%d %H:%M:%S'),
                                  u1['phone'], u2['phone'], random.randint(10, 100)))

        self.conn.commit()

        pd.DataFrame(complaints).to_csv(COMPLAINTS_TSV, sep='\t', index=False)
        print(f"База данных успешно наполнена. Сгенерировано {n_users} пользователей и {n_frauds} кейсов мошенничества.")

    def close(self) -> None:
        """Закрывает соединение с базой данных."""
        self.cursor.close()
        self.conn.close()


if __name__ == "__main__":
    populator = DataPopulator()
    populator.setup_schema()
    populator.generate_data(n_users=1500, n_frauds=150)
    populator.close()
