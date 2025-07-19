from flask import Blueprint, jsonify
from flask_login import login_required, current_user
from sqlalchemy import text
from extensions import db
from models import Task, UserTaskProgress, Lab, LabProgress

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/tasks')
@login_required
def api_tasks():
    try:
        tasks = Task.query.all()
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

            result.append({
                'id': t.id,
                'title': t.title,
                'description': t.description,
                'status': status,
                'correct_answer': t.correct_answer,
                'approved_answer': approved_answer,
                'type': t.type
            })

        return jsonify(tasks=result)
    except Exception as e:
        print(f"Ошибка в api_tasks: {e}")
        return jsonify({'error': 'Ошибка загрузки задач'}), 500


@api_bp.route('/labs')
@login_required
def api_labs():
    try:
        labs = Lab.query.all()
        result = []

        for lab in labs:
            # Проверка прогресса
            progress_result = LabProgress.query.filter_by(
                user_id=current_user.id,
                lab_id=lab.id
            ).first()

            is_solved = progress_result.is_solved if progress_result else False

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
                'flag_instruction': 'Флаг имеет формат FLAG{текст}. Скопируйте его точно как найдете в лаборатории.'
            })

        return jsonify({'success': True, 'labs': result})

    except Exception as e:
        print(f"Ошибка в api_labs: {e}")
        return jsonify({'success': False, 'labs': [], 'error': str(e)}), 500