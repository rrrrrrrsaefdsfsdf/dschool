from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

from extensions import db
from models import Task, UserTaskProgress

task_bp = Blueprint('task', __name__)
# Добавь импорт в начало файла
from logging_utils import log_user_action

@task_bp.route('/task/solve/<int:task_id>', methods=['POST'])
@login_required
def solve_task(task_id):
    task = Task.query.get_or_404(task_id)
    data = request.get_json() or {}
    user_answer = data.get('answer', '').strip()
    
    if not user_answer:
        return jsonify({"error": "Ответ не может быть пустым"}), 400

    # Проверяем предыдущий ответ для логирования
    previous_progress = UserTaskProgress.query.filter_by(user_id=current_user.id, task_id=task.id).first()
    is_resubmission = bool(previous_progress)

    progress = UserTaskProgress.query.filter_by(user_id=current_user.id, task_id=task.id).first()
    if not progress:
        progress = UserTaskProgress(user_id=current_user.id, task_id=task.id)

    progress.user_answer = user_answer
    progress.is_checked = False
    progress.is_approved = False
    progress.checked_at = None
    db.session.add(progress)
    db.session.commit()
    
    # ✅ ДОБАВЬ ЭТО ЛОГИРОВАНИЕ
    log_user_action(
        'submit_task_answer',
        f'Отправлен ответ на задачу "{task.title}"',
        target_type='task',
        target_id=task_id,
        additional_data={
            'task_type': task.type,
            'answer_length': len(user_answer),
            'course_id': task.course_id,
            'course_title': task.course.title if task.course else None,
            'is_resubmission': is_resubmission,
            'task_difficulty': getattr(task, 'difficulty', None)
        }
    )
    
    return jsonify({"message": "Ваш ответ отправлен на проверку."})