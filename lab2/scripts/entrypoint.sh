#!/usr/bin/env bash
set -e

python - <<'PY'
import time, os, psycopg2
url = os.environ.get("DATABASE_URL", "postgresql://admin:admin123@db:5432/ben_db")
for i in range(30):
    try:
        conn = psycopg2.connect(url)
        conn.close()
        print("База данных подключена")
        break
    except psycopg2.OperationalError:
        print(f"БД не готова, ждем")
        time.sleep(1)
else:
    print("База данных не поднялась")
    exit(1)
PY

echo "Инициализация БД"

python -m backend.db_creator
python -m backend.db_auth
python -m backend.init_admin

echo "Запуск сервера"

exec python -m uvicorn backend.api:app --host 0.0.0.0 --port 8000
