from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from models import db, Produto, Categoria, Insumo, Pedido, ItemPedido, MovimentoEstoque, CardapioAlmoco, AlmocoDia, DIAS_SEMANA, Configuracao
from utils import now_local, imprimir_pedido
import json

bp = Blueprint('cardapio', __name__, url_prefix='/cardapio')


@bp.route('/')
@login_required
def listar():
    produtos = Produto.query.order_by(Produto.tipo, Produto.nome).all()
    categorias = Categoria.query.filter_by(ativo=True).all()
    insumos = Insumo.query.order_by(Insumo.nome).all()
    return render_template('cardapio.html', produtos=produtos, categorias=categorias, insumos=insumos)


@bp.route('/api/listar')
@login_required
def api_listar():
    produtos = Produto.query.order_by(Produto.tipo, Produto.nome).all()
    return jsonify([{
        'id': p.id, 'nome': p.nome, 'preco': p.preco,
        'tipo': p.tipo, 'categoria': p.categoria.nome if p.categoria else '',
        'ativo': p.ativo
    } for p in produtos])


@bp.route('/salvar', methods=['POST'])
@login_required
def salvar():
    produto_id = request.form.get('id')
    nome = request.form.get('nome', '').strip()
    preco = request.form.get('preco', '0').replace(',', '.')
    categoria_id = request.form.get('categoria_id') or None
    tipo = request.form.get('tipo', 'espetinho')
    ativo = request.form.get('ativo') == 'on'
    produzido_cozinha = request.form.get('produzido_cozinha') == 'on'
    insumo_id = request.form.get('insumo_id') or None
    qtd_insumo = request.form.get('qtd_insumo', '1').replace(',', '.')

    if not nome:
        flash('Nome do produto é obrigatório', 'error')
        return redirect(url_for('cardapio.listar'))

    try:
        preco = float(preco)
        qtd_insumo = float(qtd_insumo)
    except ValueError:
        preco = 0
        qtd_insumo = 1

    if produto_id:
        produto = Produto.query.get(int(produto_id))
        if not produto:
            flash('Produto não encontrado', 'error')
            return redirect(url_for('cardapio.listar'))
        produto.nome = nome
        produto.preco = preco
        produto.categoria_id = int(categoria_id) if categoria_id else None
        produto.tipo = tipo
        produto.ativo = ativo
        produto.insumo_id = int(insumo_id) if insumo_id else None
        produto.qtd_insumo = qtd_insumo
        produto.produzido_cozinha = produzido_cozinha
        flash('Produto atualizado!', 'success')
    else:
        produto = Produto(
            nome=nome, preco=preco,
            categoria_id=int(categoria_id) if categoria_id else None,
            tipo=tipo, ativo=ativo,
            insumo_id=int(insumo_id) if insumo_id else None,
            qtd_insumo=qtd_insumo,
            produzido_cozinha=produzido_cozinha,
        )
        db.session.add(produto)
        flash('Produto cadastrado!', 'success')

    db.session.commit()
    return redirect(url_for('cardapio.listar'))


@bp.route('/online')
def cardapio_online():
    config = Configuracao.query.filter_by(chave='dias_funcionamento').first()
    hoje = now_local().weekday()
    hora_atual = now_local().strftime('%H:%M')
    DIA_NOMES = ['Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo']

    turno_atual = None
    categorias_turno = []
    tem_config = config is not None and bool(config.valor)
    tem_config_hoje = False
    data = {}
    if tem_config:
        if config.valor.startswith('{'):
            try:
                data = json.loads(config.valor)
                d = data.get(str(hoje), {})
                if d.get('ativo'):
                    tem_config_hoje = True
                    for turno in d.get('turnos', []):
                        if turno.get('abre') and turno.get('fecha'):
                            no_horario = False
                            if turno['abre'] <= turno['fecha']:
                                if turno['abre'] <= hora_atual <= turno['fecha']:
                                    no_horario = True
                            else:
                                if hora_atual >= turno['abre'] or hora_atual <= turno['fecha']:
                                    no_horario = True
                            if no_horario:
                                turno_atual = turno
                                categorias_turno = turno.get('categorias', [])
                                break
            except (json.JSONDecodeError, KeyError):
                pass
        else:
            dias = config.valor.split(',')
            if str(hoje) in dias:
                turno_atual = True
    else:
        if hoje < 6:
            turno_atual = True

    proximo_horario = None
    proximo_dia = None
    if not turno_atual:
        if tem_config_hoje:
            for turno in d.get('turnos', []):
                if turno.get('abre'):
                    if turno['abre'] <= turno.get('fecha', '23:59'):
                        if hora_atual < turno['abre']:
                            proximo_horario = turno['abre']
                            break
                    else:
                        if hora_atual >= turno['fecha'] and hora_atual < turno['abre']:
                            proximo_horario = turno['abre']
                            break
        elif tem_config:
            for i in range(1, 8):
                dia_idx = (hoje + i) % 7
                d_next = data.get(str(dia_idx), {})
                if d_next.get('ativo'):
                    turnos = d_next.get('turnos', [])
                    if turnos and turnos[0].get('abre'):
                        proximo_dia = DIA_NOMES[dia_idx]
                        proximo_horario = turnos[0]['abre']
                        break
        return render_template('cardapio_online.html', indisponivel=True, almoco_hoje=None, almoco_produtos=[], categorias=[], produtos=[], proximo_horario=proximo_horario, proximo_dia=proximo_dia)

    todas_categorias = Categoria.query.filter_by(ativo=True).order_by(Categoria.id).all()
    if categorias_turno:
        categorias_filtradas = [c for c in todas_categorias if c.nome in categorias_turno and c.nome != 'Almoço']
    else:
        categorias_filtradas = [c for c in todas_categorias if c.nome != 'Almoço']

    if categorias_turno:
        nomes_cat = [c for c in categorias_turno if c != 'Almoço']
        produtos = Produto.query.filter(
            Produto.ativo == True,
            Produto.categoria_id.in_(
                db.session.query(Categoria.id).filter(Categoria.nome.in_(nomes_cat))
            )
        ).order_by(Produto.tipo, Produto.nome).all()
    else:
        produtos = Produto.query.filter_by(ativo=True).order_by(Produto.tipo, Produto.nome).all()

    almoco_hoje = None
    almoco_produtos = []
    if 'Almoço' in categorias_turno or not categorias_turno:
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

    return render_template('cardapio_online.html', indisponivel=False, categorias=categorias_filtradas, produtos=produtos,
                           almoco_hoje=almoco_hoje, almoco_produtos=almoco_produtos)


@bp.route('/online/pedir', methods=['POST'])
def pedir_online():
    cliente_nome = request.form.get('cliente_nome', '').strip()
    telefone = request.form.get('telefone', '').strip()
    endereco = request.form.get('endereco', '').strip()
    forma_pagamento = request.form.get('forma_pagamento', 'dinheiro')
    troco = request.form.get('troco', '').strip()
    observacao = request.form.get('observacao', '').strip()
    itens_json = request.form.get('itens', '[]')

    itens = json.loads(itens_json)
    if not itens:
        flash('Adicione pelo menos um item ao pedido.', 'error')
        return redirect(url_for('cardapio.cardapio_online'))

    # Resolve 'almoco' strings to actual database product IDs
    for item in itens:
        if item['produto_id'] == 'almoco':
            hoje_dia = now_local().weekday()
            reg = CardapioAlmoco.query.filter_by(dia_semana=hoje_dia, ativo=True).first()
            preco_almoco = reg.preco if (reg and reg.preco) else 0.0
            prod_almoco = Produto.query.filter_by(nome='Almoço do Dia').first()
            if not prod_almoco:
                cat = Categoria.query.filter_by(nome='Almoço').first()
                if not cat:
                    cat = Categoria(nome='Almoço')
                    db.session.add(cat)
                    db.session.flush()
                prod_almoco = Produto(
                    nome='Almoço do Dia',
                    preco=preco_almoco,
                    categoria_id=cat.id,
                    tipo='almoco',
                    ativo=True,
                    produzido_cozinha=True,
                )
                db.session.add(prod_almoco)
                db.session.flush()
            else:
                prod_almoco.preco = preco_almoco
            item['produto_id'] = prod_almoco.id

    obs_parts = []
    if endereco:
        obs_parts.append(f'Endereço: {endereco}')
    if telefone:
        obs_parts.append(f'WhatsApp: {telefone}')
    if forma_pagamento == 'dinheiro' and troco:
        obs_parts.append(f'Troco p/ {troco}')
    if forma_pagamento in ('pix', 'cartao'):
        obs_parts.append(f'Pagamento: {forma_pagamento}')
    if observacao:
        obs_parts.append(f'Obs: {observacao}')

    pedido = Pedido(
        mesa_id=None,
        cliente_nome=cliente_nome or None,
        tipo='delivery',
        forma_pagamento=forma_pagamento,
        status='em_preparo',
        ultimo_preparo_em=now_local(),
        observacao='\n'.join(obs_parts) if obs_parts else None,
    )
    db.session.add(pedido)
    db.session.flush()

    total = 0
    tem_cozinha = False
    for item in itens:
        produto = Produto.query.get(item['produto_id'])
        if not produto:
            continue
        if produto.produzido_cozinha:
            tem_cozinha = True
        qtd = int(item.get('quantidade', 1))
        item_pedido = ItemPedido(
            pedido_id=pedido.id,
            produto_id=produto.id,
            quantidade=qtd,
            preco_unitario=produto.preco,
        )
        db.session.add(item_pedido)
        total += produto.preco * qtd

    pedido.total = total
    db.session.flush()

    # Baixa no estoque
    erros_estoque = []
    for item_data in itens:
        qtd_pedido = int(item_data.get('quantidade', 1))
        prod = Produto.query.get(item_data['produto_id'])
        if not prod or not prod.insumo_id:
            continue
        insumo = prod.insumo
        total_consumo = prod.qtd_insumo * qtd_pedido
        if insumo.quantidade < total_consumo:
            erros_estoque.append(f'{prod.nome} (estoque insuficiente: {insumo.quantidade:.1f}{insumo.unidade} disponível, {total_consumo:.1f}{insumo.unidade} necessário)')
            continue
        insumo.quantidade -= total_consumo
        mov = MovimentoEstoque(
            insumo_id=insumo.id,
            tipo='saida',
            quantidade=total_consumo,
            observacao=f'Pedido Online #{pedido.id} - {prod.nome}',
        )
        db.session.add(mov)

    if erros_estoque:
        db.session.rollback()
        flash('Não foi possível processar o pedido. Itens sem estoque:', 'error')
        for err in erros_estoque:
            flash(err, 'error')
        return redirect(url_for('cardapio.cardapio_online'))

    if not tem_cozinha:
        pedido.status = 'pronto'
    db.session.commit()

    ok_print, erro_print = imprimir_pedido(pedido)
    if not ok_print:
        print(f'[IMPRESSÃO] Erro ao imprimir pedido #{pedido.id}: {erro_print}')

    flash(f'Pedido #{pedido.id} enviado com sucesso! Guarde esse número.', 'success')
    return redirect(url_for('cardapio.ver_pedido', id=pedido.id))


@bp.route('/online/status', methods=['GET', 'POST'])
def consultar_pedido():
    if request.method == 'POST':
        pedido_id = request.form.get('pedido_id', '').strip()
        if pedido_id.isdigit():
            return redirect(url_for('cardapio.ver_pedido', id=int(pedido_id)))
        flash('Digite um número de pedido válido.', 'error')
        return redirect(url_for('cardapio.consultar_pedido'))
    return render_template('consulta_pedido.html', pedido=None)


@bp.route('/online/pedido/<int:id>')
def ver_pedido(id):
    pedido = Pedido.query.get(id)
    if not pedido:
        flash('Pedido não encontrado.', 'error')
        return redirect(url_for('cardapio.cardapio_online'))
    if pedido.tipo != 'delivery':
        flash('Consulta disponível apenas para pedidos do delivery.', 'error')
        return redirect(url_for('cardapio.cardapio_online'))
    return render_template('consulta_pedido.html', pedido=pedido)


@bp.route('/toggle/<int:id>')
@login_required
def toggle(id):
    produto = Produto.query.get(id)
    if not produto:
        flash('Produto não encontrado', 'error')
        return redirect(url_for('cardapio.listar'))
    produto.ativo = not produto.ativo
    db.session.commit()
    return redirect(url_for('cardapio.listar'))


@bp.route('/excluir/<int:id>')
@login_required
def excluir(id):
    produto = Produto.query.get(id)
    if not produto:
        flash('Produto não encontrado', 'error')
        return redirect(url_for('cardapio.listar'))
    itens = ItemPedido.query.filter_by(produto_id=produto.id).first()
    if itens:
        flash(f'Produto "{produto.nome}" possui pedidos vinculados. Desative-o em vez de excluir.', 'error')
        return redirect(url_for('cardapio.listar'))
    try:
        db.session.delete(produto)
        db.session.commit()
        flash('Produto removido!', 'success')
    except Exception:
        db.session.rollback()
        flash('Erro ao remover produto. Ele pode estar vinculado a pedidos.', 'error')
    return redirect(url_for('cardapio.listar'))


@bp.route('/categorias', methods=['POST'])
@login_required
def salvar_categoria():
    nome = request.form.get('nome', '').strip()
    if nome:
        cat = Categoria(nome=nome)
        db.session.add(cat)
        db.session.commit()
        flash('Categoria criada!', 'success')
    return redirect(url_for('cardapio.listar'))


@bp.route('/categoria/excluir/<int:id>')
@login_required
def excluir_categoria(id):
    cat = Categoria.query.get(id)
    if not cat:
        flash('Categoria não encontrada', 'error')
        return redirect(url_for('cardapio.listar'))
    produtos = Produto.query.filter_by(categoria_id=cat.id).count()
    if produtos > 0:
        flash(f'Exclua os produtos da categoria "{cat.nome}" primeiro.', 'error')
        return redirect(url_for('cardapio.listar'))
    try:
        db.session.delete(cat)
        db.session.commit()
        flash('Categoria removida!', 'success')
    except Exception:
        db.session.rollback()
        flash('Erro ao excluir categoria.', 'error')
    return redirect(url_for('cardapio.listar'))
