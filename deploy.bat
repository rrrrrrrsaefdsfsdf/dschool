@echo off
chcp 65001 >nul
color 0A
title DSchool Deploy Manager

:menu
cls
echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║                  🚀 DSCHOOL DEPLOY MANAGER                 ║
echo ╠════════════════════════════════════════════════════════════╣
echo ║                                                            ║
echo ║  [1] 🚀 Полный деплой (git + deploy)                      ║
echo ║  [2] 📤 Только отправить в Git                            ║
echo ║  [3] 🖥️  Только деплой на сервер                          ║
echo ║  [4] 🔄 Перезапустить сервисы                             ║
echo ║  [5] 📋 Посмотреть логи                                   ║
echo ║  [6] 🔍 Проверить статус сайта                            ║
echo ║  [7] 🛠️  SSH подключение к серверу                        ║
echo ║  [0] ❌ Выход                                              ║
echo ║                                                            ║
echo ╚════════════════════════════════════════════════════════════╝
echo.
set /p choice="Выбери действие (0-7): "

if "%choice%"=="1" goto full_deploy
if "%choice%"=="2" goto git_only
if "%choice%"=="3" goto deploy_only
if "%choice%"=="4" goto restart_services
if "%choice%"=="5" goto view_logs
if "%choice%"=="6" goto check_status
if "%choice%"=="7" goto ssh_connect
if "%choice%"=="0" exit /b 0
goto menu

:full_deploy
cls
echo 🚀 ПОЛНЫЙ ДЕПЛОЙ
echo ════════════════════════════════════════
cd /d "C:\путь\к\проекту\dschool"
call :git_push
call :deploy_server
echo.
echo ✅ Полный деплой завершен!
pause
goto menu

:git_only
cls
echo 📤 ОТПРАВКА В GIT
echo ════════════════════════════════════════
cd /d "C:\путь\к\проекту\dschool"
call :git_push
pause
goto menu

:deploy_only
cls
echo 🖥️  ДЕПЛОЙ НА СЕРВЕР
echo ════════════════════════════════════════
call :deploy_server
pause
goto menu

:restart_services
cls
echo 🔄 ПЕРЕЗАПУСК СЕРВИСОВ
echo ════════════════════════════════════════
ssh root@188.124.58.84 "systemctl restart dschool && systemctl reload nginx && echo 'Сервисы перезапущены'"
pause
goto menu

:view_logs
cls
echo 📋 ПОСЛЕДНИЕ ЛОГИ ДЕПЛОЯ
echo ════════════════════════════════════════
ssh root@188.124.58.84 "tail -30 /var/www/dschool/deploy.log"
echo.
echo ────────────────────────────────────────
echo 📋 СТАТУС СЕРВИСА
echo ────────────────────────────────────────
ssh root@188.124.58.84 "systemctl status dschool --no-pager | tail -20"
pause
goto menu

:check_status
cls
echo 🔍 ПРОВЕРКА СТАТУСА
echo ════════════════════════════════════════
echo.
echo Проверяю доступность сайта...
curl -s -o nul -w "HTTP статус: %%{http_code}\n" https://dschool-practice.icu
echo.
ssh root@188.124.58.84 "systemctl is-active dschool && echo 'Сервис dschool: ✅ Активен' || echo 'Сервис dschool: ❌ Не активен'"
ssh root@188.124.58.84 "systemctl is-active nginx && echo 'Сервис nginx: ✅ Активен' || echo 'Сервис nginx: ❌ Не активен'"
echo.
pause
goto menu

:ssh_connect
cls
echo 🛠️  Подключение к серверу...
ssh root@188.124.58.84
goto menu

:: Функции
:git_push
echo Добавляю файлы в Git...
git add .
git commit -m "Update: %date% %time%"
git push origin main
echo ✅ Изменения отправлены
goto :eof

:deploy_server
echo Запускаю деплой на сервере...
ssh root@188.124.58.84 "/var/www/dschool/deploy.sh"
echo ✅ Деплой выполнен
goto :eof