from db import db
from datetime import date


class Reservas(db.Model):
    __tablename__ = 'reservas'

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    quarto_id = db.Column(db.Integer, db.ForeignKey('quartos.id'), nullable=False)
    data_entrada = db.Column(db.Date, nullable=False)
    data_saida = db.Column(db.Date, nullable=False)
    data_reserva = db.Column(db.Date, default=date.today)
    status = db.Column(db.String())