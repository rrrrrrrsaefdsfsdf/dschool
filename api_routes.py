from flask import Blueprint, jsonify
from flask_login import login_required, current_user
from sqlalchemy import text
from extensions import db
from models import Task, UserTaskProgress, Lab, LabProgress, Course

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/tasks')
@login_required
def api_tasks():
    try:
        # Получаем задачи, доступные пользователю
        if current_user.is_admin:
            tasks = Task.query.all()
        elif current_user.role == 'curator':
            # Куратор видит задачи из своих курсов + задачи без привязки к курсу
            curated_course_ids = [c.id for c in current_user.curated_courses]
            if curated_course_ids:
                tasks = Task.query.filter(
                    (Task.course_id.in_(curated_course_ids)) | (Task.course_id == None)
                ).all()
            else:
                # Если у куратора нет курсов - только задачи без привязки к курсу
                tasks = Task.query.filter_by(course_id=None).all()
        else:
            # Для студентов - только задачи из их курсов
            user_course_ids = [uc.course_id for uc in current_user.user_courses]
            if user_course_ids:
                # Задачи из курсов пользователя + задачи без привязки к курсу
                tasks = Task.query.filter(
                    (Task.course_id.in_(user_course_ids)) | (Task.course_id == None)
                ).all()
            else:
                # Только задачи без привязки к курсу
                tasks = Task.query.filter_by(course_id=None).all()

        result = []
        for t in tasks:
            progress = UserTaskProgress.query.filter_by(
                user_id=current_user.id,
                task_id=t.id
            ).order_by(
                UserTaskProgress.checked_at.desc().nullslast(),
                UserTaskProgress.id.desc()
            ).first()

            if progress:
                if progress.is_checked:
                    status = 'approved' if progress.is_approved else 'rejected'
                else:
                    status = 'pending'
                approved_answer = progress.user_answer if progress.is_approved else None
            else:
                status = 'not_answered'
                approved_answer = None

            # Добавляем информацию о курсе
            course_info = None
            if t.course:
                course_info = {
                    'id': t.course.id,
                    'title': t.course.title,
                    'curator': t.course.curator.username if t.course.curator else None
                }

            result.append({
                'id': t.id,
                'title': t.title,
                'description': t.description,
                'status': status,
                'correct_answer': t.correct_answer,
                'approved_answer': approved_answer,
                'type': t.type,
                'course': course_info
            })

        return jsonify(tasks=result)
    except Exception as e:
        print(f"Ошибка в api_tasks: {e}")
        return jsonify({'error': 'Ошибка загрузки задач'}), 500

@api_bp.route('/labs')
@login_required
def api_labs():
    try:
        # Получаем лабы, доступные пользователю
        if current_user.is_admin:
            labs = Lab.query.all()
        elif current_user.role == 'curator':
            # Куратор видит лабы из своих курсов + лабы без привязки к курсу
            curated_course_ids = [c.id for c in current_user.curated_courses]
            if curated_course_ids:
                labs = Lab.query.filter(
                    (Lab.course_id.in_(curated_course_ids)) | (Lab.course_id == None)
                ).all()
            else:
                # Если у куратора нет курсов - только лабы без привязки к курсу
                labs = Lab.query.filter_by(course_id=None).all()
        else:
            # Для студентов - только лабы из их курсов
            user_course_ids = [uc.course_id for uc in current_user.user_courses]
            if user_course_ids:
                # Лабы из курсов пользователя + лабы без привязки к курсу
                labs = Lab.query.filter(
                    (Lab.course_id.in_(user_course_ids)) | (Lab.course_id == None)
                ).all()
            else:
                # Только лабы без привязки к курсу
                labs = Lab.query.filter_by(course_id=None).all()

        result = []
        for lab in labs:
            # Проверка прогресса
            progress_result = LabProgress.query.filter_by(
                user_id=current_user.id,
                lab_id=lab.id
            ).first()

            is_solved = progress_result.is_solved if progress_result else False

            # Добавляем информацию о курсе
            course_info = None
            if lab.course:
                course_info = {
                    'id': lab.course.id,
                    'title': lab.course.title,
                    'curator': lab.course.curator.username if lab.course.curator else None
                }

            result.append({
                'id': lab.id,
                'title': lab.title,
                'description': lab.description,
                'difficulty': lab.difficulty,
                'endpoint': lab.endpoint,
                'type': lab.type,
                'is_solved': is_solved,
                'hints': [],
                'instruction_before': '',
                'instruction_after': '',
                'flag_format': 'FLAG{...}',
                'flag_instruction': 'Флаг имеет формат FLAG{текст}. Скопируйте его точно как найдете в лаборатории.',
                'course': course_info
            })

        return jsonify({'success': True, 'labs': result})

    except Exception as e:
        print(f"Ошибка в api_labs: {e}")
        return jsonify({'success': False, 'labs': [], 'error': str(e)}), 500

@api_bp.route('/user/courses')
@login_required
def api_user_courses():
    try:
        courses = current_user.accessible_courses
        result = []
        for course in courses:
            result.append({
                'id': course.id,
                'title': course.title,
                'description': course.description,
                'curator': course.curator.username if course.curator else None
            })
        return jsonify({'courses': result})
    except Exception as e:
        print(f"Ошибка в api_user_courses: {e}")
        return jsonify({'error': 'Ошибка загрузки курсов'}), 500