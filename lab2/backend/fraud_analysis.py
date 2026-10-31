"""Модуль для расследования мошеннических транзакций в банковской экосистеме.

Этот модуль извлекает суммы из текста жалоб, ищет соответствующие транзакции
в базе данных PostgreSQL и формирует детальные профили пользователей с тегами риска.

Раньше использовал aiosqlite (асинхронный sqlite). Postgres-клиенты для Python
(psycopg2) синхронные, поэтому сам доступ к БД теперь синхронный, а наружу
(в FastAPI) отдаётся через run_in_threadpool — чтобы не блокировать event loop
и не менять сигнатуры вызовов в api.py (там всё так же `await investigator...`).
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi.concurrency import run_in_threadpool

from backend.db import get_connection

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class AmountExtractor:
    """Извлекает сумму транзакции из текстового описания жалобы."""

    def __init__(self) -> None:
        """Инициализирует регулярное выражение для поиска денежных сумм."""
        self._pattern = re.compile(r'([\d\s\.]+)[\s]?(?:руб|р|₽)', re.IGNORECASE)

    def extract(self, text: str) -> Optional[int]:
        """Парсит текст для поиска суммы.

        Args:
            text: Строка текста жалобы.

        Returns:
            Целое число (сумма) или None, если сумма не найдена или некорректна.
        """
        if not text or pd.isna(text):
            return None

        match = self._pattern.search(text)
        if match:
            clean_number = re.sub(r'[\s\.]', '', match.group(1))
            try:
                return int(clean_number)
            except ValueError:
                return None
        return None


class EcosystemDB:
    """Класс для синхронного взаимодействия с базой данных транзакций экосистемы."""

    def __init__(self) -> None:
        """Инициализирует объект без открытого соединения (открывается в connect())."""
        self.conn = None

    def connect(self) -> None:
        """Устанавливает соединение с базой данных."""
        self.conn = get_connection()

    def close(self) -> None:
        """Закрывает соединение с базой данных."""
        if self.conn:
            self.conn.close()

    def find_transaction(self, victim_id: str, amount: int) -> Optional[Dict[str, Any]]:
        """Ищет последнюю транзакцию по ID жертвы и сумме.

        Args:
            victim_id: Идентификатор пострадавшего (userId).
            amount: Сумма транзакции.

        Returns:
            Строка результата запроса (dict) или None.
        """
        query = """
            SELECT
                v.fio AS victim_name,
                f.fio AS fraud_name,
                t.event_date AS date,
                f.userid AS fraud_bank_id
            FROM bank_clients v
            JOIN bank_transactions t ON t.account_out = v.account
            JOIN bank_clients f ON f.account = t.account_in
            WHERE v.userid = %s AND t.value = %s
            ORDER BY t.event_date DESC
            LIMIT 1
        """
        if not self.conn:
            return None

        with self.conn.cursor() as cursor:
            cursor.execute(query, (victim_id, amount))
            return cursor.fetchone()

    def get_user_profile_data(self, bank_id: str) -> Optional[Dict[str, Any]]:
        """Собирает комплексные данные о пользователе из разных таблиц.

        Args:
            bank_id: ID пользователя в банковской системе.

        Returns:
            Словарь со списками транзакций, звонков и заказов или None.
        """
        if not self.conn:
            return None

        with self.conn.cursor() as cursor:
            cursor.execute("SELECT * FROM unified_users WHERE bank_id = %s", (bank_id,))
            user = cursor.fetchone()
            if not user:
                return None

            account = user['account']

            cursor.execute("""
                SELECT DISTINCT v.userid, v.fio AS author_name
                FROM bank_clients v
                JOIN bank_transactions t ON t.account_out = v.account
                WHERE t.account_in = %s
            """, (account,))
            victims = cursor.fetchall()

            cursor.execute("""
                SELECT * FROM bank_transactions
                WHERE account_out = %s OR account_in = %s
                LIMIT 10
            """, (account, account))
            transfers = cursor.fetchall()

            calls = []
            if user['phone_mobile']:
                phone = str(int(user['phone_mobile']))
                cursor.execute("""
                    SELECT * FROM mobile_build
                    WHERE from_call = %s OR to_call = %s
                    LIMIT 10
                """, (phone, phone))
                calls = cursor.fetchall()

            orders = []
            if user['marketplace_id']:
                cursor.execute("""
                    SELECT * FROM market_place_delivery
                    WHERE user_id = %s
                    LIMIT 10
                """, (user['marketplace_id'],))
                orders = cursor.fetchall()

        return {
            "user": user,
            "victims": victims,
            "transfers": transfers,
            "calls": calls,
            "orders": orders
        }

    def get_calls_between(self, fraud_id: str, victim_id: str) -> List[Dict[str, Any]]:
        """Получает историю звонков между предполагаемым мошенником и жертвой."""
        with self.conn.cursor() as cursor:
            phone_query = "SELECT phone FROM bank_clients WHERE userid = %s"
            cursor.execute(phone_query, (fraud_id,))
            f_row = cursor.fetchone()
            cursor.execute(phone_query, (victim_id,))
            v_row = cursor.fetchone()

            if not f_row or not v_row:
                return None

            f_phone, v_phone = f_row['phone'], v_row['phone']
            calls_query = """
                SELECT from_call AS "from", to_call AS "to",
                       duration_sec AS duration, event_date AS date
                FROM mobile_build
                WHERE (from_call = %s AND to_call = %s)
                   OR (from_call = %s AND to_call = %s)
            """
            cursor.execute(calls_query, (f_phone, v_phone, v_phone, f_phone))
            return cursor.fetchall()

    def get_delivery_for(self, fraud_id: str) -> Dict[str, Any]:
        """Получает данные о доставках маркетплейса для аккаунта."""
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT marketplace_id FROM ecosystem_mapping WHERE bank_id = %s",
                (fraud_id,)
            )
            mapping = cursor.fetchone()

            if not mapping:
                return {"data": [], "message": "No marketplace account found"}

            cursor.execute("""
                SELECT address, contact_fio, contact_phone, event_date AS date
                FROM market_place_delivery
                WHERE user_id = %s
            """, (mapping['marketplace_id'],))
            rows = cursor.fetchall()
            return {"data": rows}


class FraudInvestigator:
    """Оркестратор процесса расследования жалоб на мошенничество."""

    def __init__(self, complaints_path: str) -> None:
        """Инициализирует следователя и загружает жалобы.

        Args:
            complaints_path: Путь к TSV-файлу с жалобами.
        """
        self.complaints_path = complaints_path
        self.extractor = AmountExtractor()
        self.complaints_df = self._load_complaints()

    def _load_complaints(self) -> pd.DataFrame:
        """Загружает файл жалоб."""
        try:
            return pd.read_csv(self.complaints_path, sep='\t')
        except Exception as e:
            logger.error("Failed to load complaints file: %s", e)
            return pd.DataFrame()

    def _generate_tags(self, user_row: Dict[str, Any], transfers: List[Dict[str, Any]]) -> List[str]:
        """Генерирует список тегов на основе бизнес-логики."""
        tags = []
        user = dict(user_row)

        address = user.get('address', '')
        if address:
            city_part = address.split(',')[0].strip()
            clean_city = re.sub(r'^(д\.|г\.|с\.|ст\.|к\.|клх|п\.)\s*', '', city_part)
            tags.append(clean_city)

        account = user.get('account')
        stolen_sum = sum(t['value'] for t in transfers if t['account_in'] == account)

        if stolen_sum >= 50000:
            tags.append("Крупная кража")
        elif stolen_sum >= 15000:
            tags.append("Средняя кража")
        elif stolen_sum > 1:
            tags.append("Малая кража")

        mkt_id = user.get('marketplace_id', '') or ''
        mkt_match = re.search(r'\d+', mkt_id)
        if mkt_match:
            tags.append("Wildberries" if int(mkt_match.group()) % 2 == 0 else "Ozon")

        mob_id = user.get('mobile_id', '') or ''
        mob_match = re.search(r'\d+$', mob_id)
        if mob_match:
            op_code = int(mob_match.group()[-2:]) % 4
            operators = {0: "МТС", 1: "МегаФон", 2: "Билайн", 3: "Tele2"}
            tags.append(operators.get(op_code, "Неизвестный оператор"))

        return tags

    def _fetch_full_user_profile_sync(self, bank_id: str) -> Optional[Dict[str, Any]]:
        db = EcosystemDB()
        db.connect()
        try:
            data = db.get_user_profile_data(bank_id)
            if not data:
                return None

            user = data['user']

            actual_complaints = []
            if not self.complaints_df.empty:
                for v in data['victims']:
                    v_complaints = self.complaints_df[self.complaints_df['userId'].astype(str) == str(v['userid'])]
                    for _, c_row in v_complaints.iterrows():
                        actual_complaints.append({
                            "author": v['author_name'],
                            "text": c_row['text']
                        })

            is_fraud = len(actual_complaints) > 0

            phone_val = user['phone_bank']
            formatted_phone = f"+{int(phone_val)}" if phone_val else "Неизвестно"

            profile = {
                "id": user['unique_id'],
                "name": user['fio_bank'],
                "status": "Мошенник" if is_fraud else "Пользователь",
                "phone": formatted_phone,
                "address": user['address'],
                "bankAccount": user['account'],
                "marketplaceId": user['marketplace_id'],
                "mobileId": user['mobile_id'],
                "bankId": user['bank_id'],
                "threat": "_high" if is_fraud else "_low",
                "tags": self._generate_tags(user, data['transfers']),
                "complaints": actual_complaints,
                "transfers": [
                    {
                        "date": t['event_date'],
                        "sum": f"{t['value']} ₽",
                        "from": t['account_out'],
                        "to": t['account_in']
                    } for t in data['transfers']
                ],
                "calls": [
                    {
                        "date": c['event_date'],
                        "duration": f"{c['duration_sec']} сек.",
                        "from": c['from_call'],
                        "to": c['to_call']
                    } for c in data['calls']
                ],
                "orders": [
                    {
                        "date": o['event_date'],
                        "id": o['user_id'],
                        "fio": o['contact_fio'],
                        "phone": (f"+{int(o['contact_phone'])}" if o['contact_phone'] else "Неизвестно"),
                        "address": o['address']
                    } for o in data['orders']
                ],
                "connections": []
            }
            return profile
        finally:
            db.close()

    async def fetch_full_user_profile(self, bank_id: str) -> Optional[Dict[str, Any]]:
        """Собирает и форматирует профиль пользователя (async-обёртка над sync-запросами)."""
        return await run_in_threadpool(self._fetch_full_user_profile_sync, bank_id)

    def _investigate_single_case_sync(self, user_id: str) -> str:
        if self.complaints_df.empty:
            return json.dumps({"error": "Complaints data unavailable"})

        user_complaints = self.complaints_df[
            self.complaints_df['userId'] == user_id
        ].sort_values('event_date', ascending=False)

        if user_complaints.empty:
            return json.dumps({"error": f"No complaints for user {user_id}"})

        complaint_text = user_complaints.iloc[0]['text']
        amount = self.extractor.extract(complaint_text)

        if not amount:
            return json.dumps({"error": "Amount extraction failed"})

        db = EcosystemDB()
        db.connect()
        try:
            trans = db.find_transaction(user_id, amount)
            if trans:
                result = {
                    "transaction_info": {
                        "who": trans['victim_name'],
                        "to_whom": trans['fraud_name'],
                        "when": trans['date'],
                        "amount": amount
                    },
                    "fraud_bank_id": trans['fraud_bank_id']
                }
            else:
                result = {"error": "Transaction not found"}

            return json.dumps(result, indent=4, ensure_ascii=False)
        finally:
            db.close()

    async def investigate_single_case(self, user_id: str) -> str:
        """Проводит анализ жалобы по ID пользователя (async-обёртка над sync-запросами)."""
        return await run_in_threadpool(self._investigate_single_case_sync, user_id)
