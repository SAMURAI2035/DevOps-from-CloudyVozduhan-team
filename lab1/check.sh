#!/usr/bin/env bash

echo "[1/6] Проверка HTTP -> HTTPS редиректа (app.local):"
curl -s -I http://app.local | grep -E "HTTP/|Location"
echo ""

echo "[2/6] Проверка работы HTTPS (app.local):"
curl -s -k -I https://app.local | grep "HTTP/"
echo ""

echo "[3/6] Проверка авторизации /admin (без логина / с логином):"
echo -n "Без пароля (ожидается 401 Unauthored): "
curl -s -k -o /dev/null -w "%{http_code}\n" https://app.local/admin/
echo -n "С паролем (ожидается 200 OK): "
curl -s -k -u admin:secret https://app.local/admin/
echo ""

echo "[4/6] Проверка Alias (/docs/):"
curl -s -k https://app.local/docs/
echo ""

echo "[5/6] Проверка балансировки бэкенда (/api/health) — 4 запроса:"
for i in {1..4}; do
    echo -n "Запрос $i: "
    curl -s -k https://app.local/api/health
    echo ""
done
echo ""

echo "[6/6] Проверка второго виртуального хоста (second.local):"
curl -s http://second.local
echo ""