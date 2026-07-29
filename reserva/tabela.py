from db import db
from flask_login import UserMixin

class Usuarios(UserMixin, db.Model):
    __tablename__ = 'usuarios'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String())
    cpf = db.Column(db.String())
    email = db.Column(db.String(), unique=True)
    telefone = db.Column(db.String())
    senha = db.Column(db.String())
    administrador = db.Column(db.Boolean, default=False)