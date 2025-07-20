import os
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, current_app
from flask_login import login_required, current_user
from extensions import db, csrf
from forms import TaskForm, LabForm, RegistrationForm
from models import User, Task, Lab, UserTaskProgress, LabProgress, CuratorContact
from utils import admin_required, get_lab_db

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/tasks')
@login_required
@admin_required
def admin_tasks():
    task_type = request.args.get('type', 'Теория')
    tasks = Task.query.filter_by(type=task_type).order_by(Task.id.asc()).all()
    return render_template('admin_tasks.html', tasks=tasks, task_type=task_type)

@admin_bp.route('/tasks/new', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_tasks_new():
    form = TaskForm()
    if form.validate_on_submit():
        new_task = Task(title=form.title.data, description=form.description.data, type=form.type.data)
        db.session.add(new_task)
        db.session.commit()
        flash("Задача успешно создана", "success")
        return redirect(url_for('admin.admin_tasks'))
    return render_template('admin_task_form.html', form=form, title='Создать новую задачу')

@admin_bp.route('/tasks/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_tasks_edit(id):
    task = Task.query.get_or_404(id)
    form = TaskForm(obj=task)
    if form.validate_on_submit():
        task.title = form.title.data
        task.description = form.description.data
        task.type = form.type.data
        db.session.commit()
        flash("Задача успешно обновлена", "success")
        return redirect(url_for('admin.admin_tasks'))
    return render_template('admin_task_form.html', form=form, title='Редактировать задачу')

@admin_bp.route('/tasks/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
@csrf.exempt
def admin_tasks_delete(id):
    task = Task.query.get_or_404(id)
    db.session.delete(task)
    db.session.commit()
    flash("Задача удалена", "success")
    return redirect(url_for('admin.admin_tasks'))

@admin_bp.route('/labs')
@login_required
@admin_required
def admin_labs():
    labs = Lab.query.all()
    return render_template('admin_labs.html', labs=labs)

@admin_bp.route('/labs/new', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_labs_new():
    form = LabForm()
    if form.validate_on_submit():
        full_endpoint = f'/lab/vulnerable/{form.endpoint_suffix.data}'
        full_flag = f'FLAG{{{form.flag_content.data}}}'
        lab = Lab(
            title=form.title.data,
            description=form.description.data,
            difficulty=form.difficulty.data,
            endpoint=full_endpoint,
            flag=full_flag,
            type=form.type.data
        )
        db.session.add(lab)
        db.session.commit()
        flash('Лабораторная работа создана', 'success')
        return redirect(url_for('admin.admin_labs'))
    return render_template('admin_lab_form.html', form=form, title='Создать лабу')

@admin_bp.route('/labs/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_labs_edit(id):
    lab = Lab.query.get_or_404(id)
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        difficulty = request.form.get('difficulty')
        
        if title and description and difficulty:
            lab.title = title
            lab.description = description
            lab.difficulty = difficulty
            db.session.commit()
            flash('Лабораторная работа обновлена', 'success')
            return redirect(url_for('admin.admin_labs'))
        else:
            flash('Заполните все поля', 'error')
    
    return render_template('admin_lab_form.html', lab=lab, title='Редактировать лабу')

@admin_bp.route('/labs/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def admin_labs_delete(id):
    try:
        lab = Lab.query.get_or_404(id)
        lab_title = lab.title
        
        LabProgress.query.filter_by(lab_id=lab.id).delete()
        
        db.session.delete(lab)
        db.session.commit()
        
        flash(f'Лабораторная работа "{lab_title}" успешно удалена', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при удалении лабораторной работы: {str(e)}', 'error')
        current_app.logger.error(f'Error deleting lab {id}: {str(e)}')
    
    return redirect(url_for('admin.admin_labs'))

@admin_bp.route('/answers')
@login_required
@admin_required
def admin_answers():
    selected_type = request.args.get('type', None)
    query = UserTaskProgress.query.filter_by(is_checked=False)
    if selected_type:
        query = query.join(Task).filter(Task.type == selected_type)
    answers = query.all()
    return render_template('admin_answers.html', answers=answers, selected_type=selected_type)

@admin_bp.route('/answers/<int:id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_answer(id):
    answer = UserTaskProgress.query.get_or_404(id)
    answer.is_checked = True
    answer.is_approved = True
    answer.checked_at = datetime.utcnow()
    db.session.commit()
    flash(f"Ответ пользователя {answer.user.username} по задаче '{answer.task.title}' подтверждён.", "success")
    return redirect(url_for('admin.admin_answers'))

@admin_bp.route('/answers/<int:id>/reject', methods=['POST'])
@login_required
@admin_required
def reject_answer(id):
    answer = UserTaskProgress.query.get_or_404(id)
    answer.is_checked = True
    answer.is_approved = False
    answer.checked_at = datetime.utcnow()
    db.session.commit()
    flash(f"Ответ пользователя {answer.user.username} по задаче '{answer.task.title}' отклонён.", "warning")
    return redirect(url_for('admin.admin_answers'))

@admin_bp.route('/users', methods=['POST'])
@login_required
@admin_required
def manage_users():
    user_id = request.form.get('user_id')
    action = request.form.get('action')
    try:
        if action == 'delete':
            user = User.query.get_or_404(user_id)
            if user.id == current_user.id:
                flash('Вы не можете удалить самого себя', 'danger')
            else:
                UserTaskProgress.query.filter_by(user_id=user.id).delete()
                LabProgress.query.filter_by(user_id=user.id).delete()
                db.session.delete(user)
                db.session.commit()
                flash(f'Пользователь {user.username} удалён', 'success')
        elif action == 'toggle_admin':
            user = User.query.get_or_404(user_id)
            user.is_admin = not user.is_admin
            db.session.commit()
            flash(f'Пользователь {user.username} {"назначен админом" if user.is_admin else "снят с должности админа"}',
                  'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Произошла ошибка: {e}', 'danger')
    return redirect(url_for('dashboard'))

@admin_bp.route('/curator_contacts')
@login_required
@admin_required
def curator_contacts():
    contacts = CuratorContact.query.all()
    return render_template('curator_contacts.html', contacts=contacts)

@admin_bp.route('/curator-contact/<int:contact_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_curator_contact(contact_id):
    contact = CuratorContact.query.get_or_404(contact_id)
    if request.method == 'POST':
        contact.name = request.form.get('name').strip() or None
        contact.telegram = request.form.get('telegram').strip() or None
        contact.email = request.form.get('email').strip() or None
        if not any([contact.name, contact.telegram, contact.email]):
            flash('Заполните хотя бы одно поле!', 'error')
            return render_template('curator_contact_form.html', contact=contact)
        try:
            db.session.commit()
            flash('Контакт куратора обновлён!', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при обновлении контакта: {str(e)}', 'error')
    return render_template('curator_contact_form.html', contact=contact)

@admin_bp.route('/curator-contact/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_curator_contact():
    if request.method == 'POST':
        name = request.form.get('name').strip() or None
        telegram = request.form.get('telegram').strip() or None
        email = request.form.get('email').strip() or None
        if not any([name, telegram, email]):
            flash('Заполните хотя бы одно поле!', 'error')
            return render_template('curator_contact_form.html', contact=None)
        contact = CuratorContact(
            name=name,
            telegram=telegram,
            email=email
        )
        try:
            db.session.add(contact)
            db.session.commit()
            flash('Контакт куратора создан!', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при создании контакта: {str(e)}', 'error')
    return render_template('curator_contact_form.html', contact=None)

@admin_bp.route('/database')
@login_required
@admin_required
def admin_database():
    try:
        stats = {
            'users': User.query.count(),
            'tasks': Task.query.count(),
            'labs': Lab.query.count(),
            'task_progress': UserTaskProgress.query.count(),
            'lab_progress': LabProgress.query.count(),
            'contacts': CuratorContact.query.count()
        }
        import os
        db_files = []
        for filename in ['instance/users.db', 'lab_vulnerable.db']:
            if os.path.exists(filename):
                size = os.path.getsize(filename)
                db_files.append({
                    'name': filename,
                    'size': f"{size / 1024:.2f} KB" if size < 1024 * 1024 else f"{size / (1024 * 1024):.2f} MB"
                })
        return render_template('admin_database.html', stats=stats, db_files=db_files)
    except Exception as e:
        flash(f'Ошибка получения статистики БД: {e}', 'error')
        return redirect(url_for('dashboard'))

@admin_bp.route('/init-labs-data')
@login_required
@admin_required
def init_labs_data():
    try:
        if Lab.query.count() > 0:
            flash('Лабораторные работы уже существуют!', 'info')
            return redirect(url_for('dashboard'))
        labs_data = [
            {
                'title': 'SQL Injection - Обход авторизации',
                'description': 'Практическое изучение SQL инъекций в формах входа',
                'difficulty': 'Легко',
                'type': 'SQL Injection',
                'endpoint': '/vulnerable/login',
                'flag': 'FLAG{sql_login_bypass_success}'
            },
            {
                'title': 'SQL Injection - Слепая инъекция',
                'description': 'Изучение boolean-based blind SQL инъекций',
                'difficulty': 'Средне',
                'type': 'SQL Injection',
                'endpoint': '/vulnerable/blind',
                'flag': 'FLAG{blind_sql_injection_master}'
            },
            {
                'title': 'SQL Injection - UNION SELECT',
                'description': 'Извлечение данных с помощью UNION SELECT',
                'difficulty': 'Сложный',
                'type': 'SQL Injection',
                'endpoint': '/vulnerable/union',
                'flag': 'FLAG{union_select_data_extraction}'
            }
        ]
        for lab_data in labs_data:
            lab = Lab(**lab_data)
            db.session.add(lab)
        db.session.commit()
        flash(f'Создано {len(labs_data)} лабораторных работ!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при создании лабораторных работ: {str(e)}', 'error')
    return redirect(url_for('dashboard'))

@admin_bp.route('/init-test-tasks')
@login_required
@admin_required
def init_test_tasks():
    try:
        if Task.query.count() > 0:
            flash('Задачи уже существуют. Очистите базу данных перед добавлением тестовых задач.', 'warning')
            return redirect(url_for('admin.admin_tasks'))
        theory_tasks = [
            {
                'title': 'Задача 1: Найти пользователя по имени (уязвимость SQL-инъекции)',
                'description': 'Есть таблица users с полями id, username, password. Напишите запрос, который возвращает информацию о пользователе с именем \'admin\'. Важно: попробуйте представить, как может выглядеть уязвимый запрос, если имя пользователя вставляется напрямую в SQL без экранирования. Например, запрос может быть: SELECT * FROM users WHERE username = \'admin\'; Попробуйте написать запрос, который вернёт данные пользователя \'admin\'.',
                'type': 'Теория'
            },
            {
                'title': 'Задача 2: Вход без пароля (SQL-инъекция)',
                'description': 'В приложении запрос для логина формируется: SELECT * FROM users WHERE username = \'введённое_имя\' AND password = \'введённый_пароль\'; Напишите запрос с SQL-инъекцией, позволяющей войти без пароля.',
                'type': 'Теория'
            },
            {
                'title': 'Задача 3: UNION-инъекция для вывода паролей',
                'description': 'В таблице products есть поля (id, name, price). Используйте UNION для получения данных из таблицы users (username, password).',
                'type': 'Теория'
            },
            {
                'title': 'Задача 4: Что такое Kali Linux?',
                'description': 'Опишите в двух словах, что такое Kali Linux.',
                'type': 'Теория'
            },
            {
                'title': 'Задача 5: Назначение Burp Suite',
                'description': 'Для чего используется Burp Suite?',
                'type': 'Теория'
            },
            {
                'title': 'Задача 6: Как защитить SQL-запросы от инъекций?',
                'description': 'Напишите один способ защиты SQL-запросов от инъекций.',
                'type': 'Теория'
            },
            {
                'title': 'Задача 7: Что такое CSRF атака?',
                'description': 'Кратко объясните, что такое CSRF атака.',
                'type': 'Теория'
            },
            {
                'title': 'Задача 8: Инструмент для сканирования уязвимостей в Kali Linux',
                'description': 'Назовите распространённый инструмент для сканирования уязвимостей в Kali Linux.',
                'type': 'Теория'
            },
            {
                'title': 'Задача 9: Как перехватить HTTP запрос в Burp Suite?',
                'description': 'Опишите один из способов перехвата HTTP запроса в Burp Suite.',
                'type': 'Теория'
            },
            {
                'title': 'Задача 10: SQL выражение для выбора всех записей',
                'description': 'Напишите SQL запрос, который выбирает все записи из таблицы products.',
                'type': 'Теория'
            },
            {
                'title': 'Задача 11: Какие базовые права у пользователя Linux в Kali?',
                'description': 'Перечислите базовые права файлов обычного пользователя в Kali Linux.',
                'type': 'Теория'
            },
            {
                'title': 'Задача 12: Как включить режим перехвата в Burp Suite?',
                'description': 'Где обычно в Burp Suite можно включить режим перехвата?',
                'type': 'Теория'
            },
            {
                'title': 'Задача 13: Значение оператора LIKE в SQL',
                'description': 'Что делает оператор LIKE в SQL?',
                'type': 'Теория'
            },
            {
                'title': 'Задача 14: Способ проверки пароля в Python',
                'description': 'Как проверить пароль пользователя безопасно в Python?',
                'type': 'Теория'
            },
            {
                'title': 'Задача 15: Что такое XSS атака?',
                'description': 'Кратко опишите XSS атаку.',
                'type': 'Теория'
            }
        ]
        for task_data in theory_tasks:
            task = Task(
                title=task_data['title'],
                description=task_data['description'],
                type=task_data['type'],
                created_at=datetime.utcnow()
            )
            db.session.add(task)
        db.session.commit()
        flash(f'Успешно добавлено {len(theory_tasks)} теоретических задач!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при создании тестовых задач: {e}', 'error')
    return redirect(url_for('admin.admin_tasks'))

@admin_bp.route('/init-vulnerable-db')
@login_required
@admin_required
def init_vulnerable_db():
    try:
        conn = get_lab_db()
        cursor = conn.cursor()
        cursor.execute(
            '''CREATE TABLE IF NOT EXISTS vulnerable_users (id INTEGER PRIMARY KEY, username TEXT, password TEXT, role TEXT DEFAULT 'user', secret TEXT)''')
        cursor.execute(
            '''CREATE TABLE IF NOT EXISTS vulnerable_products (id INTEGER PRIMARY KEY, name TEXT, description TEXT, price REAL, category TEXT)''')
        cursor.execute(
            '''CREATE TABLE IF NOT EXISTS flags (id INTEGER PRIMARY KEY, flag_name TEXT, flag_value TEXT, hint TEXT)''')
        cursor.execute("DELETE FROM vulnerable_users")
        cursor.execute("DELETE FROM vulnerable_products")
        cursor.execute("DELETE FROM flags")
        users_data = [(1, 'admin', 'admin123', 'administrator', 'FLAG{sql_auth_bypass_master}'),
                      (2, 'user', 'userpass', 'user', 'nothing_here'),
                      (3, 'test', 'test', 'user', 'test_data'),
                      (4, 'guest', 'guest', 'guest', 'FLAG{guest_access_granted}')]
        cursor.executemany("INSERT INTO vulnerable_users VALUES (?,?,?,?,?)", users_data)
        products_data = [(1, 'Laptop Dell', 'Gaming laptop with RTX', 1500.00, 'computers'),
                         (2, 'Wireless Mouse', 'Logitech wireless mouse', 25.00, 'accessories'),
                         (3, 'Mechanical Keyboard', 'RGB mechanical keyboard', 100.00, 'accessories'),
                         (4, 'Monitor 4K', '27inch 4K monitor', 400.00, 'monitors')]
        cursor.executemany("INSERT INTO vulnerable_products VALUES (?,?,?,?,?)", products_data)
        flags_data = [(1, 'union_master', 'FLAG{union_injection_success}', 'Look in flags table'),
                      (2, 'blind_expert', 'FLAG{blind_sql_injection_pro}', 'Extract char by char'),
                      (3, 'admin_secret', 'FLAG{administrative_access}', 'Admin panel access')]
        cursor.executemany("INSERT INTO flags VALUES (?,?,?,?)", flags_data)
        conn.commit()
        conn.close()
        flash('База данных для уязвимых лабораторий создана!', 'success')
    except Exception as e:
        flash(f'Ошибка создания уязвимой БД: {e}', 'error')
    return redirect(url_for('dashboard'))

@admin_bp.route('/database/clear-all', methods=['POST'])
@login_required
@admin_required
def clear_all_database():
    confirmation = request.form.get('confirmation')
    if confirmation != 'DELETE ALL DATA':
        flash('Неверное подтверждение. Введите точно: DELETE ALL DATA', 'error')
        return redirect(url_for('admin.admin_database'))
    try:
        UserTaskProgress.query.delete()
        LabProgress.query.delete()
        Task.query.delete()
        Lab.query.delete()
        CuratorContact.query.delete()
        User.query.filter(User.id != current_user.id).delete()
        db.session.commit()
        try:
            conn = get_lab_db()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM vulnerable_users")
            cursor.execute("DELETE FROM vulnerable_products")
            cursor.execute("DELETE FROM flags")
            conn.commit()
            conn.close()
        except:
            pass
        flash('База данных полностью очищена!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка очистки БД: {e}', 'error')
    return redirect(url_for('admin.admin_database'))

@admin_bp.route('/curator-contact/<int:contact_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_curator_contact(contact_id):
    contact = CuratorContact.query.get_or_404(contact_id)
    try:
        db.session.delete(contact)
        db.session.commit()
        flash('Контакт куратора удалён!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при удалении контакта: {str(e)}', 'error')
    return redirect(url_for('dashboard'))

@admin_bp.route('/database/clear-tasks', methods=['POST'])
@login_required
@admin_required
def clear_tasks():
    try:
        UserTaskProgress.query.delete()
        Task.query.delete()
        db.session.commit()
        flash('Все задачи и прогресс по задачам удалены', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка удаления задач: {e}', 'error')
    return redirect(url_for('admin.admin_database'))

@admin_bp.route('/database/clear-labs', methods=['POST'])
@login_required
@admin_required
def clear_labs():
    try:
        LabProgress.query.delete()
        Lab.query.delete()
        db.session.commit()
        flash('Все лабораторные работы и прогресс удалены', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка удаления лабораторий: {e}', 'error')
    return redirect(url_for('admin.admin_database'))

@admin_bp.route('/database/clear-users', methods=['POST'])
@login_required
@admin_required
def clear_users():
    try:
        UserTaskProgress.query.filter(UserTaskProgress.user_id != current_user.id).delete()
        LabProgress.query.filter(LabProgress.user_id != current_user.id).delete()
        User.query.filter(User.id != current_user.id).delete()
        db.session.commit()
        flash('Все пользователи (кроме вас) удалены', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка удаления пользователей: {e}', 'error')
    return redirect(url_for('admin.admin_database'))

@admin_bp.route('/database/clear-progress', methods=['POST'])
@login_required
@admin_required
def clear_progress():
    try:
        UserTaskProgress.query.delete()
        LabProgress.query.delete()
        db.session.commit()
        flash('Весь прогресс пользователей удален', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка удаления прогресса: {e}', 'error')
    return redirect(url_for('admin.admin_database'))

@admin_bp.route('/database/recreate-vulnerable', methods=['POST'])
@login_required
@admin_required
def recreate_vulnerable_db():
    try:
        import os
        if os.path.exists('lab_vulnerable.db'):
            os.remove('lab_vulnerable.db')
        conn = get_lab_db()
        cursor = conn.cursor()
        cursor.execute(
            '''CREATE TABLE vulnerable_users (id INTEGER PRIMARY KEY, username TEXT, password TEXT, role TEXT DEFAULT 'user', secret TEXT)''')
        cursor.execute(
            '''CREATE TABLE vulnerable_products (id INTEGER PRIMARY KEY, name TEXT, description TEXT, price REAL, category TEXT)''')
        cursor.execute('''CREATE TABLE flags (id INTEGER PRIMARY KEY, flag_name TEXT, flag_value TEXT, hint TEXT)''')
        users_data = [(1, 'admin', 'admin123', 'administrator', 'FLAG{sql_auth_bypass_master}'),
                      (2, 'user', 'userpass', 'user', 'nothing_here'),
                      (3, 'test', 'test', 'user', 'test_data'),
                      (4, 'guest', 'guest', 'guest', 'FLAG{guest_access_granted}')]
        cursor.executemany("INSERT INTO vulnerable_users VALUES (?,?,?,?,?)", users_data)
        products_data = [(1, 'Laptop Dell', 'Gaming laptop with RTX', 1500.00, 'computers'),
                         (2, 'Wireless Mouse', 'Logitech wireless mouse', 25.00, 'accessories'),
                         (3, 'Mechanical Keyboard', 'RGB mechanical keyboard', 100.00, 'accessories'),
                         (4, 'Monitor 4K', '27inch 4K monitor', 400.00, 'monitors')]
        cursor.executemany("INSERT INTO vulnerable_products VALUES (?,?,?,?,?)", products_data)
        flags_data = [(1, 'union_master', 'FLAG{union_injection_success}', 'Look in flags table'),
                      (2, 'blind_expert', 'FLAG{blind_sql_injection_pro}', 'Extract char by char'),
                      (3, 'admin_secret', 'FLAG{administrative_access}', 'Admin panel access')]
        cursor.executemany("INSERT INTO flags VALUES (?,?,?,?)", flags_data)
        conn.commit()
        conn.close()
        flash('Уязвимая база данных пересоздана', 'success')
    except Exception as e:
        flash(f'Ошибка пересоздания уязвимой БД: {e}', 'error')
    return redirect(url_for('admin.admin_database'))

@admin_bp.route('/database/backup', methods=['POST'])
@login_required
@admin_required
def backup_database():
    try:
        import shutil
        import os
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = f'backups/backup_{timestamp}'
        os.makedirs(backup_dir, exist_ok=True)
        if os.path.exists('instance/users.db'):
            shutil.copy2('instance/users.db', f'{backup_dir}/users.db')
        if os.path.exists('lab_vulnerable.db'):
            shutil.copy2('lab_vulnerable.db', f'{backup_dir}/lab_vulnerable.db')
        flash(f'Резервная копия создана: {backup_dir}', 'success')
    except Exception as e:
        flash(f'Ошибка создания резервной копии: {e}', 'error')
    return redirect(url_for('admin.admin_database'))

@admin_bp.route('/users/new', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_users_new():
    form = RegistrationForm()
    if form.validate_on_submit():
        if User.query.filter_by(username=form.username.data).first():
            flash("Логин уже занят.", "danger")
            return render_template('admin_user_form.html', form=form)
        
        new_user = User(username=form.username.data)
        new_user.set_password(form.password.data)
        db.session.add(new_user)
        db.session.commit()
        flash(f"Пользователь {new_user.username} создан", "success")
        return redirect(url_for('dashboard'))
    
    return render_template('admin_user_form.html', form=form)