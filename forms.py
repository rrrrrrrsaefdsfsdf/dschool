from flask_wtf import FlaskForm
from wtforms import PasswordField, TextAreaField, StringField, SubmitField, SelectField, BooleanField
from wtforms.validators import DataRequired, Length


class RegistrationForm(FlaskForm):
    username = StringField('Логин', validators=[DataRequired(), Length(min=3, max=150)])
    password = PasswordField('Пароль', validators=[DataRequired(), Length(min=6)])
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


from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length, Optional


class LabForm(FlaskForm):
    title = StringField('Название лабы', validators=[DataRequired(), Length(max=300)])
    description = TextAreaField('Описание', validators=[DataRequired()])
    difficulty = SelectField('Сложность', choices=[('Легко', 'Легко'), ('Средне', 'Средне'), ('Сложно', 'Сложно')])
    endpoint = StringField('Эндпоинт', validators=[DataRequired(), Length(max=100)])
    flag = StringField('Флаг', validators=[DataRequired(), Length(max=200)])
    flag_content = StringField('Содержимое флага', validators=[Optional(), Length(max=200)])
    submit = SubmitField('Сохранить')
