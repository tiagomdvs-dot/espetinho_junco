from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required
from models import db, Pedido, CaixaRegistro, PagamentoParcial
from datetime import datetime, timedelta
from utils import now_local, hoje_inicio, marcar_pago, processar_pagamentos
from sqlalchemy import func

bp = Blueprint('caixa', __name__, url_prefix='/caixa')


def get_caixa_hoje():
    hoje = now_local().date()
    inicio = datetime(hoje.year, hoje.month, hoje.day)
    fim = inicio + timedelta(days=1)
    caixa = CaixaRegistro.query.filter(
        CaixaRegistro.data_abertura >= inicio,
        CaixaRegistro.data_abertura < fim
    ).first()
    return caixa


@bp.route('/')
@login_required
def index():
    caixa = get_caixa_hoje()
    pedidos_pendentes = Pedido.query.filter(
        Pedido.status.in_(['em_preparo', 'pronto', 'saiu_para_entrega', 'entregue'])
    ).order_by(Pedido.criado_em.desc()).all()
    hoje_inicio_dt = now_local().replace(hour=0, minute=0, second=0, microsecond=0)
    pedidos_pagos = Pedido.query.filter(
        Pedido.status == 'pago',
        Pedido.pago_em >= hoje_inicio_dt
    ).order_by(Pedido.pago_em.desc()).limit(50).all()

    parciais = db.session.query(
        PagamentoParcial.forma_pagamento,
        func.sum(PagamentoParcial.valor)
    ).join(Pedido, Pedido.id == PagamentoParcial.pedido_id).filter(
        Pedido.status == 'pago',
        Pedido.pago_em >= hoje_inicio_dt
    ).group_by(PagamentoParcial.forma_pagamento).all()
    resumo = {}
    for forma, total in parciais:
        resumo[forma] = resumo.get(forma, 0) + (total or 0)

    return render_template('caixa.html',
                           caixa=caixa,
                           pedidos_pendentes=pedidos_pendentes,
                           pedidos_pagos=pedidos_pagos,
                           resumo=resumo)


@bp.route('/abrir', methods=['POST'])
@login_required
def abrir():
    if get_caixa_hoje():
        flash('Caixa já está aberto hoje!', 'warning')
        return redirect(url_for('caixa.index'))

    saldo_inicial = request.form.get('saldo_inicial', '0').replace(',', '.')
    try:
        saldo_inicial = float(saldo_inicial)
    except ValueError:
        saldo_inicial = 0

    caixa = CaixaRegistro(saldo_inicial=saldo_inicial, status='aberto')
    db.session.add(caixa)
    db.session.commit()
    flash('Caixa aberto!', 'success')
    return redirect(url_for('caixa.index'))


@bp.route('/pagar', methods=['POST'])
@login_required
def pagar():
    pedido_id = request.form.get('pedido_id')
    pagamentos_json = request.form.get('pagamentos', '[{"forma":"dinheiro","valor":0}]')

    import json
    pagamentos = json.loads(pagamentos_json)

    pedido = Pedido.query.get(int(pedido_id))
    if not pedido:
        flash('Pedido não encontrado', 'error')
        return redirect(url_for('caixa.index'))

    if len(pagamentos) == 1:
        ok, erro = marcar_pago(pedido, pagamentos[0]['forma'])
    else:
        ok, erro = processar_pagamentos(pedido, pagamentos)

    if not ok:
        flash(erro, 'error')
        return redirect(url_for('caixa.index'))
    db.session.commit()

    formas_str = ', '.join([f"{p['forma']} R$ {p['valor']:.2f}" for p in pagamentos])
    flash(f'Pedido #{pedido.id} pago! ({formas_str})', 'success')
    return redirect(url_for('caixa.index'))


@bp.route('/fechar', methods=['POST'])
@login_required
def fechar():
    caixa = get_caixa_hoje()
    if not caixa:
        flash('Nenhum caixa aberto hoje', 'error')
        return redirect(url_for('caixa.index'))

    hoje = now_local().date()
    inicio = datetime(hoje.year, hoje.month, hoje.day)
    fim = inicio + timedelta(days=1)
    total_vendas = db.session.query(db.func.sum(Pedido.total)).filter(
        Pedido.status == 'pago',
        Pedido.pago_em >= inicio,
        Pedido.pago_em < fim
    ).scalar() or 0

    caixa.saldo_final = (caixa.saldo_inicial or 0) + total_vendas
    caixa.status = 'fechado'
    caixa.data_fechamento = now_local()
    db.session.commit()
    flash('Caixa fechado com sucesso!', 'success')
    return redirect(url_for('caixa.index'))
