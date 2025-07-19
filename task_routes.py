from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

from extensions import db
from models import Task, UserTaskProgress

task_bp = Blueprint('task', __name__)

@task_bp.route('/task/solve/<int:task_id>', methods=['POST'])
@login_required
def solve_task(task_id):
    task = Task.query.get_or_404(task_id)
    data = request.get_json() or {}
    user_answer = data.get('answer', '').strip()
    if not user_answer:
        return jsonify({"error": "Ответ не может быть пустым"}), 400

    progress = UserTaskProgress.query.filter_by(user_id=current_user.id, task_id=task.id).first()
    if not progress:
        progress = UserTaskProgress(user_id=current_user.id, task_id=task.id)

    progress.user_answer = user_answer
    progress.is_checked = False
    progress.is_approved = False
    progress.checked_at = None
    db.session.add(progress)
    db.session.commit()
    return jsonify({"message": "Ваш ответ отправлен на проверку."})