@echo off
chcp 65001 >nul
color 0A
title DSchool Deploy Script

echo.
echo ════════════════════════════════════════════════════════════
echo                    🚀 DSCHOOL DEPLOY SCRIPT                 
echo ════════════════════════════════════════════════════════════
echo.

:: Переходим в папку проекта (измени путь на свой)
cd /d "C:\путь\к\твоему\проекту\dschool"

echo [1/4] 📁 Текущая папка: %cd%
echo.

echo [2/4] 📤 Отправка изменений в Git...
echo ────────────────────────────────────────────────────────────
git add .
if errorlevel 1 goto error

git commit -m "Update: %date% %time%"
if errorlevel 1 (
    echo ⚠️  Нет изменений для коммита или ошибка
    echo.
) else (
    echo ✅ Коммит создан
    echo.
)

git push origin main
if errorlevel 1 goto error
echo ✅ Изменения отправлены на GitHub
echo.

echo [3/4] 🖥️  Подключение к серверу и запуск деплоя...
echo ────────────────────────────────────────────────────────────
echo Сервер: 188.124.58.84
echo Домен: dschool-practice.icu
echo.

:: Запускаем деплой на сервере
ssh root@188.124.58.84 "/var/www/dschool/deploy.sh"
if errorlevel 1 goto ssh_error

echo.
echo [4/4] 🔍 Проверка статуса...
echo ────────────────────────────────────────────────────────────

:: Проверяем что сайт доступен
curl -s -o nul -w "HTTP статус: %%{http_code}\n" https://dschool-practice.icu
echo.

echo ════════════════════════════════════════════════════════════
echo                   ✅ ДЕПЛОЙ ЗАВЕРШЕН УСПЕШНО!