from datetime import datetime

from flask import Blueprint, render_template, request, abort, jsonify
from flask_login import login_required, current_user

from extensions import db, csrf
from models import Lab, LabProgress
from utils import get_lab_db
from logging_utils import log_user_action



lab_bp = Blueprint('lab', __name__)


@lab_bp.route('/vulnerable/<path:lab_path>', methods=['GET', 'POST'])
@csrf.exempt
def universal_lab_handler(lab_path):
    lab = Lab.query.filter_by(endpoint=f'/vulnerable/{lab_path}').first()
    if not lab:
        # ✅ ЛОГИРОВАНИЕ ДОСТУПА К НЕСУЩЕСТВУЮЩЕЙ ЛАБЕ
        if current_user.is_authenticated:
            log_user_action(
                'access_unknown_lab',
                f'Попытка доступа к несуществующей лабе: {lab_path}',
                additional_data={'requested_path': lab_path}
            )
        abort(404)

    # ✅ ЛОГИРОВАНИЕ ДОСТУПА К ЛАБЕ
    if current_user.is_authenticated:
        log_user_action(
            'access_lab',
            f'Доступ к лабораторной работе "{lab.title}"',
            target_type='lab',
            target_id=lab.id,
            additional_data={
                'lab_path': lab_path,
                'lab_difficulty': lab.difficulty,
                'lab_type': lab.type,
                'method': request.method
            }
        )
    lab = Lab.query.filter_by(endpoint=f'/vulnerable/{lab_path}').first()
    if not lab:
        abort(404)

    handler_type = getattr(lab, 'handler_type', 'static')

    # Исправлены операторы сравнения
    if handler_type == 'auth_bypass':
        return handle_auth_bypass_lab(lab)
    elif handler_type == 'union_injection':
        return handle_union_injection_lab(lab)
    elif handler_type == 'blind_injection':
        return handle_blind_injection_lab(lab)
    else:
        # Если тип не определен, пытаемся определить по пути
        if 'login' in lab_path or 'auth' in lab_path:
            return handle_auth_bypass_lab(lab)
        elif 'union' in lab_path:
            return handle_union_injection_lab(lab)
        elif 'blind' in lab_path:
            return handle_blind_injection_lab(lab)
        else:
            abort(404)

def handle_auth_bypass_lab(lab):
    error = None
    success = False
    user_data = None
    query = None

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            error = "Заполните все поля"
        else:
            conn = get_lab_db()
            cursor = conn.cursor()
            query = f"SELECT * FROM vulnerable_users WHERE username='{username}' AND password='{password}'"

            try:
                cursor.execute(query)
                result = cursor.fetchone()
                if result:
                    user_data = {
                        'id': result[0],
                        'username': result[1],
                        'role': result[3],
                        'secret': lab.flag
                    }
                    success = True
                else:
                    error = "Неверные учетные данные"
            except Exception as e:
                error = f"SQL Error: {str(e)}"
            finally:
                conn.close()

    return render_template('labs/sql_login.html',
                           lab=lab,
                           error=error,
                           success=success,
                           user_data=user_data,
                           query=query)


def handle_union_injection_lab(lab):
    search = ''
    results = []
    error = None
    query = None
    lab_type = 'union_injection'

    if request.method == 'POST':
        search = request.form.get('search', '').strip()
        conn = get_lab_db()
        cursor = conn.cursor()
        query = f"SELECT name, description, price FROM vulnerable_products WHERE name LIKE '%{search}%'"

        try:
            cursor.execute(query)
            raw_results = cursor.fetchall()

            results = []
            for row in raw_results:
                filtered_row = []
                for cell in row:
                    if cell and 'FLAG{' in str(cell):
                        filtered_row.append(lab.flag)
                    else:
                        filtered_row.append(cell)
                results.append(tuple(filtered_row))

        except Exception as e:
            error = f"SQL Error: {str(e)}"
        finally:
            conn.close()

    return render_template('labs/sql_union.html',
                           lab=lab,
                           results=results,
                           search=search,
                           error=error,
                           query=query,
                           lab_type=lab_type,
                           str=str)


def handle_blind_injection_lab(lab):
    user_id = ''
    exists = None
    username = None
    error = None
    query = None
    debug_info = None

    if request.method == 'POST':
        user_id = request.form.get('user_id', '').strip()

        if not user_id:
            error = "Введите ID пользователя"
        else:
            conn = get_lab_db()
            cursor = conn.cursor()
            
            query = f"SELECT username FROM vulnerable_users WHERE id={user_id}"

            try:
                cursor.execute(query)
                result = cursor.fetchone()

                if result:
                    exists = True
                    username = result[0]
                    if username == 'admin':
                        username = lab.flag
                else:
                    exists = False

            except Exception as e:
                error = f"SQL Error: {str(e)}"
                exists = False
            finally:
                conn.close()

    return render_template('labs/sql_blind.html',
                           lab=lab,
                           exists=exists,
                           user_id=user_id,
                           error=error,
                           query=query,
                           username=username)








@lab_bp.route('/lab/<int:lab_id>/submit', methods=['POST'])
@login_required
def submit_lab_flag(lab_id):
    try:
        lab = Lab.query.get_or_404(lab_id)
        flag = request.form.get('flag', '').strip()

        if not flag:
            # ✅ ЛОГИРОВАНИЕ ПУСТОГО ФЛАГА
            log_user_action(
                'submit_flag_empty',
                f'Попытка отправки пустого флага для лабы "{lab.title}"',
                target_type='lab',
                target_id=lab_id
            )
            return jsonify({'success': False, 'message': 'Флаг не может быть пустым'}), 400

        if flag == lab.flag:
            progress = LabProgress.query.filter_by(user_id=current_user.id, lab_id=lab_id).first()
            if not progress:
                progress = LabProgress(user_id=current_user.id, lab_id=lab_id)

            if progress.is_solved:
                # ✅ ЛОГИРОВАНИЕ ПОВТОРНОЙ ОТПРАВКИ
                log_user_action(
                    'submit_flag_duplicate',
                    f'Повторная отправка правильного флага для уже решенной лабы "{lab.title}"',
                    target_type='lab',
                    target_id=lab_id,
                    additional_data={
                        'lab_difficulty': lab.difficulty,
                        'lab_type': lab.type,
                        'course_id': lab.course_id
                    }
                )
                return jsonify({'success': True, 'message': 'Лабораторная работа уже была решена ранее!'})

            progress.is_solved = True
            progress.solved_at = datetime.utcnow()
            db.session.add(progress)
            db.session.commit()
            
            # ✅ ЛОГИРОВАНИЕ УСПЕШНОГО РЕШЕНИЯ
            log_user_action(
                'submit_flag_success',
                f'Успешно решена лабораторная работа "{lab.title}"',
                target_type='lab',
                target_id=lab_id,
                additional_data={
                    'lab_difficulty': lab.difficulty,
                    'lab_type': lab.type,
                    'course_id': lab.course_id,
                    'course_title': lab.course.title if lab.course else None,
                    'flag_submitted': flag
                }
            )
            
            return jsonify({'success': True, 'message': 'Поздравляем! Лабораторная работа решена!'})
        else:
            # ✅ ЛОГИРОВАНИЕ НЕПРАВИЛЬНОГО ФЛАГА
            log_user_action(
                'submit_flag_wrong',
                f'Неправильный флаг для лабы "{lab.title}"',
                target_type='lab',
                target_id=lab_id,
                additional_data={
                    'submitted_flag': flag,
                    'lab_difficulty': lab.difficulty,
                    'lab_type': lab.type,
                    'course_id': lab.course_id
                }
            )
            return jsonify({'success': False, 'message': 'Неправильный флаг. Проверьте формат и попробуйте еще раз.'})

    except Exception as e:
        db.session.rollback()
        # ✅ ЛОГИРОВАНИЕ ОШИБКИ
        lab_title = lab.title if 'lab' in locals() else 'Unknown'
        log_user_action(
            'submit_flag_error',
            f'Ошибка при проверке флага для лабы "{lab_title}": {str(e)}',
            target_type='lab',
            target_id=lab_id,
            additional_data={'error': str(e)}
        )
        return jsonify({'success': False, 'message': 'Произошла ошибка при проверке флага'}), 500