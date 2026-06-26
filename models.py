from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timedelta, timezone
from werkzeug.security import generate_password_hash, check_password_hash


def now_local():
    utc = datetime.now(timezone.utc)
    brasilia = utc - timedelta(hours=3)
    return brasilia.replace(tzinfo=None)


def hoje_inicio():
    agora = now_local()
    return datetime(agora.year, agora.month, agora.day)


def get_data_limite(dias):
    if dias == 0:
        return hoje_inicio()
    return now_local() - timedelta(days=dias)

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(80), nullable=False)
    senha_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='owner')
    criado_em = db.Column(db.DateTime, default=now_local)

    def set_password(self, password):
        self.senha_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.senha_hash, password)


class Categoria(db.Model):
    __tablename__ = 'categorias'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), nullable=False)
    ativo = db.Column(db.Boolean, default=True)
    abre = db.Column(db.String(5))  # HH:MM
    fecha = db.Column(db.String(5))  # HH:MM
    produtos = db.relationship('Produto', backref='categoria', lazy=True)


class Produto(db.Model):
    __tablename__ = 'produtos'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    preco = db.Column(db.Float, nullable=False)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categorias.id'))
    tipo = db.Column(db.String(20), nullable=False, default='espetinho')
    foto = db.Column(db.String(200))
    ativo = db.Column(db.Boolean, default=True)
    insumo_id = db.Column(db.Integer, db.ForeignKey('insumos.id'), nullable=True)
    qtd_insumo = db.Column(db.Float, default=1)
    insumo = db.relationship('Insumo', backref='produtos')
    produzido_cozinha = db.Column(db.Boolean, default=False)


class Mesa(db.Model):
    __tablename__ = 'mesas'
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.Integer, nullable=False, unique=True)
    ativo = db.Column(db.Boolean, default=True)
    pedidos = db.relationship('Pedido', backref='mesa', lazy=True)


class Pedido(db.Model):
    __tablename__ = 'pedidos'
    id = db.Column(db.Integer, primary_key=True)
    mesa_id = db.Column(db.Integer, db.ForeignKey('mesas.id'), nullable=True)
    cliente_nome = db.Column(db.String(100))
    tipo = db.Column(db.String(20), nullable=False, default='mesa')
    status = db.Column(db.String(20), nullable=False, default='em_preparo')
    total = db.Column(db.Float, default=0)
    forma_pagamento = db.Column(db.String(20))
    criado_em = db.Column(db.DateTime, default=now_local)
    pago_em = db.Column(db.DateTime)
    observacao = db.Column(db.Text)
    ultimo_preparo_em = db.Column(db.DateTime)
    itens = db.relationship('ItemPedido', backref='pedido', lazy=True, cascade='all, delete-orphan')
    pagamentos_parciais = db.relationship('PagamentoParcial', backref='pedido_pagamento', lazy=True, cascade='all, delete-orphan')


class ItemPedido(db.Model):
    __tablename__ = 'itens_pedido'
    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey('pedidos.id'), nullable=False)
    produto_id = db.Column(db.Integer, db.ForeignKey('produtos.id'), nullable=False)
    quantidade = db.Column(db.Integer, nullable=False, default=1)
    preco_unitario = db.Column(db.Float, nullable=False)
    observacao = db.Column(db.Text)
    criado_em = db.Column(db.DateTime, default=now_local)
    pronto = db.Column(db.Boolean, default=False)
    produto = db.relationship('Produto')


class CategoriaInsumo(db.Model):
    __tablename__ = 'categorias_insumo'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), nullable=False, unique=True)
    icone = db.Column(db.String(30), default='fa-box')

    def __repr__(self):
        return self.nome

CATEGORIAS_INSUMO_FIXAS = ['espetos', 'cervejas', 'destilados', 'sucos', 'refrigerantes', 'agua_mineral', 'acompanhamentos']

class Insumo(db.Model):
    __tablename__ = 'insumos'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    categoria = db.Column(db.String(30), nullable=False, default='espetos')
    quantidade = db.Column(db.Float, nullable=False, default=0)
    unidade = db.Column(db.String(20), nullable=False, default='un')
    quantidade_minima = db.Column(db.Float, default=0)
    preco_unitario = db.Column(db.Float, default=0)
    produzido_cozinha = db.Column(db.Boolean, default=False)
    movimentos = db.relationship('MovimentoEstoque', backref='insumo', lazy=True, cascade='all, delete-orphan')


class MovimentoEstoque(db.Model):
    __tablename__ = 'movimentos_estoque'
    id = db.Column(db.Integer, primary_key=True)
    insumo_id = db.Column(db.Integer, db.ForeignKey('insumos.id'), nullable=False)
    tipo = db.Column(db.String(10), nullable=False)
    quantidade = db.Column(db.Float, nullable=False)
    criado_em = db.Column(db.DateTime, default=now_local)
    observacao = db.Column(db.Text)


class Configuracao(db.Model):
    __tablename__ = 'configuracoes'
    id = db.Column(db.Integer, primary_key=True)
    chave = db.Column(db.String(50), nullable=False, unique=True)
    valor = db.Column(db.Text)


class CaixaRegistro(db.Model):
    __tablename__ = 'caixa'
    id = db.Column(db.Integer, primary_key=True)
    data_abertura = db.Column(db.DateTime, nullable=False, default=now_local)
    data_fechamento = db.Column(db.DateTime)
    saldo_inicial = db.Column(db.Float, default=0)
    saldo_final = db.Column(db.Float)
    status = db.Column(db.String(20), default='aberto')


DIAS_SEMANA = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado']

class CardapioAlmoco(db.Model):
    __tablename__ = 'cardapio_almoco'
    id = db.Column(db.Integer, primary_key=True)
    dia_semana = db.Column(db.Integer, nullable=False, unique=True)
    descricao = db.Column(db.Text)
    preco = db.Column(db.Float, default=0)
    ativo = db.Column(db.Boolean, default=True)


class AlmocoDia(db.Model):
    __tablename__ = 'almoco_dias'
    id = db.Column(db.Integer, primary_key=True)
    produto_id = db.Column(db.Integer, db.ForeignKey('produtos.id'), nullable=False)
    dia_semana = db.Column(db.Integer, nullable=False)
    produto = db.relationship('Produto', backref='almoco_dias')


class PagamentoParcial(db.Model):
    __tablename__ = 'pagamentos_parciais'
    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey('pedidos.id'), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    forma_pagamento = db.Column(db.String(20), nullable=False)
    criado_em = db.Column(db.DateTime, default=now_local)


CATEGORIAS_FINANCEIRO = [
    'aluguel', 'salarios', 'insumos', 'energia', 'agua',
    'internet', 'telefone', 'manutencao', 'marketing', 'impostos',
    'prolabore', 'equipamentos', 'transporte', 'outros'
]


class LancamentoFinanceiro(db.Model):
    __tablename__ = 'lancamentos_financeiro'
    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(200), nullable=False)
    tipo = db.Column(db.String(10), nullable=False)  # 'entrada' ou 'saida'
    valor = db.Column(db.Float, nullable=False)
    categoria = db.Column(db.String(50), nullable=False, default='outros')
    data_lancamento = db.Column(db.DateTime, nullable=False, default=now_local)
    observacao = db.Column(db.Text)
    criado_em = db.Column(db.DateTime, default=now_local)
    usuario_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    usuario = db.relationship('User', backref='lancamentos')


class FaturamentoMensal(db.Model):
    __tablename__ = 'faturamento_mensal'
    id = db.Column(db.Integer, primary_key=True)
    mes = db.Column(db.Integer, nullable=False)
    ano = db.Column(db.Integer, nullable=False)
    valor = db.Column(db.Float, nullable=False, default=0)
    atualizado_em = db.Column(db.DateTime, default=now_local, onupdate=now_local)


class Contrato(db.Model):
    __tablename__ = 'contratos'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False)
    valor_mensal = db.Column(db.Float, nullable=False, default=0)
    dia_vencimento = db.Column(db.Integer, nullable=False, default=5)
    ativo = db.Column(db.Boolean, default=True)
    observacao = db.Column(db.Text)
    criado_em = db.Column(db.DateTime, default=now_local)
    pagamentos = db.relationship('ContratoPagamento', backref='contrato', lazy=True, cascade='all, delete-orphan')


class ContratoPagamento(db.Model):
    __tablename__ = 'contrato_pagamentos'
    id = db.Column(db.Integer, primary_key=True)
    contrato_id = db.Column(db.Integer, db.ForeignKey('contratos.id'), nullable=False)
    mes = db.Column(db.Integer, nullable=False)
    ano = db.Column(db.Integer, nullable=False)
    valor_pago = db.Column(db.Float, nullable=False)
    pago_em = db.Column(db.DateTime, nullable=False, default=now_local)
    observacao = db.Column(db.Text)
