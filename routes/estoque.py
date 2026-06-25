from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required
from models import db, Insumo, MovimentoEstoque, CategoriaInsumo, Categoria, Produto, CATEGORIAS_INSUMO_FIXAS
from datetime import datetime

bp = Blueprint('estoque', __name__, url_prefix='/estoque')


@bp.route('/')
@login_required
def listar():
    categorias_bd = CategoriaInsumo.query.order_by(CategoriaInsumo.nome).all()
    if not categorias_bd:
        for nome in CATEGORIAS_INSUMO_FIXAS:
            db.session.add(CategoriaInsumo(nome=nome))
        db.session.commit()
        categorias_bd = CategoriaInsumo.query.order_by(CategoriaInsumo.nome).all()
    categorias = {}
    for cat in categorias_bd:
        categorias[cat.nome] = Insumo.query.filter_by(categoria=cat.nome).order_by(Insumo.nome).all()
    return render_template('estoque.html', categorias=categorias, CATEGORIAS_INSUMO=[c.nome for c in categorias_bd], CATEGORIAS_BD=categorias_bd)


@bp.route('/salvar', methods=['POST'])
@login_required
def salvar():
    insumo_id = request.form.get('id')
    nome = request.form.get('nome', '').strip()
    categoria = request.form.get('categoria', 'espetos')
    quantidade = request.form.get('quantidade', '0').replace(',', '.')
    unidade = request.form.get('unidade', 'un')
    quantidade_minima = request.form.get('quantidade_minima', '0').replace(',', '.')
    produzido_cozinha = request.form.get('produzido_cozinha') == 'on'
    if not nome:
        flash('Nome do insumo é obrigatório', 'error')
        return redirect(url_for('estoque.listar'))

    try:
        quantidade = float(quantidade)
        quantidade_minima = float(quantidade_minima)
    except ValueError:
        flash('Valores inválidos', 'error')
        return redirect(url_for('estoque.listar'))

    if insumo_id:
        insumo = Insumo.query.get(int(insumo_id))
        if not insumo:
            flash('Insumo não encontrado', 'error')
            return redirect(url_for('estoque.listar'))
        insumo.nome = nome
        insumo.categoria = categoria
        insumo.quantidade = quantidade
        insumo.unidade = unidade
        insumo.quantidade_minima = quantidade_minima
        insumo.produzido_cozinha = produzido_cozinha
        for produto in insumo.produtos:
            produto.produzido_cozinha = produzido_cozinha
        flash('Insumo atualizado!', 'success')
    else:
        insumo = Insumo(
            nome=nome, categoria=categoria,
            quantidade=quantidade, unidade=unidade,
            quantidade_minima=quantidade_minima,
            produzido_cozinha=produzido_cozinha
        )
        db.session.add(insumo)
        flash('Insumo cadastrado!', 'success')

    db.session.commit()
    return redirect(url_for('estoque.listar'))


@bp.route('/movimento', methods=['POST'])
@login_required
def movimento():
    insumo_id = request.form.get('insumo_id')
    tipo = request.form.get('tipo')
    quantidade = request.form.get('quantidade', '0').replace(',', '.')
    observacao = request.form.get('observacao', '').strip()

    try:
        quantidade = float(quantidade)
    except ValueError:
        flash('Quantidade inválida', 'error')
        return redirect(url_for('estoque.listar'))

    if quantidade <= 0:
        flash('Quantidade deve ser positiva', 'error')
        return redirect(url_for('estoque.listar'))

    insumo = Insumo.query.get(int(insumo_id))
    if not insumo:
        flash('Insumo não encontrado', 'error')
        return redirect(url_for('estoque.listar'))

    if tipo == 'entrada':
        insumo.quantidade += quantidade
    elif tipo == 'saida':
        if insumo.quantidade < quantidade:
            flash(f'Estoque insuficiente! Disponível: {insumo.quantidade:.1f} {insumo.unidade}', 'error')
            return redirect(url_for('estoque.listar'))
        insumo.quantidade -= quantidade

    mov = MovimentoEstoque(
        insumo_id=insumo.id,
        tipo=tipo,
        quantidade=quantidade,
        observacao=observacao or None
    )
    db.session.add(mov)
    db.session.commit()
    flash('Movimento registrado!', 'success')
    return redirect(url_for('estoque.listar'))


@bp.route('/categoria/salvar', methods=['POST'])
@login_required
def salvar_categoria():
    nome = request.form.get('nome', '').strip().lower()
    if not nome:
        flash('Nome da categoria é obrigatório', 'error')
        return redirect(url_for('estoque.listar'))
    existe = CategoriaInsumo.query.filter_by(nome=nome).first()
    if existe:
        flash('Categoria já existe', 'error')
        return redirect(url_for('estoque.listar'))
    db.session.add(CategoriaInsumo(nome=nome))
    db.session.commit()
    flash('Categoria criada!', 'success')
    return redirect(url_for('estoque.listar'))


@bp.route('/categoria/excluir/<int:id>')
@login_required
def excluir_categoria(id):
    cat = CategoriaInsumo.query.get(id)
    if not cat:
        flash('Categoria não encontrada', 'error')
        return redirect(url_for('estoque.listar'))
    insumos = Insumo.query.filter_by(categoria=cat.nome).count()
    if insumos > 0:
        flash(f'Exclua os insumos da categoria "{cat.nome}" primeiro', 'error')
        return redirect(url_for('estoque.listar'))
    db.session.delete(cat)
    db.session.commit()
    flash('Categoria removida!', 'success')
    return redirect(url_for('estoque.listar'))


@bp.route('/toggle-cozinha/<int:id>', methods=['POST'])
@login_required
def toggle_cozinha(id):
    insumo = Insumo.query.get(id)
    if not insumo:
        return jsonify({'erro': 'Insumo não encontrado'}), 404
    insumo.produzido_cozinha = not insumo.produzido_cozinha
    for produto in insumo.produtos:
        produto.produzido_cozinha = insumo.produzido_cozinha
    db.session.commit()
    return jsonify({'produzido_cozinha': insumo.produzido_cozinha})


@bp.route('/api/alertas')
@login_required
def api_alertas():
    baixo = Insumo.query.filter(
        Insumo.quantidade_minima > 0,
        Insumo.quantidade <= Insumo.quantidade_minima
    ).all()
    return jsonify([{
        'id': i.id, 'nome': i.nome,
        'quantidade': i.quantidade,
        'unidade': i.unidade,
        'minimo': i.quantidade_minima
    } for i in baixo])


@bp.route('/excluir/<int:id>')
@login_required
def excluir(id):
    insumo = Insumo.query.get(id)
    if not insumo:
        flash('Insumo não encontrado', 'error')
        return redirect(url_for('estoque.listar'))
    db.session.delete(insumo)
    db.session.commit()
    flash('Insumo removido!', 'success')
    return redirect(url_for('estoque.listar'))
