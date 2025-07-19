@echo off
chcp 65001 >nul
color 0A
title DSchool Deploy Manager

:: Настройки
set SSH_HOST=188.124.58.84
set SSH_USER=root
set SSH_PASS=dschoolubuntupractice_
set PUTTY_PATH=C:\Program Files\PuTTY\putty.exe
set PLINK_PATH=C:\Program Files\PuTTY\plink.exe

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
echo ║  [8] 🔐 Настроить SSH ключи (рекомендуется)              ║
echo ║  [0] ❌ Выход                                              ║
echo ║                                                            ║
echo ╚════════════════════════════════════════════════════════════╝
echo.
set /p choice="Выбери действие (0-8): "

if "%choice%"=="1" goto full_deploy
if "%choice%"=="2" goto git_only
if "%choice%"=="3" goto deploy_only
if "%choice%"=="4" goto restart_services
if "%choice%"=="5" goto view_logs
if "%choice%"=="6" goto check_status
if "%choice%"=="7" goto ssh_connect
if "%choice%"=="8" goto setup_ssh_keys
if "%choice%"=="0" exit /b 0
goto menu

:full_deploy
cls
echo 🚀 ПОЛНЫЙ ДЕПЛОЙ
echo ════════════════════════════════════════
cd /d "C:\Users\mbpsc\Documents\prod\ds_py"
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
cd /d "C:\Users\mbpsc\Documents\prod\ds_py"
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
echo %SSH_PASS% | "%PLINK_PATH%" -pw %SSH_PASS% %SSH_USER%@%SSH_HOST% "systemctl restart dschool && systemctl reload nginx && echo 'Сервисы перезапущены'"
pause
goto menu

:view_logs
cls
echo 📋 ПОСЛЕДНИЕ ЛОГИ ДЕПЛОЯ
echo ════════════════════════════════════════
echo %SSH_PASS% | "%PLINK_PATH%" -pw %SSH_PASS% %SSH_USER%@%SSH_HOST% "tail -30 /var/www/dschool/deploy.log"
echo.
echo ────────────────────────────────────────
echo 📋 СТАТУС СЕРВИСА
echo ────────────────────────────────────────
echo %SSH_PASS% | "%PLINK_PATH%" -pw %SSH_PASS% %SSH_USER%@%SSH_HOST% "systemctl status dschool --no-pager | tail -20"
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
echo %SSH_PASS% | "%PLINK_PATH%" -pw %SSH_PASS% %SSH_USER%@%SSH_HOST% "systemctl is-active dschool && echo 'Сервис dschool: ✅ Активен' || echo 'Сервис dschool: ❌ Не активен'"
echo %SSH_PASS% | "%PLINK_PATH%" -pw %SSH_PASS% %SSH_USER%@%SSH_HOST% "systemctl is-active nginx && echo 'Сервис nginx: ✅ Активен' || echo 'Сервис nginx: ❌ Не активен'"
echo.
pause
goto menu

:ssh_connect
cls
echo 🛠️  Подключение к серверу...
:: Используем PuTTY с сохраненной сессией
"%PUTTY_PATH%" -load "DSchool_Server" 2>nul
if errorlevel 1 (
    echo Создаю сессию PuTTY...
    :: Альтернатива - использовать plink в интерактивном режиме
    "%PLINK_PATH%" -pw %SSH_PASS% %SSH_USER%@%SSH_HOST%
)
goto menu

:setup_ssh_keys
cls
echo 🔐 НАСТРОЙКА SSH КЛЮЧЕЙ
echo ════════════════════════════════════════
echo.
echo Это поможет избежать ввода пароля каждый раз.
echo.
echo 1. Сначала создадим SSH ключ на вашем компьютере:
echo.
pause
:: Генерация SSH ключа
if not exist "%USERPROFILE%\.ssh" mkdir "%USERPROFILE%\.ssh"
if not exist "%USERPROFILE%\.ssh\id_rsa" (
    ssh-keygen -t rsa -f "%USERPROFILE%\.ssh\id_rsa" -N ""
) else (
    echo SSH ключ уже существует!
)
echo.
echo 2. Теперь скопируем ключ на сервер:
echo.
type "%USERPROFILE%\.ssh\id_rsa.pub" | "%PLINK_PATH%" -pw %SSH_PASS% %SSH_USER%@%SSH_HOST% "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
echo.
echo ✅ SSH ключи настроены!
pause
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
echo %SSH_PASS% | "%PLINK_PATH%" -pw %SSH_PASS% %SSH_USER%@%SSH_HOST% "/var/www/dschool/deploy.sh"
echo ✅ Деплой выполнен
goto :eof