from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Length, EqualTo, ValidationError
from models.user import User

class RegisterForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[InputRequired(), Length(min=4, max=20)])
    password = PasswordField('Пароль', validators=[InputRequired(), Length(min=4, max=20), EqualTo('confirm', message='Пароли должны совпадать')])
    confirm = PasswordField('Подтвердите пароль')
    submit = SubmitField('Зарегистрироваться')

    def validate_username(self, username):
        existing_user = User.query.filter_by(username=username.data).first()
        if existing_user:
            raise ValidationError('Это имя пользователя уже занято.')
