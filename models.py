from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db


class User(UserMixin, db.Model):
    __tablename__ = 'users'  # Добавил __tablename__

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Task(db.Model):
    __tablename__ = 'tasks'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(50), nullable=False, default='Практика')
    difficulty = db.Column(db.String(50), default='Легко')
    correct_answer = db.Column(db.Text)
    answer = db.Column(db.Text, nullable=True)  # Для совместимости
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Lab(db.Model):
    __tablename__ = 'labs'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text, nullable=False)
    difficulty = db.Column(db.String(50), nullable=False, default='Средне')
    endpoint = db.Column(db.String(100), nullable=False)  # Уже содержит полный путь /lab/sql/...
    flag = db.Column(db.String(200), nullable=False)    # Уже содержит FLAG{...}
    type = db.Column(db.String(50), nullable=False, default='SQL Injection')
    template_id = db.Column(db.Integer, db.ForeignKey('lab_template.id'))
    template_file = db.Column(db.String(100))  # Добавьте это поле для хранения имени файла
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    template = db.relationship('LabTemplate', backref='labs')

    @property
    def is_solved_by_user(self, user_id):
        """Проверяет, решена ли лаба конкретным пользователем"""
        progress = UserLabProgress.query.filter_by(
            user_id=user_id,
            lab_id=self.id,
            is_solved=True
        ).first()
        return progress is not None


class UserTaskProgress(db.Model):
    __tablename__ = 'user_task_progress'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False)
    user_answer = db.Column(db.Text)
    is_approved = db.Column(db.Boolean, default=False)
    is_checked = db.Column(db.Boolean, default=False)
    checked_at = db.Column(db.DateTime)

    user = db.relationship('User', backref=db.backref('tasks_progress', lazy='dynamic'))
    task = db.relationship('Task')


class UserTaskAnswer(db.Model):
    __tablename__ = 'user_task_answers'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False)
    answer = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    approved_answer = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', backref='task_answers')
    task = db.relationship('Task', backref='user_answers')


class UserLabProgress(db.Model):
    __tablename__ = 'user_lab_progress'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    lab_id = db.Column(db.Integer, db.ForeignKey('labs.id'), nullable=False)
    is_solved = db.Column(db.Boolean, default=False)
    flag_submitted = db.Column(db.String(200), nullable=True)
    solved_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Исправленные relationships без конфликтов
    user = db.relationship('User', backref='user_lab_progress')
    lab = db.relationship('Lab', backref='lab_user_progress')

    __table_args__ = (db.UniqueConstraint('user_id', 'lab_id'),)


class LabProgress(db.Model):
    __tablename__ = 'lab_progress'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    lab_id = db.Column(db.Integer, db.ForeignKey('labs.id'), nullable=False)
    is_solved = db.Column(db.Boolean, default=False)
    solved_at = db.Column(db.DateTime)

    # Уникальные backref names
    user = db.relationship('User', backref='old_lab_progress')
    lab = db.relationship('Lab', backref='old_progress')


class CuratorContact(db.Model):
    __tablename__ = 'curator_contacts'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=True)
    telegram = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<CuratorContact {self.name or "Неизвестный"}>'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'telegram': self.telegram,
            'email': self.email,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    @property
    def display_name(self):
        """Возвращает имя для отображения"""
        return self.name if self.name else "Куратор без имени"

    @property
    def contact_info(self):
        """Возвращает доступные контакты"""
        contacts = []
        if self.telegram:
            contacts.append(f"@{self.telegram}")
        if self.email:
            contacts.append(self.email)
        return " | ".join(contacts) if contacts else "Контакты не указаны"


class LabTemplate(db.Model):
    __tablename__ = 'lab_template'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    template_type = db.Column(db.String(50), nullable=False)
    html_template = db.Column(db.Text, nullable=False)
    default_configs = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'template_type': self.template_type,
            'html_template': self.html_template,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    @property
    def labs_count(self):
        return self.labs.count() if self.labs else 0

    def can_be_deleted(self):
        return self.labs_count == 0


class LabHint(db.Model):
    __tablename__ = 'lab_hints'

    id = db.Column(db.Integer, primary_key=True)
    lab_id = db.Column(db.Integer, db.ForeignKey('labs.id'), nullable=False)
    hint_text = db.Column(db.Text, nullable=False)
    hint_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    lab = db.relationship('Lab', backref=db.backref('hints', lazy='dynamic', order_by='LabHint.hint_order'))


class LabInstruction(db.Model):
    __tablename__ = 'lab_instructions'

    id = db.Column(db.Integer, primary_key=True)
    lab_id = db.Column(db.Integer, db.ForeignKey('labs.id'), nullable=False)
    instruction_type = db.Column(db.String(50), nullable=False)
    content = db.Column(db.Text, nullable=False)

    lab = db.relationship('Lab', backref=db.backref('instructions', lazy='dynamic'))


class LabConfiguration(db.Model):
    __tablename__ = 'lab_configurations'

    id = db.Column(db.Integer, primary_key=True)
    lab_id = db.Column(db.Integer, db.ForeignKey('labs.id'), nullable=False)
    config_key = db.Column(db.String(100), nullable=False)
    config_value = db.Column(db.Text)

    lab = db.relationship('Lab', backref=db.backref('configurations', lazy='dynamic'))

    __table_args__ = (db.UniqueConstraint('lab_id', 'config_key'),)