import os
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, render_template, redirect, url_for, flash, request, abort, current_app
from flask_login import login_required, current_user
from extensions import db, csrf
from forms import TaskForm, LabForm, RegistrationForm, CourseForm, UserCourseForm, CourseTaskForm, CourseLabForm
from models import User, Task, Lab, UserTaskProgress, LabProgress, CuratorContact, Course, UserCourse, CourseModeration
from utils import admin_required, get_lab_db
from logging_utils import log_admin_action, log_user_action





admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/courses')
@login_required
@admin_required
def admin_courses():
    courses = Course.query.all()
    return render_template('admin_courses.html', courses=courses)






@admin_bp.route('/courses/new', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_courses_new():
    form = CourseForm()
    curators = User.query.filter_by(role='curator').all()
    form.curator_id.choices = [(0, 'Без куратора')] + [(c.id, c.username) for c in curators]
    
    if form.validate_on_submit():
        curator_id = form.curator_id.data if form.curator_id.data != 0 else None
        course = Course(
            title=form.title.data,
            description=form.description.data,
            curator_id=curator_id,
            is_active=form.is_active.data,
            creator_id=current_user.id
        )
        db.session.add(course)
        db.session.commit()
        
        # ✅ ДОБАВЬ ЭТО ЛОГИРОВАНИЕ
        log_admin_action(
            'create_course',
            f'Создан курс "{course.title}"',
            target_type='course',
            target_id=course.id,
            additional_data={
                'curator_id': curator_id,
                'is_active': course.is_active,
                'description_length': len(course.description or '')
            }
        )
        
        flash(f'Курс "{course.title}" создан успешно!', 'success')
        return redirect(url_for('admin.admin_courses'))
    
    return render_template('admin_course_form.html', form=form, title='Создать новый курс')

# В функцию admin_courses_edit добавь после db.session.commit():
@admin_bp.route('/courses/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_courses_edit(id):
    course = Course.query.get_or_404(id)
    old_title = course.title
    form = CourseForm(obj=course)
    
    curators = User.query.filter_by(role='curator').all()
    form.curator_id.choices = [(0, 'Без куратора')] + [(c.id, c.username) for c in curators]
    
    if form.validate_on_submit():
        course.title = form.title.data
        course.description = form.description.data
        course.curator_id = form.curator_id.data if form.curator_id.data != 0 else None
        course.is_active = form.is_active.data
        course.updated_at = datetime.utcnow()
        db.session.commit()
        
        # ✅ ДОБАВЬ ЭТО ЛОГИРОВАНИЕ
        log_admin_action(
            'edit_course',
            f'Изменен курс "{course.title}"',
            target_type='course',
            target_id=course.id,
            additional_data={
                'old_title': old_title,
                'new_title': course.title,
                'curator_id': course.curator_id,
                'is_active': course.is_active
            }
        )
        
        flash(f'Курс "{course.title}" обновлен!', 'success')
        return redirect(url_for('admin.admin_courses'))
    
    return render_template('admin_course_form.html', form=form, course=course, title='Редактировать курс')

# В функцию admin_courses_delete добавь после db.session.commit():
@admin_bp.route('/courses/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def admin_courses_delete(id):
    course = Course.query.get_or_404(id)
    course_title = course.title
    course_students = UserCourse.query.filter_by(course_id=id).count()
    course_tasks = Task.query.filter_by(course_id=id).count()
    course_labs = Lab.query.filter_by(course_id=id).count()
    
    try:
        UserCourse.query.filter_by(course_id=id).delete()
        Task.query.filter_by(course_id=id).update({'course_id': None})
        Lab.query.filter_by(course_id=id).update({'course_id': None})
        CourseModeration.query.filter_by(course_id=id).delete()
        db.session.delete(course)
        db.session.commit()
        
        # ✅ ДОБАВЬ ЭТО ЛОГИРОВАНИЕ
        log_admin_action(
            'delete_course',
            f'Удален курс "{course_title}"',
            target_type='course',
            target_id=id,
            additional_data={
                'students_count': course_students,
                'tasks_count': course_tasks,
                'labs_count': course_labs
            }
        )
        
        flash(f'Курс "{course_title}" удален успешно!', 'success')
    except Exception as e:
        db.session.rollback()
        # ✅ ДОБАВЬ ЭТО ЛОГИРОВАНИЕ ОШИБКИ
        log_admin_action(
            'delete_course_failed',
            f'Ошибка при удалении курса "{course_title}": {str(e)}',
            target_type='course',
            target_id=id
        )
        flash(f'Ошибка при удалении курса: {str(e)}', 'error')
    
    return redirect(url_for('admin.admin_courses'))









@admin_bp.route('/user-courses')
@login_required
@admin_required
def admin_user_courses():
    users_with_courses = User.query.all()
    courses = Course.query.filter_by(is_active=True).all()
    return render_template('admin_user_courses.html', users=users_with_courses, courses=courses)

@admin_bp.route('/user-courses/grant', methods=['POST'])
@login_required
@admin_required
def grant_user_course_access():
    user_id = request.form.get('user_id')
    course_id = request.form.get('course_id')
    
    if not user_id or not course_id:
        flash('Выберите пользователя и курс', 'error')
        return redirect(url_for('admin.admin_user_courses'))
    
    existing = UserCourse.query.filter_by(user_id=user_id, course_id=course_id).first()
    if existing:
        flash('Пользователь уже имеет доступ к этому курсу', 'warning')
        return redirect(url_for('admin.admin_user_courses'))
    
    user = User.query.get(user_id)
    course = Course.query.get(course_id)
    
    user_course = UserCourse(
        user_id=user_id,
        course_id=course_id,
        granted_by=current_user.id
    )
    
    db.session.add(user_course)
    db.session.commit()
    
    flash(f'Пользователю {user.username} предоставлен доступ к курсу "{course.title}"', 'success')
    return redirect(url_for('admin.admin_user_courses'))

@admin_bp.route('/user-courses/revoke', methods=['POST'])
@login_required
@admin_required
def revoke_user_course_access():
    user_id = request.form.get('user_id')
    course_id = request.form.get('course_id')
    
    user_course = UserCourse.query.filter_by(user_id=user_id, course_id=course_id).first()
    if user_course:
        user = User.query.get(user_id)
        course = Course.query.get(course_id)
        
        db.session.delete(user_course)
        db.session.commit()
        
        flash(f'Доступ пользователя {user.username} к курсу "{course.title}" отозван', 'success')
    else:
        flash('Доступ к курсу не найден', 'error')
    
    return redirect(url_for('admin.admin_user_courses'))

@admin_bp.route('/moderation')
@login_required
@admin_required
def admin_moderation():
    pending_requests = CourseModeration.query.filter_by(status='pending').order_by(
        CourseModeration.created_at.desc()
    ).all()
    return render_template('admin_moderation.html', requests=pending_requests)

@admin_bp.route('/moderation/<int:id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_moderation(id):
    moderation = CourseModeration.query.get_or_404(id)
    admin_comment = request.form.get('admin_comment', '')
    
    try:
        if moderation.change_type == 'add_task':
            task_data = moderation.change_data
            task = Task(
                title=task_data['title'],
                description=task_data['description'],
                type=task_data['type'],
                difficulty=task_data.get('difficulty', 'Легко'),
                course_id=moderation.course_id
            )
            db.session.add(task)
            
        elif moderation.change_type == 'edit_task':
            task_id = moderation.change_data['task_id']
            task = Task.query.get(task_id)
            if task:
                task.title = moderation.change_data['title']
                task.description = moderation.change_data['description']
                task.type = moderation.change_data['type']
                task.difficulty = moderation.change_data.get('difficulty', task.difficulty)
                
        elif moderation.change_type == 'add_lab':
            lab_data = moderation.change_data
            lab = Lab(
                title=lab_data['title'],
                description=lab_data['description'],
                difficulty=lab_data['difficulty'],
                endpoint=lab_data['endpoint'],
                flag=lab_data['flag'],
                type=lab_data.get('type', 'SQL Injection'),
                course_id=moderation.course_id
            )
            db.session.add(lab)
            
        elif moderation.change_type == 'edit_lab':
            lab_id = moderation.change_data['lab_id']
            lab = Lab.query.get(lab_id)
            if lab:
                lab.title = moderation.change_data['title']
                lab.description = moderation.change_data['description']
                lab.difficulty = moderation.change_data['difficulty']
        
        moderation.status = 'approved'
        moderation.admin_comment = admin_comment
        moderation.reviewed_by = current_user.id
        moderation.reviewed_at = datetime.utcnow()
        
        db.session.commit()
        flash(f'Запрос от {moderation.curator.username} одобрен', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при одобрении запроса: {str(e)}', 'error')
    
    return redirect(url_for('admin.admin_moderation'))

@admin_bp.route('/moderation/<int:id>/reject', methods=['POST'])
@login_required
@admin_required
def reject_moderation(id):
    moderation = CourseModeration.query.get_or_404(id)
    admin_comment = request.form.get('admin_comment', 'Запрос отклонен')
    
    moderation.status = 'rejected'
    moderation.admin_comment = admin_comment
    moderation.reviewed_by = current_user.id
    moderation.reviewed_at = datetime.utcnow()
    
    db.session.commit()
    flash(f'Запрос от {moderation.curator.username} отклонен', 'warning')
    
    return redirect(url_for('admin.admin_moderation'))

@admin_bp.route('/tasks')
@login_required
@admin_required
def admin_tasks():
    task_type = request.args.get('type', 'Теория')
    course_id = request.args.get('course_id', None)
    
    query = Task.query.filter_by(type=task_type)
    if course_id:
        query = query.filter_by(course_id=course_id)
    
    tasks = query.order_by(Task.id.asc()).all()
    courses = Course.query.filter_by(is_active=True).all()
    
    return render_template('admin_tasks.html', tasks=tasks, task_type=task_type, 
                         courses=courses, selected_course_id=course_id)

@admin_bp.route('/tasks/new', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_tasks_new():
    form = CourseTaskForm()
    courses = Course.query.filter_by(is_active=True).all()
    form.course_id.choices = [(0, 'Общий доступ')] + [(c.id, c.title) for c in courses]
    
    if form.validate_on_submit():
        course_id = form.course_id.data if form.course_id.data != 0 else None
        new_task = Task(
            title=form.title.data,
            description=form.description.data,
            type=form.type.data,
            course_id=course_id
        )
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
    course_id = request.args.get('course_id', None)
    
    query = Lab.query
    if course_id:
        query = query.filter_by(course_id=course_id)
    
    labs = query.all()
    courses = Course.query.filter_by(is_active=True).all()
    
    return render_template('admin_labs.html', labs=labs, courses=courses, 
                         selected_course_id=course_id)

@admin_bp.route('/labs/new', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_labs_new():
    form = CourseLabForm()
    courses = Course.query.filter_by(is_active=True).all()
    form.course_id.choices = [(0, 'Общий доступ')] + [(c.id, c.title) for c in courses]
    
    if form.validate_on_submit():
        course_id = form.course_id.data if form.course_id.data != 0 else None
        full_endpoint = f'/vulnerable/{form.endpoint.data}' if not form.endpoint.data.startswith('/') else form.endpoint.data
        full_flag = f'FLAG{{{form.flag.data}}}' if not form.flag.data.startswith('FLAG{') else form.flag.data
        
        lab = Lab(
            title=form.title.data,
            description=form.description.data,
            difficulty=form.difficulty.data,
            endpoint=full_endpoint,
            flag=full_flag,
            type=form.type.data if hasattr(form, 'type') else 'SQL Injection',
            course_id=course_id
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








# Добавь логирование в функции проверки ответов:
@admin_bp.route('/answers/<int:id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_answer(id):
    answer = UserTaskProgress.query.get_or_404(id)
    answer.is_checked = True
    answer.is_approved = True
    answer.checked_at = datetime.utcnow()
    db.session.commit()
    
    # ✅ ДОБАВЬ ЭТО ЛОГИРОВАНИЕ
    log_admin_action(
        'approve_answer',
        f'Одобрен ответ пользователя {answer.user.username} по задаче "{answer.task.title}"',
        target_type='task',
        target_id=answer.task_id,
        additional_data={
            'student_id': answer.user_id,
            'student_username': answer.user.username,
            'answer_text': answer.user_answer[:100] if answer.user_answer else None  # Первые 100 символов
        }
    )
    
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
    
    # ✅ ДОБАВЬ ЭТО ЛОГИРОВАНИЕ
    log_admin_action(
        'reject_answer',
        f'Отклонен ответ пользователя {answer.user.username} по задаче "{answer.task.title}"',
        target_type='task',
        target_id=answer.task_id,
        additional_data={
            'student_id': answer.user_id,
            'student_username': answer.user.username,
            'answer_text': answer.user_answer[:100] if answer.user_answer else None
        }
    )
    
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
                username = user.username
                user_role = user.role
                
                UserTaskProgress.query.filter_by(user_id=user.id).delete()
                LabProgress.query.filter_by(user_id=user.id).delete()
                UserCourse.query.filter_by(user_id=user.id).delete()
                db.session.delete(user)
                db.session.commit()
                
                # ✅ ДОБАВЬ ЭТО ЛОГИРОВАНИЕ
                log_admin_action(
                    'delete_user',
                    f'Удален пользователь {username}',
                    target_type='user',
                    target_id=user_id,
                    additional_data={'deleted_user_role': user_role}
                )
                
                flash(f'Пользователь {username} удалён', 'success')
                
        elif action == 'toggle_admin':
            user = User.query.get_or_404(user_id)
            old_status = user.is_admin
            user.is_admin = not user.is_admin
            if user.is_admin:
                user.role = 'admin'
            else:
                user.role = 'student'
            db.session.commit()
            
            # ✅ ДОБАВЬ ЭТО ЛОГИРОВАНИЕ
            log_admin_action(
                'toggle_admin',
                f'Изменены права админа для {user.username}: {old_status} → {user.is_admin}',
                target_type='user',
                target_id=user_id,
                additional_data={
                    'old_admin_status': old_status,
                    'new_admin_status': user.is_admin,
                    'new_role': user.role
                }
            )
            
            flash(f'Пользователь {user.username} {"назначен админом" if user.is_admin else "снят с должности админа"}', 'success')
            
        elif action == 'make_curator':
            user = User.query.get_or_404(user_id)
            old_role = user.role
            user.role = 'curator'
            user.is_admin = False
            db.session.commit()
            
            # ✅ ДОБАВЬ ЭТО ЛОГИРОВАНИЕ
            log_admin_action(
                'make_curator',
                f'Назначен куратором: {user.username}',
                target_type='user',
                target_id=user_id,
                additional_data={'old_role': old_role, 'new_role': 'curator'}
            )
            
            flash(f'Пользователь {user.username} назначен куратором', 'success')
            
        elif action == 'make_student':
            user = User.query.get_or_404(user_id)
            old_role = user.role
            user.role = 'student'
            user.is_admin = False
            db.session.commit()
            
            # ✅ ДОБАВЬ ЭТО ЛОГИРОВАНИЕ
            log_admin_action(
                'make_student',
                f'Назначен студентом: {user.username}',
                target_type='user',
                target_id=user_id,
                additional_data={'old_role': old_role, 'new_role': 'student'}
            )
            
            flash(f'Пользователь {user.username} назначен студентом', 'success')
            
    except Exception as e:
        db.session.rollback()
        # ✅ ДОБАВЬ ЭТО ЛОГИРОВАНИЕ ОШИБКИ
        log_admin_action(
            'manage_users_error',
            f'Ошибка при управлении пользователем: {str(e)}',
            additional_data={'action': action, 'user_id': user_id, 'error': str(e)}
        )
        flash(f'Произошла ошибка: {e}', 'danger')
    
    return redirect(url_for('dashboard'))

# В функцию admin_users_new добавь после db.session.commit():
@admin_bp.route('/users/new', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_users_new():
    form = RegistrationForm()
    courses = Course.query.filter_by(is_active=True).all()
    form.course_ids.choices = [('', 'Без курса (можно назначить позже)')] + [(str(c.id), c.title) for c in courses]
    
    if form.validate_on_submit():
        if User.query.filter_by(username=form.username.data).first():
            flash("Логин уже занят.", "danger")
            return render_template('admin_user_form.html', form=form)
        
        new_user = User(
            username=form.username.data, 
            role=form.role.data,
            curator_name=form.curator_name.data if form.role.data == 'curator' else None,
            curator_telegram=form.curator_telegram.data if form.role.data == 'curator' else None,
            curator_email=form.curator_email.data if form.role.data == 'curator' else None
        )
        
        if form.role.data == 'admin':
            new_user.is_admin = True
            
        new_user.set_password(form.password.data)
        db.session.add(new_user)
        db.session.flush()
        
        course_id = None
        if form.course_ids.data and form.course_ids.data != '' and form.course_ids.data.isdigit():
            course_id = int(form.course_ids.data)
            user_course = UserCourse(
                user_id=new_user.id,
                course_id=course_id,
                granted_by=current_user.id
            )
            db.session.add(user_course)
        
        db.session.commit()
        
        # ✅ ДОБАВЬ ЭТО ЛОГИРОВАНИЕ
        log_admin_action(
            'create_user',
            f'Создан пользователь {new_user.username} с ролью {new_user.role}',
            target_type='user',
            target_id=new_user.id,
            additional_data={
                'created_role': new_user.role,
                'is_admin': new_user.is_admin,
                'assigned_course_id': course_id,
                'has_curator_contacts': bool(new_user.curator_name or new_user.curator_telegram or new_user.curator_email)
            }
        )
        
        role_text = {
            'student': 'студент',
            'curator': 'куратор',
            'admin': 'администратор'
        }.get(form.role.data, 'пользователь')
        
        if course_id:
            course = Course.query.get(course_id)
            flash(f'{role_text.capitalize()} {new_user.username} создан и привязан к курсу "{course.title}"', "success")
        else:
            flash(f'{role_text.capitalize()} {new_user.username} создан без привязки к курсу', "success")
        
        return redirect(url_for('dashboard'))
    
    return render_template('admin_user_form.html', form=form)

















@admin_bp.route('/courses/<int:course_id>/assign-curator', methods=['POST'])
@login_required
@admin_required
def assign_curator_to_course(course_id):
    course = Course.query.get_or_404(course_id)
    curator_id = request.form.get('curator_id')
    
    if not curator_id:
        flash('Выберите куратора', 'error')
        return redirect(url_for('admin.admin_courses'))
    
    curator = User.query.filter_by(id=curator_id, role='curator').first()
    if not curator:
        flash('Выбранный пользователь не является куратором', 'error')
        return redirect(url_for('admin.admin_courses'))
    
    # Проверяем, что у куратора еще нет этого курса
    if course.curator_id == curator.id:
        flash(f'Куратор {curator.username} уже назначен на курс "{course.title}"', 'warning')
        return redirect(url_for('admin.admin_courses'))
    
    course.curator_id = curator.id
    db.session.commit()
    
    flash(f'Куратор {curator.username} назначен на курс "{course.title}"', 'success')
    return redirect(url_for('admin.admin_courses'))

@admin_bp.route('/courses/<int:course_id>/remove-curator', methods=['POST'])
@login_required
@admin_required
def remove_curator_from_course(course_id):
    course = Course.query.get_or_404(course_id)
    
    if not course.curator_id:
        flash('У курса нет назначенного куратора', 'warning')
        return redirect(url_for('admin.admin_courses'))
    
    curator_name = course.curator.username
    course.curator_id = None
    db.session.commit()
    
    flash(f'Куратор {curator_name} снят с курса "{course.title}"', 'success')
    return redirect(url_for('admin.admin_courses'))



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
            'courses': Course.query.count(),
            'user_courses': UserCourse.query.count(),
            'task_progress': UserTaskProgress.query.count(),
            'lab_progress': LabProgress.query.count(),
            'contacts': CuratorContact.query.count(),
            'moderation_queue': CourseModeration.query.filter_by(status='pending').count()
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
        
        hacking_course = Course.query.filter_by(title='Основы хакинга и информационной безопасности').first()
        if not hacking_course:
            maine_coon = User.query.filter_by(username='MaineCoon').first()
            if not maine_coon:
                maine_coon = User(username='MaineCoon', role='curator')
                maine_coon.set_password('darkschoolmainecoon')
                db.session.add(maine_coon)
                db.session.flush()
            
            hacking_course = Course(
                title='Основы хакинга и информационной безопасности',
                description='Комплексный курс по основам информационной безопасности и этичного хакинга',
                curator_id=maine_coon.id,
                creator_id=current_user.id,
                is_active=True
            )
            db.session.add(hacking_course)
            db.session.flush()
        
        labs_data = [
            {
                'title': 'SQL Injection - Обход авторизации',
                'description': 'Практическое изучение SQL инъекций в формах входа',
                'difficulty': 'Легко',
                'type': 'SQL Injection',
                'endpoint': '/vulnerable/login',
                'flag': 'FLAG{sql_login_bypass_success}',
                'course_id': hacking_course.id
            },
            {
                'title': 'SQL Injection - Слепая инъекция',
                'description': 'Изучение boolean-based blind SQL инъекций',
                'difficulty': 'Средне',
                'type': 'SQL Injection',
                'endpoint': '/vulnerable/blind',
                'flag': 'FLAG{blind_sql_injection_master}',
                'course_id': hacking_course.id
            },
            {
                'title': 'SQL Injection - UNION SELECT',
                'description': 'Извлечение данных с помощью UNION SELECT',
                'difficulty': 'Сложно',
                'type': 'SQL Injection',
                'endpoint': '/vulnerable/union',
                'flag': 'FLAG{union_select_data_extraction}',
                'course_id': hacking_course.id
            }
        ]
        for lab_data in labs_data:
            lab = Lab(**lab_data)
            db.session.add(lab)
        db.session.commit()
        flash(f'Создано {len(labs_data)} лабораторных работ для курса "{hacking_course.title}"!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при создании лабораторных работ: {str(e)}', 'error')
    return redirect(url_for('dashboard'))

@admin_bp.route('/init-test-tasks')
@login_required
@admin_required
def init_test_tasks():
    try:
        hacking_course = Course.query.filter_by(title='Основы хакинга и информационной безопасности').first()
        if not hacking_course:
            maine_coon = User.query.filter_by(username='MaineCoon').first()
            if not maine_coon:
                maine_coon = User(username='MaineCoon', role='curator')
                maine_coon.set_password('darkschoolmainecoon')
                db.session.add(maine_coon)
                db.session.flush()
            
            hacking_course = Course(
                title='Основы хакинга и информационной безопасности',
                description='Комплексный курс по основам информационной безопасности и этичного хакинга',
                curator_id=maine_coon.id,
                creator_id=current_user.id,
                is_active=True
            )
            db.session.add(hacking_course)
            db.session.flush()
        
        theory_tasks = [
            {
                'title': 'Задача 1: Найти пользователя по имени (уязвимость SQL-инъекции)',
                'description': 'Есть таблица users с полями id, username, password. Напишите запрос, который возвращает информацию о пользователе с именем \'admin\'. Важно: попробуйте представить, как может выглядеть уязвимый запрос, если имя пользователя вставляется напрямую в SQL без экранирования. Например, запрос может быть: SELECT * FROM users WHERE username = \'admin\'; Попробуйте написать запрос, который вернёт данные пользователя \'admin\'.',
                'type': 'Теория',
                'course_id': hacking_course.id
            },
            {
                'title': 'Задача 2: Вход без пароля (SQL-инъекция)',
                'description': 'В приложении запрос для логина формируется: SELECT * FROM users WHERE username = \'введённое_имя\' AND password = \'введённый_пароль\'; Напишите запрос с SQL-инъекцией, позволяющей войти без пароля.',
                'type': 'Теория',
                'course_id': hacking_course.id
            },
            {
                'title': 'Задача 3: UNION-инъекция для вывода паролей',
                'description': 'В таблице products есть поля (id, name, price). Используйте UNION для получения данных из таблицы users (username, password).',
                'type': 'Теория',
                'course_id': hacking_course.id
            },
            {
                'title': 'Задача 4: Что такое Kali Linux?',
                'description': 'Опишите в двух словах, что такое Kali Linux.',
                'type': 'Теория',
                'course_id': hacking_course.id
            },
            {
                'title': 'Задача 5: Назначение Burp Suite',
                'description': 'Для чего используется Burp Suite?',
                'type': 'Теория',
                'course_id': hacking_course.id
            },
            {
                'title': 'Задача 6: Как защитить SQL-запросы от инъекций?',
                'description': 'Напишите один способ защиты SQL-запросов от инъекций.',
                'type': 'Теория',
                'course_id': hacking_course.id
            },
            {
                'title': 'Задача 7: Что такое CSRF атака?',
                'description': 'Кратко объясните, что такое CSRF атака.',
                'type': 'Теория',
                'course_id': hacking_course.id
            },
            {
                'title': 'Задача 8: Инструмент для сканирования уязвимостей в Kali Linux',
                'description': 'Назовите распространённый инструмент для сканирования уязвимостей в Kali Linux.',
                'type': 'Теория',
                'course_id': hacking_course.id
            },
            {
                'title': 'Задача 9: Как перехватить HTTP запрос в Burp Suite?',
                'description': 'Опишите один из способов перехвата HTTP запроса в Burp Suite.',
                'type': 'Теория',
                'course_id': hacking_course.id
            },
            {
                'title': 'Задача 10: SQL выражение для выбора всех записей',
                'description': 'Напишите SQL запрос, который выбирает все записи из таблицы products.',
                'type': 'Теория',
                'course_id': hacking_course.id
            },
            {
                'title': 'Задача 11: Какие базовые права у пользователя Linux в Kali?',
                'description': 'Перечислите базовые права файлов обычного пользователя в Kali Linux.',
                'type': 'Теория',
                'course_id': hacking_course.id
            },
            {
                'title': 'Задача 12: Как включить режим перехвата в Burp Suite?',
                'description': 'Где обычно в Burp Suite можно включить режим перехвата?',
                'type': 'Теория',
                'course_id': hacking_course.id
            },
            {
                'title': 'Задача 13: Значение оператора LIKE в SQL',
                'description': 'Что делает оператор LIKE в SQL?',
                'type': 'Теория',
                'course_id': hacking_course.id
            },
            {
                'title': 'Задача 14: Способ проверки пароля в Python',
                'description': 'Как проверить пароль пользователя безопасно в Python?',
                'type': 'Теория',
                'course_id': hacking_course.id
            },
            {
                'title': 'Задача 15: Что такое XSS атака?',
                'description': 'Кратко опишите XSS атаку.',
                'type': 'Теория',
                'course_id': hacking_course.id
            }
        ]
        for task_data in theory_tasks:
            task = Task(
                title=task_data['title'],
                description=task_data['description'],
                type=task_data['type'],
                course_id=task_data['course_id'],
                created_at=datetime.utcnow()
            )
            db.session.add(task)
        db.session.commit()
        flash(f'Успешно добавлено {len(theory_tasks)} теоретических задач для курса "{hacking_course.title}"!', 'success')
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
        UserCourse.query.delete()
        CourseModeration.query.delete()
        Task.query.delete()
        Lab.query.delete()
        Course.query.delete()
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
        UserCourse.query.filter(UserCourse.user_id != current_user.id).delete()
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










from logging_utils import log_admin_action
from models import UserActionLog
from sqlalchemy import desc



# Добавь эти роуты в admin_routes.py
from models import UserActionLog
from sqlalchemy import desc

@admin_bp.route('/logs')
@login_required
@admin_required
def view_logs():
    # ✅ ЛОГИРУЕМ ПРОСМОТР ЛОГОВ АДМИНОМ
    log_admin_action('view_logs', 'Просмотр системных логов')
    
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    action_type = request.args.get('action_type', '')
    user_id = request.args.get('user_id', '')
    target_type = request.args.get('target_type', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    query = UserActionLog.query
    
    if action_type:
        query = query.filter(UserActionLog.action_type.like(f'%{action_type}%'))
    
    if user_id:
        query = query.filter(UserActionLog.user_id == user_id)
    
    if target_type:
        query = query.filter(UserActionLog.target_type == target_type)
    
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(UserActionLog.created_at >= date_from_obj)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
            query = query.filter(UserActionLog.created_at <= date_to_obj)
        except ValueError:
            pass
    
    query = query.order_by(desc(UserActionLog.created_at))
    
    logs = query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    
    users = User.query.all()
    action_types = db.session.query(UserActionLog.action_type.distinct()).all()
    action_types = [at[0] for at in action_types]
    target_types = db.session.query(UserActionLog.target_type.distinct()).filter(
        UserActionLog.target_type.isnot(None)
    ).all()
    target_types = [tt[0] for tt in target_types]
    
    stats = {
        'total_logs': UserActionLog.query.count(),
        'today_logs': UserActionLog.query.filter(
            UserActionLog.created_at >= datetime.utcnow().date()
        ).count(),
        'unique_users_today': db.session.query(UserActionLog.user_id.distinct()).filter(
            UserActionLog.created_at >= datetime.utcnow().date(),
            UserActionLog.user_id.isnot(None)
        ).count()
    }
    
    return render_template('admin_logs.html',
                         logs=logs,
                         users=users,
                         action_types=action_types,
                         target_types=target_types,
                         stats=stats,
                         filters={
                             'action_type': action_type,
                             'user_id': user_id,
                             'target_type': target_type,
                             'date_from': date_from,
                             'date_to': date_to
                         })

@admin_bp.route('/logs/live')
@login_required
@admin_required
def live_logs():
    # ✅ ЛОГИРУЕМ ПРОСМОТР ЖИВЫХ ЛОГОВ
    log_admin_action('view_live_logs', 'Открыт режим просмотра живых логов')
    return render_template('admin_live_logs.html')



@admin_bp.route('/api/logs/recent')
@login_required
@admin_required
def api_recent_logs():
    """API для получения последних логов БЕЗ IP"""
    limit = request.args.get('limit', 20, type=int)
    since_id = request.args.get('since_id', 0, type=int)
    
    query = UserActionLog.query
    if since_id > 0:
        query = query.filter(UserActionLog.id > since_id)
    
    logs = query.order_by(desc(UserActionLog.created_at)).limit(limit).all()
    
    return jsonify({
        'logs': [{
            'id': log.id,
            'user': log.user_display,
            'action_type': log.action_type,
            'description': log.action_description,
            'target_type': log.target_type,
            'target_id': log.target_id,
            # 'ip_address': log.ip_address,  # УДАЛЕНО
            'time': log.formatted_time,
            'additional_data': log.additional_data
        } for log in logs]
    })







@admin_bp.route('/logs/clear', methods=['POST'])
@login_required
@admin_required
def clear_logs():
    days = request.form.get('days', type=int)
    
    if days:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        deleted_count = UserActionLog.query.filter(
            UserActionLog.created_at < cutoff_date
        ).count()
        
        UserActionLog.query.filter(
            UserActionLog.created_at < cutoff_date
        ).delete()
        
        db.session.commit()
        
        # ✅ ЛОГИРУЕМ ОЧИСТКУ ЛОГОВ
        log_admin_action(
            'clear_logs',
            f'Очищены логи старше {days} дней. Удалено записей: {deleted_count}',
            additional_data={'days': days, 'deleted_count': deleted_count}
        )
        
        flash(f'Удалено {deleted_count} записей логов старше {days} дней', 'success')
    else:
        flash('Укажите количество дней', 'error')
    
    return redirect(url_for('admin.view_logs'))