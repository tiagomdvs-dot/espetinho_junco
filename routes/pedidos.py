from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Pedido, ItemPedido, Produto, Mesa, Insumo, MovimentoEstoque, Categoria, CardapioAlmoco, AlmocoDia, DIAS_SEMANA, PagamentoParcial
from utils import now_local, marcar_pago, marcar_parcial, processar_pagamentos, total_parcial, imprimir_pedido
from sqlalchemy import case

bp = Blueprint('pedidos', __name__, url_prefix='/pedidos')


def _redirect_back(**kwargs):
    referer = request.referrer or ''
    if '/pedidos/garcom' in referer or 'pedidos%2Fgarcom' in referer:
        return redirect(url_for('pedidos.garcom', **kwargs))
    if '/pedidos/cozinha' in referer or 'pedidos%2Fcozinha' in referer:
        return redirect(url_for('pedidos.cozinha', **kwargs))
    if current_user.role == 'garcom':
        return redirect(url_for('pedidos.garcom', **kwargs))
    if current_user.role == 'cozinha':
        return redirect(url_for('pedidos.cozinha', **kwargs))
    return redirect(url_for('pedidos.listar', **kwargs))




@bp.route('/')
@login_required
def listar():
    if current_user.role == 'garcom':
        return redirect(url_for('pedidos.garcom'))
    if current_user.role == 'cozinha':
        return redirect(url_for('pedidos.cozinha'))
    pedidos = Pedido.query.order_by(Pedido.criado_em.desc()).all()
    produtos = Produto.query.filter_by(ativo=True).all()
    mesas = Mesa.query.filter_by(ativo=True).all()
    return render_template('pedidos.html', pedidos=pedidos, produtos=produtos, mesas=mesas)


@bp.route('/cozinha')
@login_required
def cozinha():
    if current_user.role not in ('cozinha', 'owner'):
        return redirect(url_for('pedidos.listar'))
    status_order = case(
        (Pedido.status == 'em_preparo', 0),
        (Pedido.status == 'pronto', 1),
        else_=2
    )
    pedidos = Pedido.query.filter(
        Pedido.status.in_(['em_preparo', 'pronto']),
        db.or_(
            Pedido.tipo == 'delivery',
            Pedido.itens.any(
                db.or_(
                    ItemPedido.produto.has(Produto.produzido_cozinha == True),
                    ItemPedido.produto.has(
                        Produto.insumo.has(Insumo.produzido_cozinha == True)
                    )
                )
            )
        )
    ).order_by(status_order, Pedido.criado_em.asc()).all()
    return render_template('pedidos_cozinha.html', pedidos=pedidos)


@bp.route('/garcom')
@login_required
def garcom():
    if current_user.role not in ('garcom', 'owner'):
        return redirect(url_for('pedidos.listar'))
    mesas = Mesa.query.filter_by(ativo=True).all()
    pedidos_abertos = Pedido.query.filter(
        Pedido.status.in_(['em_preparo', 'pronto', 'saiu_para_entrega', 'entregue']),
        Pedido.tipo == 'mesa'
    ).order_by(Pedido.criado_em.desc()).all()

    mesas_ocupadas = set()
    for p in pedidos_abertos:
        if p.mesa_id and p.tipo == 'mesa':
            mesas_ocupadas.add(p.mesa_id)

    categorias = Categoria.query.filter_by(ativo=True).order_by(Categoria.id).all()
    produtos = Produto.query.filter_by(ativo=True).all()

    produtos_com_receita = set()
    estoque_insuficiente = set()
    for p in produtos:
        if p.insumo_id:
            produtos_com_receita.add(p.id)
            if p.insumo.quantidade < p.qtd_insumo:
                estoque_insuficiente.add(p.id)

    hoje = now_local().weekday()
    almoco_hoje = None
    almoco_produtos = []
    if hoje < 6:
        reg = CardapioAlmoco.query.filter_by(dia_semana=hoje, ativo=True).first()
        if reg and reg.descricao:
            almoco_hoje = {'dia': DIAS_SEMANA[hoje], 'descricao': reg.descricao, 'preco': reg.preco or 0}
            ids_hoje = [ad.produto_id for ad in AlmocoDia.query.filter_by(dia_semana=hoje).all()]
            if ids_hoje:
                almoco_produtos = Produto.query.filter(Produto.id.in_(ids_hoje), Produto.ativo == True).all()
    else:
        reg = CardapioAlmoco.query.filter_by(ativo=True).first()
        if reg and reg.descricao:
            almoco_hoje = {'dia': DIAS_SEMANA[reg.dia_semana], 'descricao': reg.descricao, 'preco': reg.preco or 0}

    return render_template('pedidos_garcom.html', categorias=categorias, produtos=produtos, mesas=mesas,
                           pedidos_abertos=pedidos_abertos,
                           produtos_com_receita=produtos_com_receita,
                           estoque_insuficiente=estoque_insuficiente,
                           mesas_ocupadas=mesas_ocupadas,
                           almoco_hoje=almoco_hoje, almoco_produtos=almoco_produtos)


@bp.route('/criar', methods=['POST'])
@login_required
def criar():
    mesa_id = request.form.get('mesa_id') or None
    cliente_nome = request.form.get('cliente_nome', '').strip()
    tipo = request.form.get('tipo', 'mesa')
    observacao = request.form.get('observacao', '').strip()

    if current_user.role not in ('garcom', 'owner'):
        flash('Apenas garçons podem criar pedidos.', 'error')
        return redirect(url_for('pedidos.listar'))

    if tipo == 'mesa' and mesa_id:
        mesa_ocupada = Pedido.query.filter(
            Pedido.mesa_id == int(mesa_id),
            Pedido.status.in_(['em_preparo', 'pronto', 'saiu_para_entrega', 'entregue'])
        ).first()
        if mesa_ocupada:
            flash('Esta mesa já está ocupada.', 'error')
            return _redirect_back()

    pedido = Pedido(
        mesa_id=int(mesa_id) if mesa_id else None,
        cliente_nome=cliente_nome or None,
        tipo=tipo,
        status='em_preparo',
        ultimo_preparo_em=now_local(),
        observacao=observacao or None
    )
    db.session.add(pedido)
    db.session.commit()
    flash('Pedido criado!', 'success')
    return _redirect_back()


@bp.route('/adicionar-item', methods=['POST'])
@login_required
def adicionar_item():
    pedido_id = request.form.get('pedido_id')
    produto_id = request.form.get('produto_id')
    quantidade = int(request.form.get('quantidade', 1))
    observacao = request.form.get('observacao', '').strip()

    if produto_id == 'almoco':
        hoje_dia = now_local().weekday()
        reg = CardapioAlmoco.query.filter_by(dia_semana=hoje_dia).first()
        preco_almoco = reg.preco if (reg and reg.preco) else 0.0
        prod_almoco = Produto.query.filter_by(nome='Almoço do Dia').first()
        if not prod_almoco:
            cat = Categoria.query.filter_by(nome='Almoço').first()
            if not cat:
                cat = Categoria(nome='Almoço')
                db.session.add(cat)
                db.session.flush()
            prod_almoco = Produto(
                nome='Almoço do Dia', preco=preco_almoco,
                categoria_id=cat.id, tipo='almoco', ativo=True,
                produzido_cozinha=True,
            )
            db.session.add(prod_almoco)
            db.session.flush()
        else:
            prod_almoco.preco = preco_almoco
        produto_id = prod_almoco.id

    produto = Produto.query.get(int(produto_id))
    pedido = Pedido.query.get(int(pedido_id))

    if not produto or not pedido:
        flash('Produto ou pedido não encontrado', 'error')
        return _redirect_back()

    if pedido.status in ('pago', 'cancelado'):
        flash('Não é possível adicionar itens a este pedido.', 'error')
        return _redirect_back()

    item = ItemPedido(
        pedido_id=pedido.id,
        produto_id=produto.id,
        quantidade=quantidade,
        preco_unitario=produto.preco,
        observacao=observacao or None
    )
    db.session.add(item)

    pedido.total = (pedido.total or 0) + (produto.preco * quantidade)

    # Se o item é produzido na cozinha e o pedido já estava pronto, volta para preparo
    if produto.produzido_cozinha and pedido.status in ('pronto', 'entregue'):
        pedido.status = 'em_preparo'
        pedido.ultimo_preparo_em = now_local()

    erros_estoque = []
    if produto.insumo_id:
        insumo = produto.insumo
        total_consumo = produto.qtd_insumo * quantidade
        if insumo.quantidade < total_consumo:
            erros_estoque.append(f'{insumo.nome} (tem {insumo.quantidade}{insumo.unidade})')
        else:
            insumo.quantidade -= total_consumo
            mov = MovimentoEstoque(
                insumo_id=insumo.id,
                tipo='saida',
                quantidade=total_consumo,
                observacao=f'Pedido #{pedido.id} - {produto.nome}',
            )
            db.session.add(mov)

    if erros_estoque:
        db.session.rollback()
        flash(f'Estoque insuficiente: {" | ".join(erros_estoque)}', 'error')
        return _redirect_back()

    db.session.commit()
    flash('Item adicionado!', 'success')
    return _redirect_back()


@bp.route('/finalizar-mesa', methods=['POST'])
@login_required
def finalizar_mesa():
    if current_user.role not in ('garcom', 'owner'):
        flash('Permissão negada.', 'error')
        return redirect(url_for('pedidos.listar'))

    pedido_id = request.form.get('pedido_id')
    pagamentos_json = request.form.get('pagamentos', '[]')

    import json
    pagamentos = json.loads(pagamentos_json)

    pedido = Pedido.query.get(int(pedido_id))
    if not pedido:
        flash('Pedido não encontrado', 'error')
        return _redirect_back()

    if pedido.status == 'pago':
        flash('Pedido já está pago.', 'error')
        return _redirect_back()

    # Recalcula total do pedido
    total_pedido = 0
    for i in pedido.itens:
        preco = i.preco_unitario
        if preco is None:
            preco = i.produto.preco if i.produto else 0
        total_pedido += preco * i.quantidade
    pedido.total = total_pedido

    ja_pago = total_parcial(pedido)
    restante = total_pedido - ja_pago

    if not pagamentos:
        forma_pagamento = request.form.get('forma_pagamento', 'dinheiro')
        pagamentos = [{'forma': forma_pagamento, 'valor': restante}]

    total_pago_agora = sum(p['valor'] for p in pagamentos)
    if abs(total_pago_agora - restante) > 0.01:
        flash(f'Valor dos pagamentos (R$ {total_pago_agora:.2f}) difere do restante (R$ {restante:.2f}).', 'error')
        return _redirect_back()

    pedido.status = 'pago'
    pedido.pago_em = now_local()
    if len(pagamentos) == 1:
        pedido.forma_pagamento = pagamentos[0]['forma']
    else:
        pedido.forma_pagamento = 'multi'

    for p in pagamentos:
        pp = PagamentoParcial(pedido_id=pedido.id, valor=p['valor'], forma_pagamento=p['forma'])
        db.session.add(pp)

    db.session.commit()
    formas_str = ', '.join([f"{p['forma']} R${p['valor']:.2f}" for p in pagamentos])
    flash(f'Mesa finalizada! {formas_str}', 'success')
    return _redirect_back()


@bp.route('/status/<int:id>/<status>')
@login_required
def mudar_status(id, status):
    pedido = Pedido.query.get(id)
    if not pedido:
        flash('Pedido não encontrado', 'error')
        return _redirect_back()
    status_validos = ['em_preparo', 'pronto', 'entregue', 'cancelado']
    if status == 'pago':
        flash('Use o caixa para registrar pagamentos.', 'warning')
    elif status == 'entregue' and pedido.tipo != 'delivery':
        flash('Status "entregue" é apenas para pedidos delivery.', 'error')
    elif status in status_validos:
        pedido.status = status
        if status == 'em_preparo':
            pedido.ultimo_preparo_em = now_local()
        elif status == 'pronto':
            pedido.ultimo_preparo_em = None
            for item in ItemPedido.query.filter_by(pedido_id=pedido.id).all():
                item.pronto = True
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
    return _redirect_back()


@bp.route('/item-pronto/<int:item_id>')
@login_required
def item_pronto(item_id):
    item = ItemPedido.query.get(item_id)
    if not item:
        flash('Item não encontrado', 'error')
        return _redirect_back()
    item.pronto = not item.pronto
    db.session.commit()
    return _redirect_back()


@bp.route('/api/pedidos-ativos')
@login_required
def api_pedidos_ativos():
    pedidos = Pedido.query.filter(
        Pedido.status.in_(['em_preparo', 'pronto', 'saiu_para_entrega', 'entregue'])
    ).order_by(Pedido.criado_em.desc()).all()

    return jsonify([{
        'id': p.id,
        'cliente': p.cliente_nome or f"Mesa {p.mesa.numero if p.mesa else 'N/A'}",
        'tipo': p.tipo,
        'status': p.status,
        'total': p.total,
        'itens': [{
            'nome': i.produto.nome if i.produto else f'Item #{i.produto_id}',
            'qtd': i.quantidade,
            'preco': i.preco_unitario
        } for i in p.itens],
        'criado_em': p.criado_em.strftime('%H:%M') if p.criado_em else ''
    } for p in pedidos])


@bp.route('/criar-completo', methods=['POST'])
@login_required
def criar_completo():
    if current_user.role not in ('garcom', 'owner'):
        return jsonify({'erro': 'Permissão negada'}), 403

    tipo = request.form.get('tipo', 'mesa')
    mesa_id = request.form.get('mesa_id') or None
    cliente_nome = request.form.get('cliente_nome', '').strip()
    itens_json = request.form.get('itens', '[]')

    import json
    itens = json.loads(itens_json)

    if not itens:
        flash('Adicione pelo menos um item ao pedido.', 'error')
        return _redirect_back()

    if tipo == 'mesa' and mesa_id:
        mesa_ocupada = Pedido.query.filter(
            Pedido.mesa_id == int(mesa_id),
            Pedido.status.in_(['em_preparo', 'pronto', 'saiu_para_entrega', 'entregue'])
        ).first()
        if mesa_ocupada:
            flash('Esta mesa já está ocupada.', 'error')
            return _redirect_back()

    pedido = Pedido(
        mesa_id=int(mesa_id) if mesa_id else None,
        cliente_nome=cliente_nome or None,
        tipo=tipo,
        status='em_preparo',
        ultimo_preparo_em=now_local(),
    )
    db.session.add(pedido)
    db.session.flush()

    total = 0
    tem_cozinha = False
    for item in itens:
        if item['produto_id'] == 'almoco':
            hoje_dia = now_local().weekday()
            reg = CardapioAlmoco.query.filter_by(dia_semana=hoje_dia).first()
            preco_almoco = reg.preco if (reg and reg.preco) else 0.0
            prod_almoco = Produto.query.filter_by(nome='Almoço do Dia').first()
            if not prod_almoco:
                cat = Categoria.query.filter_by(nome='Almoço').first()
                if not cat:
                    cat = Categoria(nome='Almoço')
                    db.session.add(cat)
                    db.session.flush()
                prod_almoco = Produto(nome='Almoço do Dia', preco=preco_almoco, categoria_id=cat.id, tipo='almoco', ativo=True, produzido_cozinha=True)
                db.session.add(prod_almoco)
                db.session.flush()
            else:
                prod_almoco.preco = preco_almoco
            item['produto_id'] = prod_almoco.id
        produto = Produto.query.get(item['produto_id'])
        if not produto:
            continue
        if produto.produzido_cozinha:
            tem_cozinha = True
        qtd = int(item.get('quantidade', 1))
        observacao = item.get('observacao', '').strip() or None
        item_pedido = ItemPedido(
            pedido_id=pedido.id,
            produto_id=produto.id,
            quantidade=qtd,
            preco_unitario=produto.preco,
            observacao=observacao,
        )
        db.session.add(item_pedido)
        total += produto.preco * qtd

    pedido.total = total
    db.session.flush()

    erros_estoque = []
    for item_data in itens:
        qtd_pedido = int(item_data.get('quantidade', 1))
        prod = Produto.query.get(item_data['produto_id'])
        if not prod or not prod.insumo_id:
            continue
        prod_nome = prod.nome
        insumo = prod.insumo
        total_consumo = prod.qtd_insumo * qtd_pedido
        if insumo.quantidade < total_consumo:
            erros_estoque.append(f'{insumo.nome} (tem {insumo.quantidade}{insumo.unidade}, precisa {total_consumo})')
        else:
            insumo.quantidade -= total_consumo
            mov = MovimentoEstoque(
                insumo_id=insumo.id,
                tipo='saida',
                quantidade=total_consumo,
                observacao=f'Pedido #{pedido.id} - {prod_nome}',
            )
            db.session.add(mov)

    if erros_estoque:
        db.session.rollback()
        flash(f'Estoque insuficiente: {" | ".join(erros_estoque)}', 'error')
        return _redirect_back()

    if not tem_cozinha:
        pedido.status = 'pronto'
    db.session.commit()

    ok_print, erro_print = imprimir_pedido(pedido)
    if not ok_print:
        print(f'[IMPRESSÃO] Erro ao imprimir pedido #{pedido.id}: {erro_print}')

    flash('Pedido criado com sucesso!', 'success')
    return _redirect_back()


@bp.route('/receber-parcial', methods=['POST'])
@login_required
def receber_parcial():
    if current_user.role not in ('garcom', 'owner'):
        flash('Permissão negada.', 'error')
        return _redirect_back()
    pedido_id = request.form.get('pedido_id')
    forma = request.form.get('forma_pagamento', 'dinheiro')
    try:
        valor = float(request.form.get('valor', '0').replace(',', '.'))
    except ValueError:
        flash('Valor inválido.', 'error')
        return _redirect_back()
    pedido = Pedido.query.get(int(pedido_id))
    if not pedido:
        flash('Pedido não encontrado', 'error')
        return _redirect_back()
    ok, erro = marcar_parcial(pedido, forma, valor)
    if not ok:
        flash(erro, 'error')
        return _redirect_back()
    db.session.commit()
    flash(f'Recebido R$ {valor:.2f} via {forma}!', 'success')
    return _redirect_back()


@bp.route('/comanda/<int:id>')
@login_required
def comanda(id):
    pedido = Pedido.query.get(id)
    if not pedido:
        flash('Pedido não encontrado', 'error')
        return _redirect_back()
    if pedido.observacao:
        pedido.observacao = pedido.observacao.replace(' | ', '\n')
    return render_template('comanda.html', pedido=pedido)


@bp.route('/excluir/<int:id>')
@login_required
def excluir(id):
    pedido = Pedido.query.get(id)
    if not pedido:
        flash('Pedido não encontrado', 'error')
        return _redirect_back()

    # Restore stock for all items before deleting
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

    db.session.delete(pedido)
    db.session.commit()
    flash('Pedido removido!', 'success')
    return _redirect_back()


@bp.route('/remover-item/<int:id>')
@login_required
def remover_item(id):
    item = ItemPedido.query.get(id)
    if not item:
        flash('Item não encontrado', 'error')
        return _redirect_back()

    pedido = Pedido.query.get(item.pedido_id)
    if pedido and pedido.status not in ('em_preparo', 'pronto'):
        flash('Não é possível remover itens deste pedido.', 'error')
        return _redirect_back()

    # Restore stock
    produto = Produto.query.get(item.produto_id)
    if produto and produto.insumo_id:
        insumo = produto.insumo
        qtd_restore = produto.qtd_insumo * item.quantidade
        insumo.quantidade += qtd_restore
        mov = MovimentoEstoque(
            insumo_id=insumo.id,
            tipo='entrada',
            quantidade=qtd_restore,
            observacao=f'Removido do Pedido #{pedido.id} - {produto.nome}',
        )
        db.session.add(mov)

    # Recalculate total
    if pedido:
        pedido.total = (pedido.total or 0) - (item.preco_unitario * item.quantidade)

    db.session.delete(item)
    db.session.commit()
    flash('Item removido do pedido!', 'success')
    return _redirect_back()
