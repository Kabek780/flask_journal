from extensions import db
from flask_login import UserMixin
from datetime import datetime

class User(UserMixin, db.Model):
    __tablename__ = 'user'  
    __table_args__ = {'extend_existing': True} 

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(150), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    balance = db.Column(db.Integer, default=0)

class VisitLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Может быть аноним
    ip_address = db.Column(db.String(100), nullable=False)
    user_agent = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('visits', lazy=True))

