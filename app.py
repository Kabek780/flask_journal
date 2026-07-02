from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from extensions import db
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Length, EqualTo, ValidationError
from models.user import User
from forms.auth import RegisterForm
from flask_migrate import Migrate
from models.article import Article
from forms.article import ArticleForm, EditArticleForm
import os
from werkzeug.utils import secure_filename
import docx
from models.user import VisitLog
from collections import defaultdict
from datetime import datetime, timedelta
import numpy as np
from models.article import ArticleView 

app = Flask(__name__)
app.config.from_object('config.Config')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///journal.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads/'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db.init_app(app)
migrate = Migrate(app, db)

login_manager = LoginManager(app)
login_manager.login_view = 'login'

class RegisterForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[InputRequired(), Length(min=4, max=20)])
    password = PasswordField('Пароль', validators=[InputRequired(), Length(min=4, max=20), EqualTo('confirm', message='Пароли должны совпадать')])
    confirm = PasswordField('Подтвердите пароль')
    submit = SubmitField('Зарегистрироваться')
    def validate_username(self, username):
        existing_user = User.query.filter_by(username=username.data).first()
        if existing_user:
            raise ValidationError('Это имя пользователя уже занято.')

class LoginForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[InputRequired(), Length(min=4, max=20)])
    password = PasswordField('Пароль', validators=[InputRequired(), Length(min=4, max=20)])
    submit = SubmitField('Войти')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- МАРШРУТЫ ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data, method='pbkdf2:sha256')
        new_user = User(username=form.username.data, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash('Регистрация прошла успешно!', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            return redirect(url_for('index'))
        flash('Неверное имя пользователя или пароль', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/create', methods=['GET', 'POST'])
@login_required
def create_article():
    form = ArticleForm()
    content_text = ""  # Переменная для текста из Word
    image_paths = None  # По умолчанию без картинки

    if form.validate_on_submit():
        # Если загружен Word-файл, заполняем content текстом из Word
        if 'word_file' in request.files:
            word_file = request.files['word_file']
            if word_file.filename.endswith('.docx'):  # Если это .docx
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(word_file.filename))
                word_file.save(filepath)

                # Извлекаем текст из Word
                doc = docx.Document(filepath)
                content_text = "\n".join([p.text for p in doc.paragraphs])

        # Проверяем загрузку изображения
        if 'image' in request.files:
            file = request.files['image']
            if file.filename:  # Если файл выбран
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_paths = f'uploads/{filename}'  # Сохраняем ПРАВИЛЬНЫЙ путь

        # Создаём статью с текстом из Word или из формы
        article = Article(
            title=form.title.data,
            content=content_text if content_text else form.content.data,  # Используем текст из Word, если он есть
            image_paths=image_paths,  # Путь к изображению, если есть
            author_id=current_user.id
        )

        db.session.add(article)
        db.session.commit()
        flash('Статья успешно создана!', 'success')
        return redirect(url_for('index'))

    return render_template('create_article.html', form=form)

@app.route('/edit/<int:article_id>', methods=['GET', 'POST'])
@login_required
def edit_article(article_id):
    article = Article.query.get_or_404(article_id)

    # Проверяем, является ли текущий пользователь автором статьи
    if article.author_id != current_user.id:
        flash('Вы не можете редактировать чужую статью!', 'danger')
        return redirect(url_for('index'))

    form = EditArticleForm(obj=article)

    if form.validate_on_submit():
        article.title = form.title.data
        article.content = form.content.data  # Оставляем старый текст по умолчанию

        # Обрабатываем загрузку Word-файла
        if 'word_file' in request.files:
            word_file = request.files['word_file']
            if word_file.filename.endswith('.docx'):  # Проверяем формат
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(word_file.filename))
                word_file.save(filepath)  # Сохраняем файл

                # Читаем текст из Word и заменяем старый текст статьи
                doc = docx.Document(filepath)
                article.content = "\n".join([p.text for p in doc.paragraphs])

        # Если загружено новое изображение
        if 'image' in request.files:
            file = request.files['image']
            if file.filename:
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                article.image_paths = f'uploads/{filename}'  # Перезаписываем путь

        db.session.commit()
        flash('Статья успешно обновлена!', 'success')
        return redirect(url_for('view_article', article_id=article.id))

    return render_template('edit_article.html', form=form, article=article)

@app.route('/article/<int:article_id>')
@login_required
def view_article(article_id):
    article = Article.query.get_or_404(article_id)

    # Проверяем, открывал ли пользователь уже эту статью
    existing_view = ArticleView.query.filter_by(user_id=current_user.id, article_id=article.id).first()

    if not existing_view:  # Если это первый просмотр
        if current_user.balance >= 100:
            current_user.balance -= 100  # Списываем 100р
            db.session.add(ArticleView(user_id=current_user.id, article_id=article.id))  # Записываем факт просмотра
            db.session.commit()
            flash("", "info")
        else:
            flash("У вас недостаточно средств для просмотра статьи!", "danger")
            return redirect(url_for('index'))


    return render_template('view_article.html', article=article)


@app.route('/delete_article/<int:article_id>', methods=['POST'])
@login_required
def delete_article(article_id):
    article = Article.query.get_or_404(article_id)

    if article.author_id != current_user.id and not current_user.is_admin:
        flash('Вы не можете удалить чужую статью!', 'danger')
        return redirect(url_for('index'))

    # Удаляем все записи о просмотрах этой статьи
    ArticleView.query.filter_by(article_id=article.id).delete()

    # Теперь удаляем саму статью
    db.session.delete(article)
    db.session.commit()

    flash('Статья успешно удалена!', 'success')
    return redirect(url_for('index'))


@app.route('/upload_image', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        return {"success": False, "error": "Файл не найден"}

    file = request.files['image']
    if file.filename == '':
        return {"success": False, "error": "Файл не выбран"}

    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        return {"success": True, "url": url_for('static', filename=f'uploads/{filename}')}
    return {"success": False, "error": "Ошибка загрузки"}


@app.route('/upload_word', methods=['POST'])
@login_required
def upload_word():
    if 'word_file' not in request.files:
        return jsonify({"success": False, "error": "Файл не найден!"})

    file = request.files['word_file']
    if not file.filename.endswith('.docx'):
        return jsonify({"success": False, "error": "Неверный формат файла!"})

    # Сохраняем временно и читаем текст
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file.filename))
    file.save(filepath)

    doc = docx.Document(filepath)
    text = "\n".join([p.text for p in doc.paragraphs])  # Соединяем абзацы

    return jsonify({"success": True, "text": text})

@app.before_request
def log_visit():
    """Записываем посещение страницы в БД"""
    if request.endpoint and request.endpoint not in ['static']:  # Игнорируем статику
        visit = VisitLog(
            user_id=current_user.id if current_user.is_authenticated else None,
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string
        )
        db.session.add(visit)
        db.session.commit()

@app.route('/admin/visits')
@login_required
def admin_visits():
    if not current_user.is_admin:
        flash("У вас нет доступа!", "danger")
        return redirect(url_for('index'))

    visits = VisitLog.query.order_by(VisitLog.timestamp.desc()).all()

    # Группируем посещения по дням
    visit_counts = defaultdict(int)
    for visit in visits:
        date_str = visit.timestamp.strftime('%Y-%m-%d')  # Дата в формате "ГГГГ-ММ-ДД"
        visit_counts[date_str] += 1

    # Сортируем даты
    dates = sorted(visit_counts.keys())  
    counts = [visit_counts[date] for date in dates]  

    # === Прогнозируем посещаемость ===
    future_dates = [(datetime.strptime(dates[-1], "%Y-%m-%d") + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(1, 8)]
    future_counts = [max(0, int(np.mean(counts))) if counts else 0] * 7  # Если мало данных, берём среднее

    if len(counts) > 3:  # Если есть данные для тренда
        x = np.arange(len(counts))  # Дни в числах
        y = np.array(counts)  # Количество посещений

        coef = np.polyfit(x, y, 1)  # Линейная регрессия
        trend = np.poly1d(coef)
        avg_last_days = np.mean(counts[-3:])  # Среднее за 3 дня

        for i in range(7):
            prediction = int(trend(len(counts) + i))
            if prediction < 0:
                prediction = int(avg_last_days * 0.8)  # Плавное снижение
            future_counts[i] = max(0, prediction)  # Не даём опуститься ниже 0

    return render_template('admin_visits.html', 
                           visits=visits, 
                           dates=dates, counts=counts,
                           future_dates=future_dates, future_counts=future_counts)


@app.route('/user/<int:user_id>')
@login_required
def user_profile(user_id):
    user = User.query.get_or_404(user_id)
    return render_template('user_profile.html', user=user)

@app.route('/buy', methods=['POST'])
@login_required
def buy():
    if current_user.balance is None:
        current_user.balance = 0  # Если баланс пустой, устанавливаем 0

    current_user.balance += 1000  # Добавляем 1000р
    db.session.commit()
    flash("", "success")
    return redirect(url_for('index'))

@app.route('/search', methods=['GET'])
@login_required
def search():
    query = request.args.get('q', '').strip()  # Получаем поисковый запрос
    if query:
        articles = Article.query.filter(Article.title.ilike(f"%{query}%") | Article.content.ilike(f"%{query}%")).all()
    else:
        articles = []

    return render_template('search_results.html', articles=articles, query=query)



@app.route('/')
def index():
    articles = Article.query.order_by(Article.created_at.desc()).all()
    return render_template('index.html', articles=articles)

if __name__ == '__main__':
    app.run(debug=True) 
