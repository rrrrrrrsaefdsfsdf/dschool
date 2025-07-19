from datetime import datetime

from flask import Blueprint, render_template, request, abort, jsonify
from flask_login import login_required, current_user

from extensions import db, csrf
from models import Lab, LabProgress
from utils import get_lab_db

lab_bp = Blueprint('lab', __name__)


@lab_bp.route('/vulnerable/<path:lab_path>', methods=['GET', 'POST'])
@csrf.exempt
def universal_lab_handler(lab_path):
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
                        'secret': result[4]
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
                           user_data=user_data,  # Изменено с 'user' на 'user_data'
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

            # Фильтруем результаты - показываем только свой флаг
            results = []
            for row in raw_results:
                filtered_row = []
                for cell in row:
                    if cell and 'FLAG{' in str(cell):
                        # Показываем только union флаг, остальные скрываем
                        if 'union' in str(cell).lower():
                            filtered_row.append(cell)  # Показываем правильный флаг
                        else:
                            filtered_row.append('[СКРЫТЫЕ ДАННЫЕ]')  # Скрываем другие флаги
                    else:
                        filtered_row.append(cell)  # Обычные данные показываем как есть
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

            # Проверяем, что введено
            print(f"DEBUG: Введенное значение: '{user_id}'")

            # Формируем запрос (НЕБЕЗОПАСНО - для демонстрации уязвимости)
            query = f"SELECT username FROM vulnerable_users WHERE id={user_id}"

            try:
                print(f"DEBUG: Выполняемый запрос: {query}")
                cursor.execute(query)
                result = cursor.fetchone()

                if result:
                    exists = True
                    username = result[0]
                    print(f"DEBUG: Найден пользователь: {username}")
                else:
                    exists = False
                    print("DEBUG: Пользователь не найден")

            except Exception as e:
                error = f"SQL Error: {str(e)}"
                print(f"DEBUG: Ошибка SQL: {e}")
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
            return jsonify({'success': False, 'message': 'Флаг не может быть пустым'}), 400

        if flag == lab.flag:
            # Исправлено для работы с правильной моделью
            progress = LabProgress.query.filter_by(user_id=current_user.id, lab_id=lab_id).first()
            if not progress:
                progress = LabProgress(user_id=current_user.id, lab_id=lab_id)

            if progress.is_solved:
                return jsonify({'success': True, 'message': 'Лабораторная работа уже была решена ранее!'})

            progress.is_solved = True
            progress.solved_at = datetime.utcnow()
            db.session.add(progress)
            db.session.commit()
            return jsonify({'success': True, 'message': 'Поздравляем! Лабораторная работа решена!'})
        else:
            return jsonify({'success': False, 'message': 'Неправильный флаг. Проверьте формат и попробуйте еще раз.'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Произошла ошибка при проверке флага'}), 500