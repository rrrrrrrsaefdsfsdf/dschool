from flask_wtf import FlaskForm
from wtforms import PasswordField, TextAreaField, StringField, SubmitField, SelectField, BooleanField
from wtforms.validators import DataRequired, Length, Optional, Email


class RegistrationForm(FlaskForm):
    username = StringField('Логин', validators=[DataRequired(), Length(min=3, max=150)])
    password = PasswordField('Пароль', validators=[DataRequired(), Length(min=6)])
    role = SelectField('Роль', choices=[
        ('student', 'Студент'), 
        ('curator', 'Куратор')
    ], default='student')
    # Изменяем на строковый тип без coerce
    course_ids = SelectField('Доступные курсы', choices=[], validators=[Optional()])
    
    # Поля для кураторов
    curator_name = StringField('Имя куратора', validators=[Optional(), Length(max=100)])
    curator_telegram = StringField('Telegram куратора', validators=[Optional(), Length(max=100)])
    curator_email = StringField('Email куратора', validators=[Optional(), Email(), Length(max=120)])
    
    submit = SubmitField('Создать')


class LoginForm(FlaskForm):
    username = StringField('Логин', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    remember_me = BooleanField('Запомнить меня')
    submit = SubmitField('Войти')


class TaskForm(FlaskForm):
    title = StringField('Заголовок', validators=[DataRequired(), Length(max=300)])
    description = TextAreaField('Описание', validators=[DataRequired()])
    type = SelectField('Тип задачи', choices=[('Практика', 'Практика'), ('Теория', 'Теория')], default='Теория')
    submit = SubmitField('Сохранить')


class CuratorContactForm(FlaskForm):
    type = StringField('Тип контакта', validators=[DataRequired()])
    value = StringField('Контакт', validators=[DataRequired()])
    submit = SubmitField('Сохранить')


class LabForm(FlaskForm):
    title = StringField('Название лабы', validators=[DataRequired(), Length(max=300)])
    description = TextAreaField('Описание', validators=[DataRequired()])
    difficulty = SelectField('Сложность', choices=[('Легко', 'Легко'), ('Средне', 'Средне'), ('Сложно', 'Сложно')])
    endpoint = StringField('Эндпоинт', validators=[DataRequired(), Length(max=100)])
    flag = StringField('Флаг', validators=[DataRequired(), Length(max=200)])
    flag_content = StringField('Содержимое флага', validators=[Optional(), Length(max=200)])
    type = SelectField('Тип', choices=[('SQL Injection', 'SQL Injection'), ('XSS', 'XSS'), ('CSRF', 'CSRF')], default='SQL Injection')
    submit = SubmitField('Сохранить')


class CourseForm(FlaskForm):
    title = StringField('Название курса', validators=[DataRequired(), Length(max=300)])
    description = TextAreaField('Описание курса')
    curator_id = SelectField('Куратор', coerce=int, validators=[Optional()])
    is_active = BooleanField('Активный курс', default=True)
    submit = SubmitField('Сохранить')


class UserCourseForm(FlaskForm):
    user_id = SelectField('Пользователь', coerce=int, validators=[DataRequired()])
    course_ids = SelectField('Курсы', coerce=int, choices=[], validators=[DataRequired()])
    submit = SubmitField('Предоставить доступ')


class CourseTaskForm(TaskForm):
    course_id = SelectField('Курс', coerce=int, validators=[DataRequired()])

class CourseLabForm(LabForm):
    course_id = SelectField('Курс', coerce=int, validators=[DataRequired()])


class CuratorProfileForm(FlaskForm):
    curator_name = StringField('Ваше имя', validators=[Optional(), Length(max=100)])
    curator_telegram = StringField('Telegram', validators=[Optional(), Length(max=100)])
    curator_email = StringField('Email', validators=[Optional(), Email(), Length(max=120)])
    submit = SubmitField('Сохранить')