#!/usr/bin/env bash

echo "[1/8] Проверка HTTP -> HTTPS редиректа (app.local):"
curl -s -I http://app.local | grep -E "HTTP/|Location"
echo ""

echo "[2/8] Проверка работы HTTPS (app.local):"
curl -s -k -I https://app.local | grep "HTTP/"
echo ""

echo "[3/8] Проверка авторизации /admin (без логина / с логином):"
echo -n "Без пароля (ожидается 401 Unauthored): "
curl -s -k -o /dev/null -w "%{http_code}\n" https://app.local/admin/
echo -n "С паролем (ожидается 200 OK): "
curl -s -k -u admin:secret https://app.local/admin/
echo ""

echo "[4/8] Проверка Alias (/docs/):"
curl -s -k https://app.local/docs/
echo ""

echo "[5/8] Проверка балансировки бэкенда (/api/health) — 4 запроса:"
for i in {1..4}; do
    echo -n "Запрос $i: "
    curl -s -k https://app.local/api/health
    echo ""
done
echo ""

echo "[6/8] Проверка второго виртуального хоста (second.local):"
curl -s http://second.local
echo ""

echo "[7/8] Проверка лимита запросов (limit_req на /api/):"
echo "Делаем частые запросы для получения 429:"
for i in {1..5}; do
    curl -s -k -o /dev/null -w "%{http_code} " https://app.local/api/health
done
echo ""
echo ""

echo "[8/8] Проверка кастомной 404 страницы:"
curl -s -k https://app.local/non-existent-page
echo ""