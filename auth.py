from datetime import datetime 
from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user 
from extensions import db, login_manager  # добавляем login_manager
from forms import LoginForm, RegistrationForm 
from models import User 
import json




auth_bp = Blueprint('auth', __name__) 

# Эта функция должна быть зарегистрирована в login_manager, а не в blueprint
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
 # Добавь импорт в начало файла
from logging_utils import log_user_action

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            remember_me = form.remember_me.data
            login_user(user, remember=remember_me)
            
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            # ✅ ДОБАВЬ ЭТО ЛОГИРОВАНИЕ
            log_user_action(
                'login_success', 
                f'Успешный вход пользователя {user.username}',
                additional_data={
                    'remember_me': remember_me,
                    'user_role': user.role,
                    'is_admin': user.is_admin
                }
            )
            
            flash(f"Добро пожаловать, {user.username}!", "success")
            
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('dashboard'))
        
        # ✅ ДОБАВЬ ЭТО ЛОГИРОВАНИЕ
        log_user_action(
            'login_failed', 
            f'Неудачная попытка входа с логином: {form.username.data}',
            additional_data={'attempted_username': form.username.data}
        )
        flash("Неверный логин или пароль.", "danger")
    
    return render_template('login.html', form=form)

@auth_bp.route('/logout') 
@login_required 
def logout():
    username = current_user.username
    user_role = current_user.role
    
    # ✅ ДОБАВЬ ЭТО ЛОГИРОВАНИЕ
    log_user_action(
        'logout', 
        f'Выход пользователя {username}',
        additional_data={'user_role': user_role}
    )
    
    logout_user() 
    flash("Вы вышли из системы.", "info") 
    return redirect(url_for('auth.login'))