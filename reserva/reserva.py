from flask import Flask, request, render_template, redirect, url_for
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from db import db
from tabela_token import Recuperecao
from tabela import Usuarios
from quartos_db import Quartos
from reservas_db import Reservas
from datetime import datetime, timedelta, date
import secrets
import smtplib
from email.message import Message
from decorators import admin_required
from logs import logger
import hashlib
import os


app = Flask(__name__)
app.secret_key = os.getenv("secret_key")
database_url = os.getenv("DATABASE_URL")

if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
else:
    database_url = "sqlite:///dados.db"

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
lm = LoginManager(app)
db.init_app(app)

with app.app_context():
    db.create_all()




def hash(txt):
    hash_obj = hashlib.sha256(txt.encode('utf-8'))
    return hash_obj.hexdigest()


@lm.user_loader
def user_loader(id):
    usuario = db.session.query(Usuarios).filter_by(id=id).first()
    return usuario

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    elif request.method == 'POST':
        email = request.form['emailForm']
        senha = request.form['senhaForm']

        user =  db.session.query(Usuarios).filter_by(email=email, senha=hash(senha)).first()
        if not user:
            logger.warning(
                f"Tentativa Invalida: \nEmail informado: {email} \nIP: {request.remote_addr}"
            )
            return render_template('login.html', falha='Email ou senha incorretos!')
        
        login_user(user)
        logger.info(
            f"Login Realizado \nEmail {current_user.email}\n"
            f"ID: {current_user.id} \nIP={request.remote_addr}\n"
        )
        return redirect(url_for('home'))

@app.route('/cadastrar', methods=['GET', 'POST'])
def cadastrar():
    if request.method == 'GET':
        return render_template('cadastrar.html')
    elif request.method == 'POST':
        nome = request.form['nomeForm']
        cpf = request.form['cpfForm']
        email = request.form['emailForm']
        telefone = request.form['telefoneForm']
        senha = request.form['senhaForm']
        
        email_exist = db.session.query(Usuarios).filter_by(email=email).first()

        if email_exist:
            logger.warning(
            f"Tentativa de cadastro de email ja existente: {email}"
            )
            return render_template('cadastrar.html', erro='Email ja existente!')
        else:
            novo_usuario = Usuarios(nome=nome, cpf=cpf, email=email, telefone=telefone, senha=hash(senha))
            db.session.add(novo_usuario)
            db.session.commit()
            login_user(novo_usuario)
            
            logger.info(
                f"Novo usuario cadastrado. \nNome: {novo_usuario.id} \nIP: {request.remote_addr}"
            )

        return redirect(url_for('login'))
    
@app.route('/redefinir', methods=['GET', 'POST'])
def redefinir():
    if request.method == 'GET':
        return render_template('redefinir.html')

    elif request.method == 'POST':
        email = request.form['emailredef']

        logger.info(
            f'Pedido de redefinição de senha\n'
            f'Email: {email}'
        )

        usuario = Usuarios.query.filter_by(email=email).first()

        if not usuario:
            logger.warning(
                f'O email {email} não existe.'
            )

            return render_template('redefinir.html', erro='Erro. O email não está cadastrado.')

        token = secrets.token_urlsafe(32)
        expiracao = datetime.now() + timedelta(minutes=5)

        registro = Recuperecao(
            usuario_id=usuario.id,
            token=token,
            expiracao=expiracao
        )

        db.session.add(registro)
        db.session.commit()

        link = url_for(
            'redefinirsenha',
            token=token,
            _external=True
        )

        corpo_email = f"""
        <html>
        <body>
            <h2>Recuperação de senha</h2>

            <p>Clique no link abaixo para redefinir sua senha:</p>

            <p>
                <a href="{link}">
                    {link}
                </a>
            </p>

            <p>Se você não solicitou esta alteração, ignore este e-mail.</p>
        </body>
        </html>
        """

        msg = Message()
        msg['Subject'] = 'Redefinir senha'
        msg['From'] = os.getenv("EMAIL")
        msg['To'] = usuario.email

        password = os.getenv("PASSWORD")

        msg.add_header('Content-Type', 'text/html; charset=utf-8')
        msg.set_payload(corpo_email)

        try:
            servidor = smtplib.SMTP("smtp.gmail.com", 587, timeout=20)

            servidor.ehlo()
            servidor.starttls()
            servidor.ehlo()

            servidor.login(msg['From'], password)

            servidor.sendmail(
                msg['From'],
                msg['To'],
                msg.as_string().encode('utf-8')
            )

            servidor.quit()

            logger.info(
                f'O token foi enviado para {usuario.email}'
            )

            return render_template(
                'redefinir.html',
                sucesso='Email enviado com sucesso!'
            )

        except Exception as e:
            logger.error(
                f'Erro ao enviar o email: {e}'
            )

            return render_template(
                'redefinir.html',
                erro='Erro ao enviar o email.'
            )
        
@app.route("/redefinir/<token>", methods=['GET', 'POST'])
def redefinirsenha(token):
    try:
        registro = Recuperecao.query.filter_by(token=token).first()
        if not registro:
            logger.warning(
                'Token Invalido'
            )
            return render_template('redefinir.html', erro = 'Token Invalido')
        
        usuario = Usuarios.query.get(registro.usuario_id)
        
        if datetime.now() > registro.expiracao:
            logger.error(
                f"O token enviado para {usuario.email} foi expirado"
            )
            db.session.delete(registro)
            db.session.commit()
            logger.info(
                "token deletado"
            )
            return render_template('redefinir.html', erro = 'Token expirado')
        
        if request.method == 'GET':
            return render_template('redefinirsenha.html')
        elif request.method == 'POST':
            nova_senha = request.form['senhaRedef']
            nova_senha2 = request.form['senhaConf']

            if nova_senha != nova_senha2:
                logger.error(
                    f"Usuario {usuario.email} digitou senhas diferentes"
                )
                return render_template('redefinirsenha.html', erro ='As senhas nao coincidem!')
            
            usuario.senha = hash(nova_senha)
            db.session.delete(registro)
            db.session.commit()
            logger.info(
                "token deletado"
            )

            login_user(usuario)
            return redirect(url_for('login'))
    except Exception as e:
        logger.error(
            f"erro {e}"
        )
        return render_template('redefinirsenha.html', erro = 'erro ao redefinir senha!')
    
@app.route('/home', methods=['GET', 'POST'])
@login_required
def home():
    

    if request.method == 'GET':
        erro = request.args.get('erro')
        logger.info(
            f"Usuário {current_user.id} acessou a página inicial."
        )
        return render_template('home.html', pesquisa=False, erro=erro)

    elif request.method == 'POST':

        entrada = datetime.strptime(request.form['entrada'],"%Y-%m-%d").date()
        saida = datetime.strptime(request.form['saida'],"%Y-%m-%d").date()

        logger.info(
            f"Usuário {current_user.id} pesquisou quartos de {entrada} até {saida}.")

        if entrada >= saida:
            logger.warning(
                f"Usuário {current_user.id} informou entrada ({entrada}) maior ou igual à saída ({saida})."
            )
            return render_template("home.html", erro = 'A data de entrada deve ser anterior à data de saída.')
        if entrada < date.today():
            logger.warning(
                f"Usuário {current_user.id} tentou pesquisar utilizando uma data passada ({entrada})."
            )
            return render_template("home.html", erro = 'A data de entrada não pode ser anterior à data atual.')


        quartos_disponiveis = []

        for quarto in db.session.query(Quartos).filter_by(status='Disponivel'):

            conflito = False
            reservas = db.session.query(Reservas).filter_by(quarto_id=quarto.id).all()

            logger.debug(
                f"Quarto {quarto.numero}: {len(reservas)} reservas encontradas."
            )

            for reserva in reservas:
                if entrada < reserva.data_saida and saida > reserva.data_entrada:
                    conflito = True

                    logger.debug(
                        f"Conflito encontrado no quarto {quarto.numero} "
                        f"(reserva {reserva.id})."
                    )
                    
            if not conflito:
                quartos_disponiveis.append(quarto)

                

    return render_template('home.html', quarto=quartos_disponiveis, entrada=entrada, saida=saida, pesquisa=True)

@app.route('/confirmar', methods=['GET','POST'])
def confirmar():
    if request.method == 'GET':
        return redirect(url_for('home'))
    elif request.method == 'POST':

        quarto_id = request.form['quarto_id']
        entrada = datetime.strptime(request.form['entrada'], "%Y-%m-%d").date()
        saida = datetime.strptime(request.form['saida'], "%Y-%m-%d").date()

        
        quarto = db.session.get(Quartos, int(quarto_id))
        dias = (saida - entrada).days
        valor_total = dias*quarto.valor
        logger.info(
            f"Reserva Selecionada\n"
            f"ID: {current_user.id} \nEmail: {current_user.email}\n"
            f"IP: {request.remote_addr}\n"
            f"Quarto numero: {quarto.numero}"
            f"Periodo: {entrada} até {saida}"
        )   

        return render_template('/confirmacao.html', quarto=quarto, entrada=entrada, saida=saida, usuario=current_user, valor_total=valor_total)

@app.route('/reservar', methods=['GET', 'POST'])
def reservar():
    if request.method == 'POST':
        quarto_id = request.form['quarto_id']
        entrada = datetime.strptime(request.form['entrada'], "%Y-%m-%d").date()
        saida = datetime.strptime(request.form['saida'], "%Y-%m-%d").date()
        quarto = db.session.get(Quartos, int(quarto_id))
        

        conflito = Reservas.query.filter(
            Reservas.quarto_id == quarto_id,
            Reservas.data_entrada < saida,
            Reservas.data_saida > entrada
        ).first()

        if conflito:
            return redirect(url_for('home', erro = "Este quarto acabou de ser reservado por outro cliente. Faça uma nova pesquisa."))
        
        nova_reserva = Reservas(usuario_id=current_user.id, quarto_id=quarto_id, data_entrada=entrada, data_saida=saida)
        db.session.add(nova_reserva)
        db.session.commit()
        logger.info(
            f"Quarto Reservado com Sucesso\n"
            f"ID: {current_user.id} \nEmail: ({current_user.email})\n"
            f"Numero do Quarto: {quarto.numero} \nEntrada: {entrada} \nSaida: {saida}\n"
            f"IP: {request.remote_addr}\n"
        )

        return redirect(url_for('minhas_reservas'))
    elif request.method == 'GET':
        return render_template('home.html')

@app.route('/minhas_reservas')
@login_required
def minhas_reservas():

    logger.info(
    f"Usuário {current_user.id} acessou a página de reservas.")

    reservas = Reservas.query.filter_by(usuario_id=current_user.id).all()
    logger.info(
        f"Usuário {current_user.id} possui {len(reservas)} reserva(s).")
    
    dados = []
    for reserva in reservas:
        quarto = db.session.get(Quartos, reserva.quarto_id)
        dados.append({
            "reserva": reserva,
            "quarto": quarto
        })

    return render_template('minhas_reservas.html', dados=dados)

@app.route('/cancelar_reserva/<int:id>', methods=['POST'])
@login_required
def cancelar_reserva(id):

    
    reserva = Reservas.query.get_or_404(id)

    if reserva.usuario_id != current_user.id:
        logger.warning(
            f"Usuário {current_user.id} tentou cancelar "
            f"a reserva {reserva.id} pertencente ao usuário "
            f"{reserva.usuario_id}.")
        return redirect(url_for("minhas_reservas")) 
    
    db.session.delete(reserva)
    db.session.commit()
    logger.info(
        f"Reserva cancelada\n"
        f"Reserva={reserva.id}\n "
        f"Usuário={current_user.id}\n "
        f"Quarto={reserva.quarto_id}\n "
        f"Entrada={reserva.data_entrada}\n"
        f"Saída={reserva.data_saida}\n "
        f"IP={request.remote_addr}\n")

    return redirect(url_for('minhas_reservas'))

@app.route('/quartos')
@login_required
@admin_required
def lista_quartos():
    quartos = db.session.query(Quartos).all()

    return render_template('lista_quartos.html', quartos=quartos)

@app.route('/quartos/adicionar', methods=['GET', 'POST'])
@login_required
@admin_required
def adicionar_quarto():
    if request.method == 'GET':
        return render_template('adicionar_quarto.html', quarto=None, titulo='Adicionar Quarto', funcao='adicionar')
    elif request.method == 'POST':
        numero = request.form['numero']
        tipo = request.form['tipo']
        capacidade = request.form['capacidade']
        valor = request.form['valor']
        status = request.form['status']
        quarto_exist = db.session.query(Quartos).filter_by(numero=numero).first()

        if quarto_exist:
            return render_template('adicionar_quarto.html', titulo='Adicionar Quarto', funcao='Adicionar', quarto=None, erro='Já existe um quarto com esse número.')
        
        novo_quarto = Quartos(numero=numero, tipo=tipo, capacidade=capacidade, valor=valor, status=status)
        db.session.add(novo_quarto)
        db.session.commit()
        logger.info(
            f"Quarto adicionado\n"
            f"Administrador={current_user.id}\n"
            f"Número={numero}\n"
            f"Tipo={tipo}\n"
            f"Status={status}\n"
            f"IP={request.remote_addr}\n"
        )

        return redirect(url_for('lista_quartos'))
    
@app.route('/quartos/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def editar_quarto(id):
    quarto = Quartos.query.get_or_404(id)

    if request.method == 'GET':
        logger.info(
            f"Administrador={current_user.id}\n"
            f"Email={current_user.email}\n"
            f"IP={request.remote_addr}\n "
            f"Acessou edição do quarto {quarto.numero}\n"
        )
        return render_template('adicionar_quarto.html', quarto=quarto, titulo='Editar Quarto', funcao='editar')
    
    elif request.method == 'POST':
        quarto_exist = db.session.query(Quartos).filter_by(numero=request.form['numero']).first()

        if quarto_exist and quarto_exist.id != quarto.id:

            logger.warning(
                f"Administrador={current_user.id}\n"
                f"Email={current_user.email}\n"
                f"IP={request.remote_addr}\n"
                f"Tentou alterar o quarto {quarto.numero} "
                f"para o número {request.form['numero']}, "
                f"mas esse número já está cadastrado.\n"
            )

            return render_template(
                'adicionar_quarto.html',
                quarto=quarto,
                titulo='Editar Quarto',
                funcao='Editar',
                erro='Já existe um quarto com esse número.'
            )

        numero_antigo = quarto.numero
        tipo_antigo = quarto.tipo
        capacidade_antiga = quarto.capacidade
        valor_antigo = quarto.valor
        status_antigo = quarto.status

        quarto.numero = request.form['numero']
        quarto.tipo = request.form['tipo']
        quarto.capacidade = request.form['capacidade']
        quarto.valor = request.form['valor']
        quarto.status = request.form['status']

        try:
            db.session.commit()

            logger.info(
                f"Quarto editado\n "
                f"Administrador={current_user.id}\n"
                f"Quarto={numero_antigo} - {quarto.numero}\n"
                f"Tipo={tipo_antigo} - {quarto.tipo}\n"
                f"Capacidade={capacidade_antiga} - {quarto.capacidade}\n"
                f"Valor=R$ {valor_antigo} - R$ {quarto.valor}\n"
                f"Status={status_antigo} - {quarto.status}\n"
                )


            return redirect(url_for('lista_quartos'))
        except Exception as e:
            db.session.rollback()
            logger.error(
                f'Erro ao editar o quarto {quarto.numero}: {e}'
            )
    
@app.route('/quartos/excluir/<int:id>', methods=['POST'])
@login_required
@admin_required
def excluir_quarto(id):

    quarto = Quartos.query.get_or_404(id)
    logger.info(
        f"Soliciatação de exclusão de quarto\n"
        f"Administrador: {current_user.id}\n"
        f"Email: {current_user.email}\n"
        f"IP: {request.remote_addr}\n"
    )

    numero = quarto.numero
    tipo = quarto.tipo
    capacidade = quarto.capacidade
    valor = quarto.valor
    status = quarto.status

    logger.info(
        f"Quarto excluído\n"
        f"Administrador={current_user.id}\n"
        f"Número={numero}\n"
        f"Tipo={tipo}\n"
        f"Capacidade={capacidade}\n"
        f"Valor=R$ {valor}\n"
        f"Status={status}\n"
        )
    db.session.delete(quarto)
    db.session.commit()

    return redirect(url_for('lista_quartos'))


@app.route('/logout')
@login_required
def logout():
    logger.info(
        f"Logout: \nID: {current_user.id} \nIP: {request.remote_addr}\n"
    )
    logout_user()
    return redirect(url_for('login'))



if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
