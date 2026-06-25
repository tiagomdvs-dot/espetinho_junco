from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from models import db, Produto, Categoria, CardapioAlmoco, AlmocoDia, DIAS_SEMANA

bp = Blueprint('almoco', __name__, url_prefix='/almoco')


def get_or_create_categoria():
    cat = Categoria.query.filter_by(nome='Almoço').first()
    if not cat:
        cat = Categoria(nome='Almoço', ativo=False)
        db.session.add(cat)
        db.session.commit()
    else:
        if cat.ativo:
            cat.ativo = False
            db.session.commit()
    return cat


@bp.route('/', methods=['GET', 'POST'])
@login_required
def listar():
    if request.method == 'POST':
        action = request.form.get('action', 'salvar_cardapio')

        if action == 'salvar_cardapio':
            for i in range(6):
                descricao = request.form.get(f'dia_{i}', '').strip()
                preco = request.form.get(f'preco_{i}', '0').replace(',', '.')
                try:
                    preco = float(preco)
                except ValueError:
                    preco = 0
                registro = CardapioAlmoco.query.filter_by(dia_semana=i).first()
                if descricao:
                    if registro:
                        registro.descricao = descricao
                        registro.preco = preco
                    else:
                        db.session.add(CardapioAlmoco(dia_semana=i, descricao=descricao, preco=preco))
                else:
                    if registro:
                        db.session.delete(registro)
            db.session.commit()
            flash('Cardápio da semana salvo!', 'success')

        elif action == 'add_produto':
            nome = request.form.get('nome', '').strip()
            preco = request.form.get('preco', '0').replace(',', '.')
            dias = request.form.getlist('dias')

            if not nome:
                flash('Nome é obrigatório', 'error')
            elif not dias:
                flash('Selecione pelo menos um dia', 'error')
            else:
                try:
                    preco = float(preco)
                except ValueError:
                    preco = 0
                cat = get_or_create_categoria()
                produto = Produto(nome=nome, preco=preco, categoria_id=cat.id, tipo='almoco')
                db.session.add(produto)
                db.session.flush()
                for d in dias:
                    db.session.add(AlmocoDia(produto_id=produto.id, dia_semana=int(d)))
                db.session.commit()
                flash('Item de almoço cadastrado!', 'success')

        elif action == 'editar_produto':
            produto_id = request.form.get('produto_id')
            nome = request.form.get('nome', '').strip()
            preco = request.form.get('preco', '0').replace(',', '.')
            dias = request.form.getlist('dias')

            produto = Produto.query.get(int(produto_id))
            if not produto:
                flash('Produto não encontrado', 'error')
            else:
                try:
                    preco = float(preco)
                except ValueError:
                    preco = 0
                produto.nome = nome
                produto.preco = preco
                AlmocoDia.query.filter_by(produto_id=produto.id).delete()
                for d in dias:
                    db.session.add(AlmocoDia(produto_id=produto.id, dia_semana=int(d)))
                db.session.commit()
                flash('Item atualizado!', 'success')

        return redirect(url_for('almoco.listar'))

    cardapios = {c.dia_semana: c for c in CardapioAlmoco.query.all()}
    cat = get_or_create_categoria()
    produtos = Produto.query.filter_by(categoria_id=cat.id).order_by(Produto.nome).all()
    return render_template('almoco.html', dias=DIAS_SEMANA, cardapios=cardapios, produtos=produtos)


@bp.route('/toggle-ativo/<int:dia>')
@login_required
def toggle_ativo(dia):
    reg = CardapioAlmoco.query.filter_by(dia_semana=dia).first()
    if reg:
        if reg.ativo:
            reg.ativo = False
            msg = 'desativado'
        else:
            CardapioAlmoco.query.filter(CardapioAlmoco.ativo == True).update({'ativo': False})
            reg.ativo = True
            msg = 'ativado'
        db.session.commit()
        flash(f'Cardápio de {DIAS_SEMANA[dia]} {msg}!', 'success')
    return redirect(url_for('almoco.listar'))


@bp.route('/excluir-produto/<int:id>')
@login_required
def excluir_produto(id):
    produto = Produto.query.get(id)
    if produto:
        AlmocoDia.query.filter_by(produto_id=produto.id).delete()
        db.session.delete(produto)
        db.session.commit()
        flash('Item removido!', 'success')
    return redirect(url_for('almoco.listar'))
