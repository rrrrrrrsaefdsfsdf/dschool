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
 
@auth_bp.route('/register') 
def register(): 
    flash("Регистрация доступна только администраторам", "warning") 
    return redirect(url_for('auth.login')) 
 
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            remember_me = form.remember_me.data
            
            # Эта строка не нужна для remember me функционала
            login_user(user, remember=remember_me)
            
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            flash(f"Добро пожаловать, {user.username}!", "success")
            
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('dashboard'))
        
        flash("Неверный логин или пароль.", "danger")
    
    return render_template('login.html', form=form)







@auth_bp.route('/debug_cookies')
def debug_cookies():
    try:
        cookies_info = {
            'session_cookie': request.cookies.get('session'),
            'remember_cookie': request.cookies.get('remember_token'),
            'all_cookies': dict(request.cookies),
            'is_authenticated': current_user.is_authenticated,
            'user_id': current_user.id if current_user.is_authenticated else None,
            'session_permanent': session.permanent if hasattr(session, 'permanent') else None
        }
        return f"<pre>{json.dumps(cookies_info, indent=2, ensure_ascii=False)}</pre>"
    except Exception as e:
        return f"<pre>Error: {str(e)}</pre>"
 






@auth_bp.route('/logout') 
@login_required 
def logout(): 
    logout_user() 
    flash("Вы вышли из системы.", "info") 
    return redirect(url_for('auth.login'))