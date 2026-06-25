import os
import sys
import traceback
import json
import tempfile
from flask import Flask, jsonify
from flask_login import LoginManager
from models import db, User, Produto, Pedido, PagamentoParcial

app = Flask(__name__)

database_available = False

if os.environ.get('VERCEL'):
    app.instance_path = '/tmp/instance'

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'espetinho-junco-secret-key-2024')

database_url = os.environ.get('DATABASE_URL')
if database_url and database_url.startswith('postgresql://'):
    try:
        import pg8000
        database_url = database_url.replace('postgresql://', 'postgresql+pg8000://', 1)
        from urllib.parse import urlparse, urlencode, parse_qs

        parsed = urlparse(database_url)
        qs = parse_qs(parsed.query)
        qs.pop('sslmode', None)
        qs.pop('pgbouncer', None)
        clean_query = urlencode(qs, doseq=True)
        database_url = database_url.replace(parsed.query, clean_query)
    except ImportError:
        pass
if not database_url:
    if os.environ.get('VERCEL'):
        tmp_dir = tempfile.gettempdir()
        db_path = os.path.join(tmp_dir, 'espetinho.db')
        database_url = f'sqlite:///{db_path}'
    else:
        database_url = 'sqlite:///espetinho.db'

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
}

db.init_app(app)

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Faça login para acessar o sistema'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    if not database_available:
        return None
    return User.query.get(int(user_id))

@app.route('/debug')
def debug():
    raw_url = app.config['SQLALCHEMY_DATABASE_URI']
    masked = raw_url
    if '@' in raw_url:
        parts = raw_url.split('@')
        creds = parts[0].split('://')[1] if '://' in parts[0] else parts[0]
        masked = raw_url.replace(creds, '***:***')
    info = {
        'database_url': masked,
        'has_vercel_env': bool(os.environ.get('VERCEL')),
        'has_database_url_env': bool(os.environ.get('DATABASE_URL')),
        'database_available': database_available,
    }
    if database_available:
        try:
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            info['tables'] = tables
            info['user_count'] = User.query.count()
        except Exception as e:
            info['tables_error'] = str(e)
    return jsonify(info)

from routes.auth import bp as auth_bp
from routes.dashboard import bp as dashboard_bp
from routes.cardapio import bp as cardapio_bp
from routes.pedidos import bp as pedidos_bp
from routes.caixa import bp as caixa_bp
from routes.estoque import bp as estoque_bp
from routes.relatorios import bp as relatorios_bp
from routes.configuracoes import bp as config_bp
from routes.delivery import bp as delivery_bp
from routes.almoco import bp as almoco_bp
from routes.financeiro import bp as financeiro_bp
from routes.contratos import bp as contratos_bp

app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(cardapio_bp)
app.register_blueprint(pedidos_bp)
app.register_blueprint(caixa_bp)
app.register_blueprint(estoque_bp)
app.register_blueprint(relatorios_bp)
app.register_blueprint(config_bp)
app.register_blueprint(delivery_bp)
app.register_blueprint(almoco_bp)
app.register_blueprint(financeiro_bp)
app.register_blueprint(contratos_bp)

def _from_json(s):
    if s and isinstance(s, str):
        try:
            return json.loads(s)
        except (json.JSONDecodeError, TypeError):
            pass
    return {}

app.jinja_env.filters['from_json'] = _from_json

def _fmt_forma_pagamento(forma):
    mapa = {'dinheiro': 'Dinheiro', 'especie': 'Dinheiro', 'pix': 'PIX', 'cartao': 'Cartão', 'cartão': 'Cartão', 'multi': 'Múltiplo'}
    return mapa.get(forma, forma.capitalize() if forma else '')

app.jinja_env.filters['fmt_pagamento'] = _fmt_forma_pagamento

def _fmt_brl(valor):
    try:
        return f'{valor:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    except (ValueError, TypeError):
        return '0,00'

app.jinja_env.filters['brl'] = _fmt_brl

def _total_parcial(pedido):
    return sum(pp.valor for pp in (pedido.pagamentos_parciais or []))

def _restante(pedido):
    return (pedido.total or 0) - _total_parcial(pedido)

app.jinja_env.filters['total_parcial'] = _total_parcial
app.jinja_env.filters['restante'] = _restante

with app.app_context():
    try:
        db.create_all()

        try:
            db.session.execute(db.text('ALTER TABLE cardapio_almoco ADD COLUMN preco FLOAT DEFAULT 0'))
            db.session.commit()
        except Exception:
            db.session.rollback()

        try:
            db.session.execute(db.text('ALTER TABLE pedidos ADD COLUMN pago_em TIMESTAMP'))
            db.session.commit()
        except Exception:
            db.session.rollback()

        try:
            db.session.execute(db.text('ALTER TABLE pedidos ADD COLUMN ultimo_preparo_em TIMESTAMP'))
            db.session.commit()
        except Exception:
            db.session.rollback()

        try:
            db.session.execute(db.text('ALTER TABLE itens_pedido ADD COLUMN preco_unitario FLOAT'))
            db.session.commit()
        except Exception:
            db.session.rollback()

        try:
            db.session.execute(db.text('ALTER TABLE itens_pedido ADD COLUMN quantidade INTEGER DEFAULT 1'))
            db.session.commit()
        except Exception:
            db.session.rollback()

        try:
            db.session.execute(db.text('ALTER TABLE itens_pedido ADD COLUMN criado_em TIMESTAMP'))
            db.session.commit()
        except Exception:
            db.session.rollback()

        try:
            db.session.execute(db.text('ALTER TABLE itens_pedido ADD COLUMN pronto BOOLEAN DEFAULT FALSE'))
            db.session.commit()
        except Exception:
            db.session.rollback()

        try:
            db.session.execute(db.text("ALTER TABLE cardapio_almoco ADD COLUMN ativo BOOLEAN DEFAULT TRUE"))
            db.session.commit()
        except Exception:
            db.session.rollback()

        try:
            db.session.execute(db.text("ALTER TABLE categorias ADD COLUMN abre VARCHAR(5)"))
            db.session.commit()
        except Exception:
            db.session.rollback()

        try:
            db.session.execute(db.text("ALTER TABLE categorias ADD COLUMN fecha VARCHAR(5)"))
            db.session.commit()
        except Exception:
            db.session.rollback()

        try:
            db.session.execute(db.text("ALTER TABLE configuracoes ALTER COLUMN valor TYPE TEXT"))
            db.session.commit()
        except Exception:
            db.session.rollback()

        try:
            db.session.execute(db.text("ALTER TABLE insumos ADD COLUMN produzido_cozinha BOOLEAN DEFAULT FALSE"))
            db.session.commit()
        except Exception:
            db.session.rollback()

        try:
            db.session.execute(db.text("ALTER TABLE produtos ADD COLUMN produzido_cozinha BOOLEAN DEFAULT FALSE"))
            db.session.commit()
        except Exception:
            db.session.rollback()

        produtos_cozinha = Produto.query.filter(
            Produto.produzido_cozinha == False,
            db.or_(
                Produto.tipo.in_(['espetinho', 'acompanhamento', 'almoco']),
                Produto.nome == 'Almoço do Dia',
            )
        ).all()
        for p in produtos_cozinha:
            p.produzido_cozinha = True
        if produtos_cozinha:
            db.session.commit()
            print(f'  + {len(produtos_cozinha)} produtos marcados como cozinha', file=sys.stderr)

        if User.query.count() == 0:
            admin = User(nome='admin', role='owner')
            admin.set_password('admin')
            db.session.add(admin)

            bela = User(nome='bela', role='owner')
            bela.set_password('123456')
            db.session.add(bela)

            db.session.commit()

        # Backfill PagamentoParcial for existing paid orders
        try:
            pedidos_sem_parcial = Pedido.query.filter(
                Pedido.status == 'pago',
                ~Pedido.pagamentos_parciais.any()
            ).all()
            for p in pedidos_sem_parcial:
                pp = PagamentoParcial(
                    pedido_id=p.id,
                    valor=p.total or 0,
                    forma_pagamento=p.forma_pagamento or 'dinheiro',
                    criado_em=p.pago_em or p.criado_em
                )
                db.session.add(pp)
            if pedidos_sem_parcial:
                db.session.commit()
                print(f'  + {len(pedidos_sem_parcial)} pagamentos retroativos criados', file=sys.stderr)
        except Exception:
            db.session.rollback()

        database_available = True
        print("Banco de dados configurado com sucesso!", file=sys.stderr)
    except Exception as e:
        print(f"AVISO: Banco de dados indisponivel - {e}", file=sys.stderr)
        print("O app iniciara em modo limitado (sem persistencia)", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
