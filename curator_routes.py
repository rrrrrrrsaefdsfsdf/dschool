from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from extensions import db
from forms import CuratorProfileForm, TaskForm, LabForm
from models import LabProgress, User, Task, Lab, Course, CourseModeration, UserCourse, UserTaskProgress
from utils import get_lab_db
from logging_utils import log_curator_action



curator_bp = Blueprint('curator', __name__, url_prefix='/curator')

def curator_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or (current_user.role != 'curator' and not current_user.is_admin):
            flash('Доступ только для кураторов', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@curator_bp.route('/course/<int:course_id>')
@login_required
@curator_required
def manage_course(course_id):
    course = Course.query.get_or_404(course_id)
    
    # Проверяем права доступа
    if not current_user.is_admin and course.curator_id != current_user.id:
        flash('У вас нет доступа к этому курсу', 'error')
        return redirect(url_for('dashboard'))
    
    # Получаем задачи и лабы курса
    tasks = Task.query.filter_by(course_id=course_id).all()
    labs = Lab.query.filter_by(course_id=course_id).all()
    
    # Получаем ожидающие модерацию изменения
    pending_moderations = CourseModeration.query.filter_by(
        course_id=course_id,
        curator_id=current_user.id,
        status='pending'
    ).order_by(CourseModeration.created_at.desc()).all()
    
    return render_template('curator/manage_course.html', 
                         course=course, 
                         tasks=tasks, 
                         labs=labs,
                         pending_moderations=pending_moderations)






@curator_bp.route('/course/<int:course_id>/task/new', methods=['GET', 'POST'])
@login_required
@curator_required
def new_task(course_id):
    course = Course.query.get_or_404(course_id)
    
    if not current_user.is_admin and course.curator_id != current_user.id:
        flash('У вас нет доступа к этому курсу', 'error')
        return redirect(url_for('dashboard'))
    
    form = TaskForm()
    
    if form.validate_on_submit():
        moderation_data = {
            'title': form.title.data,
            'description': form.description.data,
            'type': form.type.data,
            'difficulty': getattr(form, 'difficulty', None) and form.difficulty.data or 'Легко'
        }
        
        moderation = CourseModeration(
            curator_id=current_user.id,
            course_id=course_id,
            change_type='add_task',
            change_data=moderation_data,
            status='pending'
        )
        
        db.session.add(moderation)
        db.session.commit()
        
        # ✅ ДОБАВЬ ЭТО ЛОГИРОВАНИЕ
        log_curator_action(
            'request_add_task',
            f'Запрос на добавление задачи "{form.title.data}" в курс "{course.title}"',
            target_type='course',
            target_id=course_id,
            additional_data={
                'task_title': form.title.data,
                'task_type': form.type.data,
                'moderation_id': moderation.id
            }
        )
        
        flash('Запрос на добавление задачи отправлен на модерацию', 'success')
        return redirect(url_for('curator.manage_course', course_id=course_id))
    
    return render_template('curator/task_form.html', form=form, course=course, title='Создать новую задачу')

# Аналогично добавь логирование в другие функции куратора...




@curator_bp.route('/course/<int:course_id>/task/<int:task_id>/edit', methods=['GET', 'POST'])
@login_required
@curator_required
def edit_task(course_id, task_id):
    course = Course.query.get_or_404(course_id)
    task = Task.query.get_or_404(task_id)
    
    # Проверяем права доступа
    if not current_user.is_admin and course.curator_id != current_user.id:
        flash('У вас нет доступа к этому курсу', 'error')
        return redirect(url_for('dashboard'))
    
    if task.course_id != course_id:
        flash('Задача не принадлежит этому курсу', 'error')
        return redirect(url_for('curator.manage_course', course_id=course_id))
    
    form = TaskForm(obj=task)
    
    if form.validate_on_submit():
        # Создаем запрос на модерацию для редактирования задачи
        moderation_data = {
            'task_id': task_id,
            'title': form.title.data,
            'description': form.description.data,
            'type': form.type.data,
            'difficulty': getattr(form, 'difficulty', None) and form.difficulty.data or task.difficulty or 'Легко'
        }
        
        moderation = CourseModeration(
            curator_id=current_user.id,
            course_id=course_id,
            change_type='edit_task',
            change_data=moderation_data,
            status='pending'
        )
        
        db.session.add(moderation)
        db.session.commit()
        
        flash('Запрос на изменение задачи отправлен на модерацию', 'success')
        return redirect(url_for('curator.manage_course', course_id=course_id))
    
    return render_template('curator/task_form.html', 
                         form=form, 
                         course=course, 
                         task=task,
                         title='Редактировать задачу')

@curator_bp.route('/course/<int:course_id>/lab/new', methods=['GET', 'POST'])
@login_required
@curator_required
def new_lab(course_id):
    course = Course.query.get_or_404(course_id)
    
    # Проверяем права доступа
    if not current_user.is_admin and course.curator_id != current_user.id:
        flash('У вас нет доступа к этому курсу', 'error')
        return redirect(url_for('dashboard'))
    
    form = LabForm()
    
    if form.validate_on_submit():
        # Создаем запрос на модерацию для добавления лабы
        full_endpoint = f'/vulnerable/{form.endpoint.data}' if not form.endpoint.data.startswith('/') else form.endpoint.data
        full_flag = f'FLAG{{{form.flag.data}}}' if not form.flag.data.startswith('FLAG{') else form.flag.data
        
        moderation_data = {
            'title': form.title.data,
            'description': form.description.data,
            'difficulty': form.difficulty.data,
            'endpoint': full_endpoint,
            'flag': full_flag,
            'type': getattr(form, 'type', None) and form.type.data or 'SQL Injection'
        }
        
        moderation = CourseModeration(
            curator_id=current_user.id,
            course_id=course_id,
            change_type='add_lab',
            change_data=moderation_data,
            status='pending'
        )
        
        db.session.add(moderation)
        db.session.commit()
        
        flash('Запрос на добавление лабораторной работы отправлен на модерацию', 'success')
        return redirect(url_for('curator.manage_course', course_id=course_id))
    
    return render_template('curator/lab_form.html', 
                         form=form, 
                         course=course, 
                         title='Создать новую лабораторную работу')

@curator_bp.route('/course/<int:course_id>/lab/<int:lab_id>/edit', methods=['GET', 'POST'])
@login_required
@curator_required
def edit_lab(course_id, lab_id):
    course = Course.query.get_or_404(course_id)
    lab = Lab.query.get_or_404(lab_id)
    
    # Проверяем права доступа
    if not current_user.is_admin and course.curator_id != current_user.id:
        flash('У вас нет доступа к этому курсу', 'error')
        return redirect(url_for('dashboard'))
    
    if lab.course_id != course_id:
        flash('Лабораторная работа не принадлежит этому курсу', 'error')
        return redirect(url_for('curator.manage_course', course_id=course_id))
    
    # Создаем форму с текущими данными лабы
    form = LabForm()
    if request.method == 'GET':
        form.title.data = lab.title
        form.description.data = lab.description
        form.difficulty.data = lab.difficulty
        form.endpoint.data = lab.endpoint.replace('/vulnerable/', '') if lab.endpoint.startswith('/vulnerable/') else lab.endpoint
        form.flag.data = lab.flag.replace('FLAG{', '').replace('}', '') if lab.flag.startswith('FLAG{') else lab.flag
        if hasattr(form, 'type'):
            form.type.data = lab.type
    
    if form.validate_on_submit():
        # Создаем запрос на модерацию для редактирования лабы
        full_endpoint = f'/vulnerable/{form.endpoint.data}' if not form.endpoint.data.startswith('/') else form.endpoint.data
        full_flag = f'FLAG{{{form.flag.data}}}' if not form.flag.data.startswith('FLAG{') else form.flag.data
        
        moderation_data = {
            'lab_id': lab_id,
            'title': form.title.data,
            'description': form.description.data,
            'difficulty': form.difficulty.data,
            'endpoint': full_endpoint,
            'flag': full_flag,
            'type': getattr(form, 'type', None) and form.type.data or lab.type
        }
        
        moderation = CourseModeration(
            curator_id=current_user.id,
            course_id=course_id,
            change_type='edit_lab',
            change_data=moderation_data,
            status='pending'
        )
        
        db.session.add(moderation)
        db.session.commit()
        
        flash('Запрос на изменение лабораторной работы отправлен на модерацию', 'success')
        return redirect(url_for('curator.manage_course', course_id=course_id))
    
    return render_template('curator/lab_form.html', 
                         form=form, 
                         course=course, 
                         lab=lab,
                         title='Редактировать лабораторную работу')

@curator_bp.route('/moderation/<int:moderation_id>/cancel', methods=['POST'])
@login_required
@curator_required
def cancel_moderation(moderation_id):
    moderation = CourseModeration.query.get_or_404(moderation_id)
    
    # Проверяем права доступа
    if moderation.curator_id != current_user.id and not current_user.is_admin:
        flash('У вас нет прав для отмены этого запроса', 'error')
        return redirect(url_for('dashboard'))
    
    if moderation.status != 'pending':
        flash('Можно отменить только ожидающие модерацию запросы', 'error')
        return redirect(url_for('curator.manage_course', course_id=moderation.course_id))
    
    db.session.delete(moderation)
    db.session.commit()
    
    flash('Запрос на модерацию отменен', 'success')
    return redirect(url_for('curator.manage_course', course_id=moderation.course_id))




@curator_bp.route('/answer/<int:answer_id>/approve', methods=['POST'])
@login_required
@curator_required
def approve_answer(answer_id):
    answer = UserTaskProgress.query.get_or_404(answer_id)
    
    if answer.task.course_id not in [c.id for c in current_user.curated_courses]:
        flash('У вас нет прав для проверки этого ответа', 'error')
        return redirect(url_for('curator.review_answers'))
    
    if answer.is_checked:
        flash('Ответ уже был проверен', 'warning')
        return redirect(url_for('curator.review_answers'))
    
    answer.is_checked = True
    answer.is_approved = True
    answer.checked_at = datetime.utcnow()
    db.session.commit()
    
    # ✅ ДОБАВЬ ЭТО ЛОГИРОВАНИЕ
    log_curator_action(
        'approve_student_answer',
        f'Одобрен ответ студента {answer.user.username} по задаче "{answer.task.title}"',
        target_type='task',
        target_id=answer.task_id,
        additional_data={
            'student_id': answer.user_id,
            'student_username': answer.user.username,
            'course_id': answer.task.course_id,
            'answer_text': answer.user_answer[:100] if answer.user_answer else None
        }
    )
    
    flash(f'Ответ студента {answer.user.username} по задаче "{answer.task.title}" одобрен!', 'success')
    return redirect(url_for('curator.review_answers'))





@curator_bp.route('/answer/<int:answer_id>/reject', methods=['POST'])
@login_required
@curator_required
def reject_answer(answer_id):
    answer = UserTaskProgress.query.get_or_404(answer_id)
    
    # Проверяем права доступа
    if answer.task.course_id not in [c.id for c in current_user.curated_courses]:
        flash('У вас нет прав для проверки этого ответа', 'error')
        return redirect(url_for('curator.review_answers'))
    
    if answer.is_checked:
        flash('Ответ уже был проверен', 'warning')
        return redirect(url_for('curator.review_answers'))
    
    answer.is_checked = True
    answer.is_approved = False
    answer.checked_at = datetime.utcnow()
    
    db.session.commit()
    
    flash(f'Ответ студента {answer.user.username} по задаче "{answer.task.title}" отклонен', 'warning')
    return redirect(url_for('curator.review_answers'))

@curator_bp.route('/answers')
@login_required
@curator_required
def review_answers():
    # Получаем курсы куратора
    curator_courses = current_user.curated_courses
    course_ids = [c.id for c in curator_courses]
    
    if not course_ids:
        flash('У вас нет назначенных курсов', 'info')
        return redirect(url_for('dashboard'))
    
    # Фильтр по типу задач
    task_type = request.args.get('type', None)
    course_id = request.args.get('course_id', None)
    
    # Получаем непроверенные ответы по задачам из курсов куратора - используем явное условие join
    query = db.session.query(UserTaskProgress).join(
        Task, UserTaskProgress.task_id == Task.id
    ).filter(
        UserTaskProgress.is_checked == False,
        Task.course_id.in_(course_ids)
    )
    
    # Фильтруем по типу задачи
    if task_type:
        query = query.filter(Task.type == task_type)
    
    # Фильтруем по курсу
    if course_id:
        query = query.filter(Task.course_id == int(course_id))
    
    pending_answers = query.order_by(UserTaskProgress.id.desc()).all()
    
    # Статистика
    stats = {
        'total_pending': len(pending_answers),
        'theory_pending': len([a for a in pending_answers if a.task.type == 'Теория']),
        'practice_pending': len([a for a in pending_answers if a.task.type == 'Практика'])
    }
    
    return render_template('curator/review_answers.html', 
                         answers=pending_answers, 
                         stats=stats,
                         curator_courses=curator_courses,
                         selected_type=task_type,
                         selected_course_id=course_id)

@curator_bp.route('/students')
@login_required
@curator_required
def view_students():
    # Получаем курсы куратора
    curator_courses = current_user.curated_courses
    course_ids = [c.id for c in curator_courses]
    
    if not course_ids:
        flash('У вас нет назначенных курсов', 'info')
        return redirect(url_for('dashboard'))
    
    # Получаем студентов, записанных на курсы куратора - используем явное условие join
    students = db.session.query(User).join(
        UserCourse, User.id == UserCourse.user_id
    ).filter(
        UserCourse.course_id.in_(course_ids),
        User.role == 'student'
    ).distinct().all()
    
    # Статистика по каждому студенту
    student_stats = {}
    for student in students:
        # Решенные задачи студента в курсах куратора - используем явное условие join
        solved_tasks = db.session.query(UserTaskProgress).join(
            Task, UserTaskProgress.task_id == Task.id
        ).filter(
            UserTaskProgress.user_id == student.id,
            UserTaskProgress.is_approved == True,
            Task.course_id.in_(course_ids)
        ).count()
        
        # Всего задач в курсах куратора
        total_tasks = db.session.query(Task).filter(
            Task.course_id.in_(course_ids)
        ).count()
        
        # Решенные лабы студента в курсах куратора - используем явное условие join
        solved_labs = db.session.query(LabProgress).join(
            Lab, LabProgress.lab_id == Lab.id
        ).filter(
            LabProgress.user_id == student.id,
            LabProgress.is_solved == True,
            Lab.course_id.in_(course_ids)
        ).count()
        
        # Всего лаб в курсах куратора
        total_labs = db.session.query(Lab).filter(
            Lab.course_id.in_(course_ids)
        ).count()
        
        # Курсы студента у данного куратора - используем явное условие join
        student_courses = db.session.query(Course).join(
            UserCourse, Course.id == UserCourse.course_id
        ).filter(
            UserCourse.user_id == student.id,
            Course.id.in_(course_ids)
        ).all()
        
        student_stats[student.id] = {
            'solved_tasks': solved_tasks,
            'total_tasks': total_tasks,
            'solved_labs': solved_labs,
            'total_labs': total_labs,
            'courses': student_courses
        }
    
    return render_template('curator/view_students.html', 
                         students=students, 
                         student_stats=student_stats,
                         curator_courses=curator_courses)








@curator_bp.route('/profile', methods=['GET', 'POST'])
@login_required
@curator_required
def edit_profile():
    form = CuratorProfileForm()
    
    if request.method == 'GET':
        form.curator_name.data = current_user.curator_name
        form.curator_telegram.data = current_user.curator_telegram
        form.curator_email.data = current_user.curator_email
    
    if form.validate_on_submit():
        current_user.curator_name = form.curator_name.data
        current_user.curator_telegram = form.curator_telegram.data
        current_user.curator_email = form.curator_email.data
        
        db.session.commit()
        flash('Ваши контактные данные обновлены!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('curator/edit_profile.html', form=form)








from forms import CuratorCreateStudentForm  # добавь этот импорт в начало файла







@curator_bp.route('/create-student', methods=['GET', 'POST'])
@login_required
@curator_required
def create_student():
    form = CuratorCreateStudentForm()
    
    curator_courses = current_user.curated_courses
    form.course_ids.choices = [(c.id, c.title) for c in curator_courses]
    
    if not curator_courses:
        flash('У вас нет курсов для создания студентов', 'error')
        return redirect(url_for('dashboard'))
    
    if form.validate_on_submit():
        existing_user = User.query.filter_by(username=form.username.data).first()
        if existing_user:
            flash('Пользователь с таким логином уже существует', 'error')
            return render_template('curator/create_student.html', form=form)
        
        selected_course = Course.query.get(form.course_ids.data)
        if not selected_course or selected_course.curator_id != current_user.id:
            flash('Выбранный курс вам не принадлежит', 'error')
            return render_template('curator/create_student.html', form=form)
        
        try:
            new_student = User(
                username=form.username.data,
                role='student'
            )
            new_student.set_password(form.password.data)
            
            db.session.add(new_student)
            db.session.flush()
            
            user_course = UserCourse(
                user_id=new_student.id,
                course_id=form.course_ids.data,
                granted_by=current_user.id
            )
            db.session.add(user_course)
            db.session.commit()
            
            # ✅ ДОБАВЬ ЭТО ЛОГИРОВАНИЕ
            log_curator_action(
                'create_student',
                f'Создан студент {new_student.username} и привязан к курсу "{selected_course.title}"',
                target_type='user',
                target_id=new_student.id,
                additional_data={
                    'course_id': selected_course.id,
                    'course_title': selected_course.title
                }
            )
            
            flash(f'Студент {new_student.username} успешно создан и привязан к курсу "{selected_course.title}"', 'success')
            return redirect(url_for('curator.view_students'))
            
        except Exception as e:
            db.session.rollback()
            # ✅ ЛОГИРОВАНИЕ ОШИБКИ
            log_curator_action(
                'create_student_error',
                f'Ошибка при создании студента: {str(e)}',
                additional_data={'error': str(e), 'username': form.username.data}
            )
            flash(f'Ошибка при создании студента: {str(e)}', 'error')
    
    return render_template('curator/create_student.html', form=form)






@curator_bp.route('/students/<int:student_id>/assign-course', methods=['POST'])
@login_required
@curator_required
def assign_course_to_student(student_id):
    student = User.query.get_or_404(student_id)
    course_id = request.form.get('course_id')
    
    if not course_id:
        flash('Выберите курс', 'error')
        return redirect(url_for('curator.view_students'))
    
    course = Course.query.get_or_404(course_id)
    
    # Проверяем, что курс принадлежит куратору
    if course.curator_id != current_user.id:
        flash('Вы не можете назначать студентов на чужие курсы', 'error')
        return redirect(url_for('curator.view_students'))
    
    # Проверяем, что студент еще не записан на этот курс
    existing = UserCourse.query.filter_by(user_id=student_id, course_id=course_id).first()
    if existing:
        flash(f'Студент {student.username} уже записан на курс "{course.title}"', 'warning')
        return redirect(url_for('curator.view_students'))
    
    # Добавляем привязку
    user_course = UserCourse(
        user_id=student_id,
        course_id=course_id,
        granted_by=current_user.id
    )
    db.session.add(user_course)
    db.session.commit()
    
    flash(f'Студент {student.username} добавлен на курс "{course.title}"', 'success')
    return redirect(url_for('curator.view_students'))