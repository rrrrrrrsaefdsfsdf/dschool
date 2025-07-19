#!/bin/bash
cd /var/www/dschool
echo "📥 Получение обновлений..."
git pull origin main

source venv/bin/activate
echo "📦 Обновление зависимостей..."
pip install -r requirements.txt

echo "🔄 Перезапуск сервисов..."
systemctl restart dschool
systemctl reload nginx

echo "✅ Обновление завершено!"
echo "Время: $(date)"
