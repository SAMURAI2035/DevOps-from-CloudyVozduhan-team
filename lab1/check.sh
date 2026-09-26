#!/usr/bin/env bash

echo "[1/9] curl -I http://… → редирект 301 на https:"
curl -s -I http://app.local | grep -E "HTTP/|Location"
echo ""

echo "[2/9] Проверка работы HTTPS (app.local):"
curl -s -k -I https://app.local | grep "HTTP/"
echo ""

echo "[3/9] Проверка авторизации /admin (без логина / с логином):"
echo -n "curl на /admin без пароля → 401: "
curl -s -k -o /dev/null -w "%{http_code}\n" https://app.local/admin/
echo -n "С паролем (ожидается 200 OK): "
curl -s -k -u admin:secret "%{http_code}\n" https://app.local/admin/
echo ""

echo "[4/9] Проверка Alias (/docs/):"
curl -s -k https://app.local/docs/
echo ""

echo "[5/9] Несколько запросов на /api → видно чередование двух инстансов:"
for i in {1..4}; do
    echo -n "Запрос $i: "
    curl -s -k https://app.local/api/health
    echo ""
done
echo ""

echo "[6/9] Проверка второго виртуального хоста (second.local):"
curl -s http://second.local
echo ""

echo "[7/9] Флуд запросами → упираемся в 429:"
for i in {1..10}; do
    curl -s -k -o /dev/null -w "%{http_code} " https://app.local/api/health
done
echo ""

echo "[8/9] Запрос несуществующей страницы → ваша 404:"
curl -s -k https://app.local/non-existent-page
echo ""

echo "[9/9] Запрос с неизвестным/чужим Host → не отдаёт соседний хост:"
curl -s -k -o /dev/null -w "HTTP Code: %{http_code}\n" -H "Host: unknown.local" https://app.local