@echo off
chcp 65001 >nul
color 0A
title DSchool Deploy Manager

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
echo ║  [8] 🔐 Настроить SSH ключи                               ║
echo ║  [9] 🗑️  Управление базой данных                          ║
echo ║  [0] ❌ Выход                                              ║
echo ║                                                            ║
echo ╚════════════════════════════════════════════════════════════╝
echo.
set /p choice="Выбери действие (0-9): "

if "%choice%"=="1" goto full_deploy
if "%choice%"=="2" goto git_only
if "%choice%"=="3" goto deploy_only
if "%choice%"=="4" goto restart_services
if "%choice%"=="5" goto view_logs
if "%choice%"=="6" goto check_status
if "%choice%"=="7" goto ssh_connect
if "%choice%"=="8" goto setup_ssh_keys
if "%choice%"=="9" goto db_management
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
"%PUTTY_PATH%" -load "DSchool_Server" 2>nul
if errorlevel 1 (
    echo Создаю сессию PuTTY...
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

:db_management
cls
echo 🗑️  УПРАВЛЕНИЕ БАЗОЙ ДАННЫХ
echo ════════════════════════════════════════
echo.
echo [1] 🗑️  Удалить ВСЕ базы данных
echo [2] 🗑️  Удалить lab_vulnerable.db
echo [3] 🗑️  Удалить users.db
echo [4] 📊 Показать информацию о БД
echo [5] 💾 Создать резервную копию БД
echo [6] 🔧 Инициализировать БД (создать таблицы)
echo [7] ← Назад в главное меню
echo.
set /p db_choice="Выбери действие (1-7): "

if "%db_choice%"=="1" goto delete_all_db
if "%db_choice%"=="2" goto delete_lab_db
if "%db_choice%"=="3" goto delete_users_db
if "%db_choice%"=="4" goto show_db_info
if "%db_choice%"=="5" goto backup_db
if "%db_choice%"=="6" goto init_db
if "%db_choice%"=="7" goto menu
goto db_management

:delete_all_db
cls
echo ⚠️  УДАЛЕНИЕ ВСЕХ БАЗ ДАННЫХ
echo ════════════════════════════════════════
echo.
echo ВНИМАНИЕ! Будут удалены:
echo - lab_vulnerable.db
echo - instance/users.db
echo.
set /p confirm="Вы уверены? Введите 'YES' для подтверждения: "
if /i "%confirm%"=="YES" (
    echo.
    echo Удаляю базы данных...
    echo %SSH_PASS% | "%PLINK_PATH%" -pw %SSH_PASS% %SSH_USER%@%SSH_HOST% "cd /var/www/dschool && rm -f lab_vulnerable.db && rm -f instance/users.db && echo 'Все базы данных удалены!'"
) else (
    echo Операция отменена.
)
pause
goto db_management

:delete_lab_db
cls
echo ⚠️  УДАЛЕНИЕ lab_vulnerable.db
echo ════════════════════════════════════════
echo.
set /p confirm="Вы уверены? Введите 'YES' для подтверждения: "
if /i "%confirm%"=="YES" (
    echo.
    echo Удаляю lab_vulnerable.db...
    echo %SSH_PASS% | "%PLINK_PATH%" -pw %SSH_PASS% %SSH_USER%@%SSH_HOST% "cd /var/www/dschool && rm -f lab_vulnerable.db && echo 'lab_vulnerable.db удалена!'"
) else (
    echo Операция отменена.
)
pause
goto db_management

:delete_users_db
cls
echo ⚠️  УДАЛЕНИЕ users.db
echo ════════════════════════════════════════
echo.
set /p confirm="Вы уверены? Введите 'YES' для подтверждения: "
if /i "%confirm%"=="YES" (
    echo.
    echo Удаляю users.db...
    echo %SSH_PASS% | "%PLINK_PATH%" -pw %SSH_PASS% %SSH_USER%@%SSH_HOST% "cd /var/www/dschool && rm -f instance/users.db && echo 'users.db удалена!'"
) else (
    echo Операция отменена.
)
pause
goto db_management

:show_db_info
cls
echo 📊 ИНФОРМАЦИЯ О БАЗАХ ДАННЫХ
echo ════════════════════════════════════════
echo.
echo lab_vulnerable.db:
echo ──────────────────
echo %SSH_PASS% | "%PLINK_PATH%" -pw %SSH_PASS% %SSH_USER%@%SSH_HOST% "cd /var/www/dschool && ls -lah lab_vulnerable.db 2>/dev/null || echo 'Файл не найден'"
echo.
echo users.db:
echo ──────────────────
echo %SSH_PASS% | "%PLINK_PATH%" -pw %SSH_PASS% %SSH_USER%@%SSH_HOST% "cd /var/www/dschool && ls -lah instance/users.db 2>/dev/null || echo 'Файл не найден'"
echo.
echo Общий размер:
echo ──────────────────
echo %SSH_PASS% | "%PLINK_PATH%" -pw %SSH_PASS% %SSH_USER%@%SSH_HOST% "cd /var/www/dschool && du -ch lab_vulnerable.db instance/users.db 2>/dev/null | grep total || echo '0 байт'"
pause
goto db_management

:backup_db
cls
echo 💾 РЕЗЕРВНОЕ КОПИРОВАНИЕ БД
echo ════════════════════════════════════════
echo.
echo Создаю резервные копии...
echo %SSH_PASS% | "%PLINK_PATH%" -pw %SSH_PASS% %SSH_USER%@%SSH_HOST% "cd /var/www/dschool && mkdir -p backups && cp lab_vulnerable.db backups/lab_vulnerable_$(date +%%Y%%m%%d_%%H%%M%%S).db 2>/dev/null && echo 'lab_vulnerable.db скопирована' || echo 'lab_vulnerable.db не найдена'"
echo %SSH_PASS% | "%PLINK_PATH%" -pw %SSH_PASS% %SSH_USER%@%SSH_HOST% "cd /var/www/dschool && mkdir -p backups && cp instance/users.db backups/users_$(date +%%Y%%m%%d_%%H%%M%%S).db 2>/dev/null && echo 'users.db скопирована' || echo 'users.db не найдена'"
echo.
echo Список резервных копий:
echo ──────────────────────
echo %SSH_PASS% | "%PLINK_PATH%" -pw %SSH_PASS% %SSH_USER%@%SSH_HOST% "cd /var/www/dschool && ls -la backups/*.db 2>/dev/null | tail -10 || echo 'Резервные копии не найдены'"
pause
goto db_management

:init_db
cls
echo 🔧 ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ
echo ════════════════════════════════════════
echo.
echo Создаю скрипт инициализации...
echo %SSH_PASS% | "%PLINK_PATH%" -pw %SSH_PASS% %SSH_USER%@%SSH_HOST% "cd /var/www/dschool && cat > init_db.py << 'EOF'
#!/usr/bin/env python
import os
import sys
sys.path.insert(0, '/var/www/dschool')

# Создаем необходимые директории
os.makedirs('instance', exist_ok=True)

# Импортируем приложение
from app import create_app, db

# Создаем приложение и контекст
application = create_app()
with application.app_context():
    # Создаем все таблицы
    db.create_all()
    print('Database tables created successfully!')
    
    # Проверяем наличие таблиц
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    print(f'Created tables: {tables}')
EOF"

echo.
echo Запускаю инициализацию БД...
echo %SSH_PASS% | "%PLINK_PATH%" -pw %SSH_PASS% %SSH_USER%@%SSH_HOST% "cd /var/www/dschool && source venv/bin/activate && python init_db.py && rm -f init_db.py"
echo.
echo Перезапускаю сервис...
echo %SSH_PASS% | "%PLINK_PATH%" -pw %SSH_PASS% %SSH_USER%@%SSH_HOST% "systemctl restart dschool"
echo.
echo ✅ База данных инициализирована!
pause
goto db_management

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