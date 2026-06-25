from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Pedido, ItemPedido, Produto, MovimentoEstoque
from utils import marcar_pago, now_local

bp = Blueprint('delivery', __name__, url_prefix='/delivery')


@bp.route('/')
@login_required
def listar():
    pedidos = Pedido.query.filter_by(tipo='delivery').order_by(
        Pedido.criado_em.desc()
    ).all()
    for p in pedidos:
        if p.observacao:
            p.observacao = p.observacao.replace(' | ', '\n')
    return render_template('delivery.html', pedidos=pedidos)


@bp.route('/status/<int:id>/<status>')
@login_required
def mudar_status(id, status):
    pedido = Pedido.query.get(id)
    if not pedido:
        flash('Pedido não encontrado', 'error')
        return redirect(url_for('delivery.listar'))
    if status == 'pago':
        forma = pedido.forma_pagamento or 'pix'
        ok, erro = marcar_pago(pedido, forma)
        if not ok:
            flash(erro, 'error')
            return redirect(url_for('delivery.listar'))
        db.session.commit()
        flash('Pedido delivery pago!', 'success')
        return redirect(url_for('delivery.listar'))
    if status == 'entregue' and pedido.tipo != 'delivery':
        flash('Status "entregue" é apenas para pedidos delivery.', 'error')
        return redirect(url_for('delivery.listar'))
    status_validos = ['em_preparo', 'pronto', 'saiu_para_entrega', 'entregue', 'cancelado']
    if status in status_validos:
        pedido.status = status
        if status == 'em_preparo':
            pedido.ultimo_preparo_em = now_local()
        elif status in ('pronto', 'saiu_para_entrega', 'entregue'):
            pedido.ultimo_preparo_em = None
        elif status == 'cancelado':
            pedido.ultimo_preparo_em = None
            for item in pedido.itens:
                produto = Produto.query.get(item.produto_id)
                if produto and produto.insumo_id:
                    insumo = produto.insumo
                    qtd_restore = produto.qtd_insumo * item.quantidade
                    insumo.quantidade += qtd_restore
                    mov = MovimentoEstoque(
                        insumo_id=insumo.id,
                        tipo='entrada',
                        quantidade=qtd_restore,
                        observacao=f'Restaurado - Pedido #{pedido.id} cancelado - {produto.nome}',
                    )
                    db.session.add(mov)
        db.session.commit()
        flash(f'Status atualizado para {status}!', 'success')
    return redirect(url_for('delivery.listar'))
