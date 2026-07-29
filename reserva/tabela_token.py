from db import db
from flask_login import UserMixin

class Recuperecao(UserMixin, db.Model):
    __tablename__ = 'recuperacao'
    
    id=db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    token = db.Column(db.String(200))
    expiracao = db.Column(db.DateTime)