import os
import subprocess
import sys
import pathlib
from dotenv import load_dotenv, dotenv_values
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_assets import Bundle
from flask_login import login_required, current_user
from flask_wtf.csrf import CSRFError
from config import DevelopmentConfig, ProductionConfig
from extensions import login_manager, csrf, migrate, assets
from logging_utils import log_user_action
from models import Course, CourseModeration, UserCourse, db, Task, Lab, CuratorContact, UserTaskAnswer, UserLabProgress, LabProgress, UserTaskProgress
from curator_routes import curator_bp


dotenv_path = pathlib.Path(__file__).parent / '.env'
load_dotenv(dotenv_path, verbose=True)

def create_app():
    app = Flask(__name__)
    
    env = os.environ.get('FLASK_ENV', 'production').lower().strip()
    
    if env in ['development', 'dev', 'debug']:
        app.config.from_object(DevelopmentConfig)
    else:
        app.config.from_object(ProductionConfig)
    
    db.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)
    
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Пожалуйста, войдите в систему'
    login_manager.login_message_category = 'info'
    login_manager.session_protection = 'strong'
    
    login_manager.remember_cookie_name = app.config.get('REMEMBER_COOKIE_NAME', 'remember_token')
    login_manager.remember_cookie_duration = app.config.get('REMEMBER_COOKIE_DURATION')
    login_manager.remember_cookie_secure = app.config.get('SESSION_COOKIE_SECURE', False)
    login_manager.remember_cookie_httponly = app.config.get('REMEMBER_COOKIE_HTTPONLY', True)
    login_manager.remember_cookie_samesite = app.config.get('SESSION_COOKIE_SAMESITE', 'Lax')
    
    assets.init_app(app)

    with app.app_context():
        assets.debug = app.config.get('ASSETS_DEBUG', False)
        css_bundle = Bundle('styles.css','lab-styles.css',
                            filters='cssmin' if not app.config.get('ASSETS_DEBUG') else None,
                            output='gen/packed.%(version)s.css')
        assets.register('css_all', css_bundle)
        
        if app.config.get('USE_OBFUSCATED', False):
            js_bundle = Bundle('gen/misc.obf.js', 'gen/tasks.obf.js',
                            output='gen/app.%(version)s.js')
        else:
            js_bundle = Bundle('misc.js', 'tasks.js',
                            filters='jsmin' if not app.config.get('ASSETS_DEBUG') else None,
                            output='gen/app.%(version)s.js')
        assets.register('js_all', js_bundle)

    from models import User

    def get_admin_stats():
        from datetime import datetime, timedelta
        total_users = User.query.count()
        admin_count = User.query.filter_by(is_admin=True).count()
        curator_count = User.query.filter_by(role='curator').count()
        total_tasks = Task.query.count()
        total_labs = Lab.query.count()
        total_courses = Course.query.count()

        yesterday = datetime.utcnow() - timedelta(days=1)
        new_users_day = User.query.filter(User.created_at >= yesterday).count()
        week_ago = datetime.utcnow() - timedelta(days=7)
        active_users_week = User.query.filter(User.last_login >= week_ago).count()

        try:
            pending_answers = UserTaskAnswer.query.filter_by(status='pending').count()
        except:
            try:
                pending_answers = UserTaskProgress.query.filter_by(is_checked=False).count()
            except:
                pending_answers = 0
                
        try:
            solved_tasks_count = UserTaskAnswer.query.filter_by(status='approved').count()
        except:
            try:
                solved_tasks_count = UserTaskProgress.query.filter_by(is_approved=True).count()
            except:
                solved_tasks_count = 0
                
        try:
            solved_labs_count = UserLabProgress.query.filter_by(is_solved=True).count()
        except:
            try:
                solved_labs_count = LabProgress.query.filter_by(is_solved=True).count()
            except:
                solved_labs_count = 0

        moderation_queue = CourseModeration.query.filter_by(status='pending').count()

        total_possible_tasks = total_users * total_tasks if total_users and total_tasks else 0
        task_progress = round((solved_tasks_count / total_possible_tasks * 100), 1) if total_possible_tasks > 0 else 0
        total_possible_labs = total_users * total_labs if total_users and total_labs else 0
        lab_progress = round((solved_labs_count / total_possible_labs * 100), 1) if total_possible_labs > 0 else 0

        return {
            'total_users': total_users,
            'admin_count': admin_count,
            'curator_count': curator_count,
            'new_users_day': new_users_day,
            'active_users_week': active_users_week,
            'total_tasks': total_tasks,
            'total_labs': total_labs,
            'total_courses': total_courses,
            'pending_answers': pending_answers,
            'moderation_queue': moderation_queue,
            'solved_tasks_count': solved_tasks_count,
            'solved_labs_count': solved_labs_count,
            'task_progress': task_progress,
            'lab_progress': lab_progress
        }

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))
        
    @login_manager.unauthorized_handler
    def unauthorized():
        flash('Необходимо войти в систему', 'warning')
        return redirect(url_for('auth.login', next=request.url))
        
    from auth import auth_bp
    from admin_routes import admin_bp
    from lab_routes import lab_bp
    from task_routes import task_bp
    from api_routes import api_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(lab_bp)
    app.register_blueprint(task_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(curator_bp)
        




    @app.route('/')
    @login_required
    def index():
        # ✅ ДОБАВЬ ЛОГИРОВАНИЕ ПОСЕЩЕНИЯ ГЛАВНОЙ СТРАНИЦЫ
        task_type = request.args.get('type', 'Практика')
        
        log_user_action(
            'visit_main_page',
            f'Посещение главной страницы с типом задач: {task_type}',
            additional_data={
                'task_type': task_type,
                'user_role': current_user.role
            }
        )
        from models import Task
        task_type = request.args.get('type', 'Практика')
        solved_task_ids = [p.task_id for p in current_user.tasks_progress.filter_by(is_approved=True).all()]

        # Получаем задачи доступные пользователю
        if current_user.is_admin:
            all_tasks = Task.query.filter_by(type=task_type).order_by(Task.id.asc()).all()
        elif current_user.role == 'curator':
            # Куратор видит задачи из своих курсов + задачи без привязки к курсу
            curated_course_ids = [c.id for c in current_user.curated_courses]
            if curated_course_ids:
                all_tasks = Task.query.filter(
                    Task.type == task_type,
                    (Task.course_id.in_(curated_course_ids)) | (Task.course_id == None)
                ).order_by(Task.id.asc()).all()
            else:
                all_tasks = Task.query.filter_by(type=task_type, course_id=None).order_by(Task.id.asc()).all()
        else:
            # Для студентов
            user_course_ids = [uc.course_id for uc in current_user.user_courses]
            if user_course_ids:
                all_tasks = Task.query.filter(
                    Task.type == task_type,
                    (Task.course_id.in_(user_course_ids)) | (Task.course_id == None)
                ).order_by(Task.id.asc()).all()
            else:
                all_tasks = Task.query.filter_by(type=task_type, course_id=None).order_by(Task.id.asc()).all()

        next_task = None
        for task in all_tasks:
            if task.id not in solved_task_ids:
                next_task = task
                break

        # Получаем доступные курсы для отображения
        user_courses = current_user.accessible_courses

        return render_template('index.html', task=next_task, task_type=task_type, user_courses=user_courses)
            




    @app.route('/dashboard')
    @login_required
    def dashboard():
        # ✅ ДОБАВЬ ЛОГИРОВАНИЕ ПОСЕЩЕНИЯ ДАШБОРДА
        log_user_action(
            'visit_dashboard',
            f'Посещение дашборда пользователем {current_user.username}',
            additional_data={
                'user_role': current_user.role,
                'is_admin': current_user.is_admin
            }
        )
        if current_user.is_admin:
            curator_contacts = CuratorContact.query.all()
            stats = get_admin_stats()
            users = User.query.all()
            tasks = Task.query.all()
            
            try:
                answers = UserTaskProgress.query.filter_by(is_checked=False).all()
            except:
                try:
                    answers = UserTaskAnswer.query.filter_by(status='pending').all()
                except:
                    answers = []
                    
            solved_counts = {}
            solved_lab_counts = {}
            for user in users:
                try:
                    solved_counts[user.id] = UserTaskProgress.query.filter_by(
                        user_id=user.id, is_approved=True
                    ).count()
                except:
                    try:
                        solved_counts[user.id] = UserTaskAnswer.query.filter_by(
                            user_id=user.id, status='approved'
                        ).count()
                    except:
                        solved_counts[user.id] = 0
                        
                try:
                    solved_lab_counts[user.id] = UserLabProgress.query.filter_by(
                        user_id=user.id, is_solved=True
                    ).count()
                except:
                    try:
                        solved_lab_counts[user.id] = LabProgress.query.filter_by(
                            user_id=user.id, is_solved=True
                        ).count()
                    except:
                        solved_lab_counts[user.id] = 0
                        
            return render_template('dashboard.html',
                                user=current_user,
                                stats=stats,
                                users=users,
                                tasks=tasks,
                                curator_contacts=curator_contacts,
                                solved_counts=solved_counts,
                                solved_lab_counts=solved_lab_counts,
                                answers=answers)
                                
        elif current_user.role == 'curator':
            # Статистика для куратора
            curator_courses = current_user.curated_courses
            course_ids = [c.id for c in curator_courses]
            
            if course_ids:
                # Студенты куратора - используем явное условие join
                total_students = db.session.query(User).join(
                    UserCourse, User.id == UserCourse.user_id
                ).filter(
                    UserCourse.course_id.in_(course_ids),
                    User.role == 'student'
                ).distinct().count()
                
                # Непроверенные ответы - используем явное условие join
                pending_answers = db.session.query(UserTaskProgress).join(
                    Task, UserTaskProgress.task_id == Task.id
                ).filter(
                    UserTaskProgress.is_checked == False,
                    Task.course_id.in_(course_ids)
                ).count()
                
                # Задачи и лабы куратора
                total_tasks = Task.query.filter(Task.course_id.in_(course_ids)).count()
                total_labs = Lab.query.filter(Lab.course_id.in_(course_ids)).count()
                
                curator_stats = {
                    'total_students': total_students,
                    'pending_answers': pending_answers,
                    'total_tasks': total_tasks,
                    'total_labs': total_labs
                }
            else:
                curator_stats = {
                    'total_students': 0,
                    'pending_answers': 0,
                    'total_tasks': 0,
                    'total_labs': 0
                }
            
            return render_template('dashboard.html',
                                user=current_user,
                                curator_stats=curator_stats)
        else:
            # Для студентов
            try:
                solved_count = UserTaskProgress.query.filter_by(
                    user_id=current_user.id, is_approved=True
                ).count()
            except:
                try:
                    solved_count = UserTaskAnswer.query.filter_by(
                        user_id=current_user.id, status='approved'
                    ).count()
                except:
                    solved_count = 0
                    
            try:
                solved_labs_count = UserLabProgress.query.filter_by(
                    user_id=current_user.id, is_solved=True
                ).count()
            except:
                try:
                    solved_labs_count = LabProgress.query.filter_by(
                        user_id=current_user.id, is_solved=True
                    ).count()
                except:
                    solved_labs_count = 0
                    
            total_tasks = Task.query.count()
            total_labs = Lab.query.count()
            
            return render_template('dashboard.html',
                                user=current_user,
                                solved_count=solved_count,
                                solved_labs_count=solved_labs_count,
                                total_tasks=total_tasks,
                                total_labs=total_labs)


    # В app.py добавляем новый роут
    @app.route('/contacts')
    @login_required
    def contacts():
        # ✅ ДОБАВЬ ЛОГИРОВАНИЕ ПОСЕЩЕНИЯ КОНТАКТОВ
        log_user_action(
            'visit_contacts',
            'Просмотр страницы контактов',
            additional_data={'user_role': current_user.role}
        )
        
        # Общий контакт техподдержки
        tech_support = {
            'name': 'Техническая поддержка',
            'telegram': '@darkschool_sup',
            'url': 'https://t.me/darkschool_sup',
            'description': 'Общие вопросы по платформе'
        }
        
        # Контакты кураторов для студентов
        curator_contacts = []
        if current_user.role == 'student':
            curators = current_user.curator_contacts
            for curator in curators:
                if curator.has_contact_info:
                    curator_courses = [c.title for c in curator.curated_courses 
                                    if c.id in [uc.course_id for uc in current_user.user_courses]]
                    curator_contacts.append({
                        'curator': curator,
                        'courses': curator_courses
                    })
        
        return render_template('contacts.html', 
                            tech_support=tech_support, 
                            curator_contacts=curator_contacts)

                                   
    @app.route('/course')
    def course():
        return redirect("https://dark.school/courses")
    

    
        
    @app.route('/curator')
    @login_required
    def curator():
        curator_contacts = CuratorContact.query.all()
        return render_template('curator.html', contacts=curator_contacts)
        
    @app.errorhandler(403)
    def forbidden(e):
        return render_template('403.html'), 403
        
    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        return render_template('csrf_error.html', reason=e.description), 400
        
    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('500.html'), 500
        
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404
        
    if app.config.get('MINIFY_HTML', False):
        from htmlmin.main import minify
        
        @app.after_request
        def response_minify(response):
            if response.content_type == 'text/html; charset=utf-8':
                try:
                    minified = minify(response.get_data(as_text=True),
                                      remove_comments=True,
                                      remove_empty_space=True,
                                      reduce_empty_attributes=True,
                                      reduce_boolean_attributes=True,
                                      remove_optional_attribute_quotes=False,
                                      keep_pre=True)
                    response.set_data(minified)
                except Exception as e:
                    app.logger.error(f'HTML минификация ошибка: {e}')
            return response
            


    @app.template_global()
    def datetime():
        import datetime as dt
        return dt.datetime

    @app.template_filter('today')
    def today_filter(s):
        from datetime import datetime
        return datetime.utcnow().strftime('%Y-%m-%d')



    return app


def startup_info():
    env = os.environ.get('FLASK_ENV', 'production')
    print(f"🚀 Запуск приложения - Режим: {env.upper()}")


if __name__ == '__main__':
    load_dotenv(dotenv_path, override=True)
    
    app = create_app()
    
    with app.app_context():
        db.create_all()

        from models import User
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(username='admin', is_admin=True)
            admin.set_password('fAd*LvCA%vHqV?kPl#vTLE4u99$2ZOox')
            db.session.add(admin)
            db.session.commit()
            print("✓ Админ создан автоматически")
        
    startup_info()

    env = os.environ.get('FLASK_ENV', 'production').lower().strip()
    
    if env in ['development', 'dev', 'debug']:
        app.run(debug=True)
    else:
        if app.config.get('USE_OBFUSCATED', False):
            print("Сборка обфусцированных ассетов...")
            result = subprocess.run([sys.executable, 'build_assets.py'])
            if result.returncode != 0:
                print("⚠️  Ошибка при сборке ассетов!")
        app.run(host='0.0.0.0', port=5000, debug=False)