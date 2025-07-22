from flask import request
from flask_login import current_user
from models import UserActionLog
from extensions import db

def log_user_action(action_type, description, target_type=None, target_id=None, additional_data=None):
    """
    Логирует действие пользователя БЕЗ IP адреса
    """
    try:
        user_agent = request.headers.get('User-Agent', '')[:500]
        
        UserActionLog.log_action(
            action_type=action_type,
            description=description,
            user=current_user if current_user.is_authenticated else None,
            target_type=target_type,
            target_id=target_id,
            ip_address=None,  # Больше не логируем IP
            user_agent=user_agent,
            additional_data=additional_data
        )
    except Exception as e:
        print(f"Ошибка логирования: {e}")

def log_admin_action(action_type, description, target_type=None, target_id=None, additional_data=None):
    """Специальное логирование для админских действий БЕЗ IP"""
    log_user_action(f"admin_{action_type}", f"[ADMIN] {description}", target_type, target_id, additional_data)

def log_curator_action(action_type, description, target_type=None, target_id=None, additional_data=None):
    """Специальное логирование для действий кураторов БЕЗ IP"""
    log_user_action(f"curator_{action_type}", f"[CURATOR] {description}", target_type, target_id, additional_data)