from flask_wtf import FlaskForm
from wtforms import PasswordField, TextAreaField, StringField, SubmitField, SelectField, BooleanField
from wtforms.validators import DataRequired, Length


class RegistrationForm(FlaskForm):
    username = StringField('Логин', validators=[DataRequired(), Length(min=3, max=150)])
    password = PasswordField('Пароль', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('Зарегистрироваться')


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
    endpoint_suffix = StringField('Суффикс эндпоинта', validators=[Optional(), Length(max=100)])
    flag = StringField('Флаг', validators=[DataRequired(), Length(max=200)])
    flag_content = StringField('Содержимое флага', validators=[Optional(), Length(max=200)])
    type = SelectField('Тип', choices=[('SQL Injection', 'SQL Injection'), ('XSS', 'XSS'), ('Other', 'Другое')])
    handler_type = SelectField('Тип обработчика',
                               choices=[
                                   ('auth_bypass', 'Обход аутентификации'),
                                   ('union_injection', 'UNION инъекция'),
                                   ('blind_injection', 'Слепая инъекция'),
                                   ('static', 'Статический')
                               ])
    template_id = SelectField('Шаблон', coerce=int, validators=[Optional()])
    template_source = SelectField('Источник шаблона',
                                  choices=[
                                      ('', 'Без шаблона'),
                                      ('existing', 'Из базы данных'),
                                      ('file', 'Из файла')
                                  ],
                                  validators=[Optional()])
    template_file = SelectField('Файл шаблона', validators=[Optional()])
    submit = SubmitField('Сохранить')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from models import LabTemplate
        import os

        # Заполняем шаблоны из базы данных
        self.template_id.choices = [(0, '-- Без шаблона --')] + [
            (t.id, t.name) for t in LabTemplate.query.all()
        ]

        # Заполняем файлы шаблонов
        template_files = []
        template_dir = 'templates/labs'
        if os.path.exists(template_dir):
            for file in os.listdir(template_dir):
                if file.endswith('.html'):
                    template_files.append((file, file))

        self.template_file.choices = [('', '-- Выберите файл --')] + template_files


class LabHintForm(FlaskForm):
    hint_text = TextAreaField('Текст подсказки', validators=[DataRequired()])
    hint_order = StringField('Порядок отображения', default='0')
    submit = SubmitField('Сохранить')


class LabTemplateForm(FlaskForm):
    name = StringField('Название шаблона', validators=[DataRequired()])
    description = TextAreaField('Описание')
    template_type = SelectField('Тип шаблона',
                                choices=[
                                    ('auth_bypass', 'Обход аутентификации'),
                                    ('union_injection', 'UNION инъекция'),
                                    ('blind_injection', 'Слепая инъекция'),
                                    ('custom', 'Кастомный')
                                ])
    html_template = TextAreaField('HTML шаблон', validators=[DataRequired()])
    submit = SubmitField('Сохранить')


class LabInstructionForm(FlaskForm):
    instruction_type = SelectField('Тип инструкции',
        choices=[
            ('before_start', 'Перед началом работы'),
            ('after_solve', 'После решения'),
            ('flag_format', 'Формат флага'),
            ('flag_instruction', 'Инструкция по флагу')
        ],
        validators=[DataRequired()])
    content = TextAreaField('Содержание', validators=[DataRequired()])
    submit = SubmitField('Сохранить')