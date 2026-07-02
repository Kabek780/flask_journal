from extensions import db
from datetime import datetime

class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    image_paths = db.Column(db.String(255))
    author = db.relationship('User', backref=db.backref('articles', lazy=True))

class ArticleView(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    article_id = db.Column(db.Integer, db.ForeignKey('article.id'), nullable=False)
    viewed_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('article_views', lazy=True))
    article = db.relationship(
    'Article',
    backref=db.backref('article_view_entries', lazy=True, cascade="all, delete-orphan")
)
