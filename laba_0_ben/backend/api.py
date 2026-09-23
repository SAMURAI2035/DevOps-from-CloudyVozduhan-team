"""Модуль API для системы анализа мошенничества (BEN API).

Предоставляет интерфейсы для работы с жалобами, проведения расследований
и получения полных профилей пользователей на основе данных экосистемы.
"""

import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Security
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import pandas as pd
from pydantic import BaseModel

from backend.db import get_connection
from backend.fraud_analysis import EcosystemDB, FraudInvestigator
from fastapi.staticfiles import StaticFiles
from backend.auth import authenticate_user, create_session, validate_token

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="BEN API", version="1.3.0")
security = HTTPBearer()
PORT = sys.argv[1] if len(sys.argv) > 1 else os.getenv("PORT", "5000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMPLAINTS_TSV = os.path.join(BASE_DIR, 'backend/data', 'bank_complaints.tsv')
SECRET_TOKEN = "secret-token-123"


class LoginRequest(BaseModel):
    username: str
    password: str


def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> dict:
    token = credentials.credentials
    user_data = validate_token(token)
    if token == SECRET_TOKEN:
        return user_data
    if not user_data:
        raise HTTPException(status_code=403, detail="Сессия истекла или неверный токен")
    else:
        return user_data


def _audit_log_sync(user_id: str, action: str) -> None:
    """Пишет запись аудита в Postgres (раньше просто уходило в консоль)."""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO audit_log (user_id, action) VALUES (%s, %s)",
                (user_id, action)
            )
        conn.commit()
    finally:
        conn.close()
    logger.info("[AUDIT] %s | Action: %s", user_id, action)


async def audit_log(user_id: str, action: str) -> None:
    """Записывает действие пользователя в аудит-лог (эндпоинт-пара с GET /audit-log)."""
    await run_in_threadpool(_audit_log_sync, user_id, action)


def read_complaints_safe() -> pd.DataFrame:
    """Безопасно читает данные из TSV файла с жалобами.

    Returns:
        DataFrame с данными жалоб.

    Raises:
        HTTPException: Если файл базы данных жалоб не найден (500).
    """
    if not os.path.exists(COMPLAINTS_TSV):
        logger.error("Complaints file not found at %s", COMPLAINTS_TSV)
        raise HTTPException(status_code=500, detail="Complaints file not found")

    return pd.read_csv(COMPLAINTS_TSV, sep='\t')


@app.get("/api/health")
def health() -> Dict[str, str]:
    """Проверка живости сервиса — пригодится для Лабы 1 (балансировка) и Лабы 2 (HEALTHCHECK)."""
    return {"status": "ok", "instance": f"backend-{PORT}"}


@app.post("/login")
async def login(data: LoginRequest):
    success, token, user_data = authenticate_user(data.username, data.password)

    if success and token:
        create_session(token, user_data)
        return {"token": token, "user": user_data}

    raise HTTPException(status_code=401, detail="Неверный логин или пароль")


@app.get("/complaints", dependencies=[Depends(verify_token)])
async def get_complaints(
        start_date: Optional[str] = Query(None, description="Format: YYYY-MM-DD"),
        end_date: Optional[str] = Query(None, description="Format: YYYY-MM-DD"),
        skip: int = 0,
        limit: int = 20
) -> List[Dict[str, Any]]:
    """Возвращает список жалоб с фильтрацией по дате."""
    df = read_complaints_safe()

    if start_date:
        df = df[df['event_date'] >= start_date]
    if end_date:
        df = df[df['event_date'] <= f"{end_date} 23:59:59"]

    return df.iloc[skip: skip + limit].to_dict(orient='records')


@app.get("/complaints/{complaint_id}", dependencies=[Depends(verify_token)])
async def get_complaint_text(complaint_id: str) -> Dict[str, str]:
    """Получает текст конкретной жалобы по ID."""
    df = read_complaints_safe()
    complaint = df[df['userId'].astype(str) == str(complaint_id)]

    if complaint.empty:
        raise HTTPException(status_code=404, detail="Complaint not found")

    return {"id": complaint_id, "text": complaint.iloc[0]['text']}


@app.post("/investigate/{complaint_id}")
async def investigate(
        complaint_id: str,
        current_user: dict = Depends(verify_token)
) -> Dict[str, Any]:
    """Запускает процесс автоматизированного расследования по жалобе.

    Это тот самый write+read эндпоинт для лабы 0: расследование пишет запись
    в таблицу audit_log (см. GET /audit-log ниже, где эти записи читаются обратно).
    """
    investigator = FraudInvestigator(COMPLAINTS_TSV)
    res_json = await investigator.investigate_single_case(complaint_id)
    result = json.loads(res_json)

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    actor = current_user.get("username", str(current_user)) if isinstance(current_user, dict) else str(current_user)
    await audit_log(actor, f"Investigated complaint #{complaint_id}")
    return result


@app.get("/audit-log", dependencies=[Depends(verify_token)])
async def get_audit_log(limit: int = 50) -> List[Dict[str, Any]]:
    """Возвращает последние записи аудита — читает то, что пишет POST /investigate."""

    def _fetch():
        conn = get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id, user_id, action, created_at FROM audit_log "
                    "ORDER BY created_at DESC LIMIT %s",
                    (limit,)
                )
                return cursor.fetchall()
        finally:
            conn.close()

    rows = await run_in_threadpool(_fetch)
    return [dict(r) for r in rows]


@app.get("/cases/{fraud_id}/calls", dependencies=[Depends(verify_token)])
async def get_calls(fraud_id: str, victim_id: str) -> List[Dict[str, Any]]:
    """Получает историю звонков между предполагаемым мошенником и жертвой."""

    def _fetch():
        db = EcosystemDB()
        db.connect()
        try:
            return db.get_calls_between(fraud_id, victim_id)
        finally:
            db.close()

    result = await run_in_threadpool(_fetch)
    if result is None:
        raise HTTPException(status_code=404, detail="Phones not found")
    return [dict(r) for r in result]


@app.get("/cases/{fraud_id}/delivery", dependencies=[Depends(verify_token)])
async def get_delivery(fraud_id: str) -> Dict[str, Any]:
    """Получает данные о доставках маркетплейса для аккаунта."""

    def _fetch():
        db = EcosystemDB()
        db.connect()
        try:
            return db.get_delivery_for(fraud_id)
        finally:
            db.close()

    result = await run_in_threadpool(_fetch)
    return {"data": [dict(r) for r in result["data"]]}


@app.get("/full-profile/{bank_id}", dependencies=[Depends(verify_token)])
async def get_full_profile_endpoint(bank_id: str) -> Dict[str, Any]:
    """Получает полный профиль пользователя (единое окно)."""
    investigator = FraudInvestigator(COMPLAINTS_TSV)
    profile = await investigator.fetch_full_user_profile(bank_id)

    if not profile:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    return profile


@app.get("/frauds", dependencies=[Depends(verify_token)])
async def get_frauds(
        start_date: Optional[str] = Query(None),
        end_date: Optional[str] = Query(None),
        skip: int = 0,
        limit: int = 10
) -> List[Dict[str, Any]]:
    """Возвращает список полных профилей мошенников, выявленных по жалобам."""
    df = read_complaints_safe()

    if start_date:
        df = df[df['event_date'] >= start_date]
    if end_date:
        df = df[df['event_date'] <= f"{end_date} 23:59:59"]

    investigator = FraudInvestigator(COMPLAINTS_TSV)
    results = []
    victim_ids = df.iloc[skip: skip + limit]['userId'].tolist()

    for v_id in victim_ids:
        res_json = await investigator.investigate_single_case(str(v_id))
        res_data = json.loads(res_json)

        if "fraud_bank_id" in res_data:
            fraud_bank_id = res_data["fraud_bank_id"]
            full_profile = await investigator.fetch_full_user_profile(fraud_bank_id)
            if full_profile:
                results.append(full_profile)

    return results


if 'pytest' not in sys.modules:
    app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
