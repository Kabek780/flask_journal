from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField, FileField
from wtforms.validators import InputRequired, Length
from flask_wtf.file import FileAllowed

class ArticleForm(FlaskForm):
    title = StringField('Заголовок', validators=[InputRequired(), Length(min=5, max=200)])
    content = TextAreaField('Содержание', validators=[InputRequired()])
    image = FileField('Изображение (необязательно)', validators=[FileAllowed(['jpg', 'jpeg', 'png'], 'Только изображения!')])
    submit = SubmitField('Опубликовать')

class EditArticleForm(FlaskForm):
    title = StringField('Заголовок', validators=[InputRequired(), Length(min=5, max=200)])
    content = TextAreaField('Содержание', validators=[InputRequired()])
    image = FileField('Изображение (необязательно)', validators=[FileAllowed(['jpg', 'jpeg', 'png'], 'Только изображения!')])
    submit = SubmitField('Сохранить изменения')
