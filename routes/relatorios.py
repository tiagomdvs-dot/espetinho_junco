from flask import Blueprint, render_template, request, jsonify, Response
from flask_login import login_required
from models import db, Pedido, ItemPedido, Produto, PagamentoParcial, now_local
from datetime import datetime, timedelta
from sqlalchemy import func, or_, and_
from utils import exportar_relatorio_csv

bp = Blueprint('relatorios', __name__, url_prefix='/relatorios')


def parse_datas():
    data_inicial = request.args.get('data_inicial', '')
    data_final = request.args.get('data_final', '')
    hoje = now_local()

    try:
        dt_inicial = datetime.strptime(data_inicial, '%Y-%m-%d') if data_inicial else hoje - timedelta(days=30)
    except ValueError:
        dt_inicial = hoje - timedelta(days=30)

    try:
        dt_final = datetime.strptime(data_final + ' 23:59:59', '%Y-%m-%d %H:%M:%S') if data_final else hoje
    except ValueError:
        dt_final = hoje

    return dt_inicial, dt_final


def filtro_turno():
    turno = request.args.get('turno', '')
    if not turno or turno == 'todos':
        return None
    hora = func.cast(func.strftime('%H', Pedido.pago_em), db.Integer)
    if turno == 'almoco':
        return and_(hora >= 10, hora < 16)
    if turno == 'espetinho':
        return or_(hora >= 19, hora < 5)
    return None


def aplicar_filtros(query):
    dt_inicial, dt_final = parse_datas()
    query = query.filter(Pedido.status == 'pago', Pedido.pago_em >= dt_inicial, Pedido.pago_em <= dt_final)
    turno = filtro_turno()
    if turno is not None:
        query = query.filter(turno)
    return query


@bp.route('/')
@login_required
def index():
    hoje = now_local()
    data_inicial = (hoje - timedelta(days=30)).strftime('%Y-%m-%d')
    data_final = hoje.strftime('%Y-%m-%d')
    return render_template('relatorios.html', data_inicial=data_inicial, data_final=data_final)


@bp.route('/api/vendas')
@login_required
def api_vendas():
    query = Pedido.query
    query = aplicar_filtros(query)
    pedidos = query.order_by(Pedido.pago_em.asc()).all()

    return jsonify([{
        'id': p.id,
        'data': p.pago_em.strftime('%d/%m/%Y %H:%M') if p.pago_em else '',
        'cliente': p.cliente_nome or f"Mesa {p.mesa.numero if p.mesa else 'N/A'}",
        'total': p.total,
        'forma': p.forma_pagamento or 'N/A',
        'tipo': p.tipo or 'mesa'
    } for p in pedidos])


@bp.route('/api/vendas-por-produto')
@login_required
def api_vendas_por_produto():
    itens = db.session.query(
        Produto.nome,
        db.func.sum(ItemPedido.quantidade).label('total_qtd'),
        db.func.sum(ItemPedido.preco_unitario * ItemPedido.quantidade).label('total_valor')
    ).join(ItemPedido, ItemPedido.produto_id == Produto.id
    ).join(Pedido, Pedido.id == ItemPedido.pedido_id
    )
    itens = aplicar_filtros(itens)
    itens = itens.group_by(Produto.nome).order_by(db.text('total_qtd DESC')).all()

    return jsonify([{
        'nome': i.nome,
        'quantidade': i.total_qtd,
        'total': i.total_valor
    } for i in itens])


@bp.route('/api/resumo')
@login_required
def api_resumo():
    base = db.session.query(
        Pedido.tipo,
        db.func.count(Pedido.id).label('total_pedidos'),
        db.func.sum(Pedido.total).label('total_valor')
    )
    base = aplicar_filtros(base)
    base = base.group_by(Pedido.tipo).all()

    total_arrecadado = 0
    total_mesa = 0
    total_delivery = 0
    for r in base:
        total_arrecadado += r.total_valor or 0
        if r.tipo == 'mesa':
            total_mesa = r.total_pedidos
        elif r.tipo == 'delivery':
            total_delivery = r.total_pedidos

    return jsonify({
        'total_arrecadado': total_arrecadado,
        'total_mesa': total_mesa,
        'total_delivery': total_delivery,
        'total_pedidos': total_mesa + total_delivery,
    })


@bp.route('/api/vendas-por-pagamento')
@login_required
def api_vendas_por_pagamento():
    resultados = db.session.query(
        PagamentoParcial.forma_pagamento,
        db.func.count(db.distinct(PagamentoParcial.pedido_id)).label('total_pedidos'),
        db.func.sum(PagamentoParcial.valor).label('total_valor')
    ).join(Pedido, Pedido.id == PagamentoParcial.pedido_id)
    resultados = aplicar_filtros(resultados)
    resultados = resultados.group_by(PagamentoParcial.forma_pagamento).all()

    return jsonify([{
        'forma': r.forma_pagamento or 'N/A',
        'pedidos': r.total_pedidos,
        'total': r.total_valor
    } for r in resultados])


@bp.route('/exportar/csv')
@login_required
def exportar_csv():
    dt_inicial, dt_final = parse_datas()
    tipo = request.args.get('tipo', 'vendas')

    periodo = f'{dt_inicial.strftime("%d%m%Y")}_a_{dt_final.strftime("%d%m%Y")}'

    if tipo == 'vendas':
        query = Pedido.query
        query = aplicar_filtros(query)
        pedidos = query.all()
        dados = [[p.id, p.pago_em.strftime('%d/%m/%Y %H:%M') if p.pago_em else '',
                  p.cliente_nome or '', p.total or 0, p.forma_pagamento or ''] for p in pedidos]
        colunas = ['ID', 'Data', 'Cliente', 'Valor', 'Forma Pagamento']
        csv_data = exportar_relatorio_csv(dados, colunas, 'vendas.csv')
    else:
        itens = db.session.query(
            Produto.nome,
            db.func.sum(ItemPedido.quantidade).label('qtd'),
            db.func.sum(ItemPedido.preco_unitario * ItemPedido.quantidade).label('val')
        ).join(ItemPedido, ItemPedido.produto_id == Produto.id
        ).join(Pedido, Pedido.id == ItemPedido.pedido_id
        )
        itens = aplicar_filtros(itens)
        itens = itens.group_by(Produto.nome).all()
        dados = [[i.nome, i.qtd, f'{i.val:.2f}'] for i in itens]
        colunas = ['Produto', 'Quantidade', 'Valor Total']
        csv_data = exportar_relatorio_csv(dados, colunas, 'produtos.csv')

    return Response(
        csv_data,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={tipo}_{periodo}.csv'}
    )
