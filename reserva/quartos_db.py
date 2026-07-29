from db import db
from flask_login import UserMixin

class Quartos(db.Model, UserMixin):
    __tablename__ = 'quartos'

    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(), unique=True)
    tipo = db.Column(db.String())
    capacidade = db.Column(db.String())
    valor = db.Column(db.Float())
    status = db.Column(db.String())