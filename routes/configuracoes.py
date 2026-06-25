import json
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, User, Mesa, Configuracao, Categoria

bp = Blueprint('config', __name__, url_prefix='/config')


@bp.route('/')
@login_required
def index():
    if current_user.role != 'owner':
        flash('Acesso restrito ao proprietário', 'error')
        return redirect(url_for('dashboard.index'))
    usuarios = User.query.all()
    mesas = Mesa.query.order_by(Mesa.numero).all()
    configs = {c.chave: c.valor for c in Configuracao.query.all()}
    categorias = Categoria.query.order_by(Categoria.nome).all()
    return render_template('configuracoes.html', usuarios=usuarios, mesas=mesas, configs=configs, categorias=categorias)


@bp.route('/salvar-config', methods=['POST'])
@login_required
def salvar_config():
    if current_user.role != 'owner':
        return redirect(url_for('dashboard.index'))

    chaves = ['nome_estabelecimento', 'horario_abertura', 'horario_fechamento']
    for chave in chaves:
        valor = request.form.get(chave, '').strip()
        config = Configuracao.query.filter_by(chave=chave).first()
        if config:
            config.valor = valor
        else:
            config = Configuracao(chave=chave, valor=valor)
            db.session.add(config)

    db.session.commit()
    flash('Configurações salvas!', 'success')
    return redirect(url_for('config.index'))


@bp.route('/salvar-mesa', methods=['POST'])
@login_required
def salvar_mesa():
    if current_user.role != 'owner':
        return redirect(url_for('dashboard.index'))

    mesa_id = request.form.get('id')
    numero = request.form.get('numero')

    try:
        numero = int(numero)
    except (ValueError, TypeError):
        flash('Número da mesa inválido', 'error')
        return redirect(url_for('config.index'))

    if mesa_id:
        mesa = Mesa.query.get(int(mesa_id))
        if not mesa:
            flash('Mesa não encontrada', 'error')
            return redirect(url_for('config.index'))
        mesa.numero = numero
        flash('Mesa atualizada!', 'success')
    else:
        if Mesa.query.filter_by(numero=numero).first():
            flash(f'Mesa {numero} já existe!', 'error')
            return redirect(url_for('config.index'))
        mesa = Mesa(numero=numero)
        db.session.add(mesa)
        flash('Mesa cadastrada!', 'success')

    db.session.commit()
    return redirect(url_for('config.index'))


@bp.route('/excluir-mesa/<int:id>')
@login_required
def excluir_mesa(id):
    if current_user.role != 'owner':
        return redirect(url_for('dashboard.index'))
    mesa = Mesa.query.get(id)
    if not mesa:
        flash('Mesa não encontrada', 'error')
        return redirect(url_for('config.index'))
    db.session.delete(mesa)
    db.session.commit()
    flash('Mesa removida!', 'success')
    return redirect(url_for('config.index'))


@bp.route('/salvar-funcionario', methods=['POST'])
@login_required
def salvar_funcionario():
    if current_user.role != 'owner':
        return redirect(url_for('dashboard.index'))

    nome = request.form.get('nome', '').strip()
    senha = request.form.get('senha', '')
    role = request.form.get('role', 'garcom')

    if not nome:
        flash('Nome é obrigatório', 'error')
        return redirect(url_for('config.index'))

    if User.query.filter_by(nome=nome).first():
        flash('Usuário já existe!', 'error')
        return redirect(url_for('config.index'))

    user = User(nome=nome, role=role)
    user.set_password(senha)
    db.session.add(user)
    db.session.commit()
    flash('Funcionário cadastrado!', 'success')
    return redirect(url_for('config.index'))


@bp.route('/excluir-funcionario/<int:id>')
@login_required
def excluir_funcionario(id):
    if current_user.role != 'owner':
        return redirect(url_for('dashboard.index'))
    if id == current_user.id:
        flash('Não pode excluir a si mesmo', 'error')
        return redirect(url_for('config.index'))
    user = User.query.get(id)
    if not user:
        flash('Funcionário não encontrado', 'error')
        return redirect(url_for('config.index'))
    db.session.delete(user)
    db.session.commit()
    flash('Funcionário removido!', 'success')
    return redirect(url_for('config.index'))


@bp.route('/salvar-horarios', methods=['POST'])
@login_required
def salvar_horarios():
    if current_user.role != 'owner':
        return redirect(url_for('dashboard.index'))

    for cat in Categoria.query.all():
        cat.abre = request.form.get(f'abre_{cat.id}', '').strip() or None
        cat.fecha = request.form.get(f'fecha_{cat.id}', '').strip() or None
    db.session.commit()
    flash('Horários das categorias salvos!', 'success')
    return redirect(url_for('config.index'))


@bp.route('/salvar-dias', methods=['POST'])
@login_required
def salvar_dias():
    if current_user.role != 'owner':
        return redirect(url_for('dashboard.index'))

    dias_marcados = request.form.getlist('dias')
    categorias_lista = [c.nome for c in Categoria.query.all()]
    data = {}
    for i in range(7):
        si = str(i)
        ativo = si in dias_marcados
        turnos = []
        a1 = request.form.get(f'abre1_{i}', '').strip()
        f1 = request.form.get(f'fecha1_{i}', '').strip()
        a2 = request.form.get(f'abre2_{i}', '').strip()
        f2 = request.form.get(f'fecha2_{i}', '').strip()
        if ativo and a1 and f1:
            cats1 = request.form.getlist(f'cat1_{i}')
            turnos.append({'abre': a1, 'fecha': f1, 'categorias': cats1})
        if ativo and a2 and f2:
            cats2 = request.form.getlist(f'cat2_{i}')
            turnos.append({'abre': a2, 'fecha': f2, 'categorias': cats2})
        data[si] = {'ativo': ativo, 'turnos': turnos}

    valor = json.dumps(data, ensure_ascii=False)
    config = Configuracao.query.filter_by(chave='dias_funcionamento').first()
    if config:
        config.valor = valor
    else:
        config = Configuracao(chave='dias_funcionamento', valor=valor)
        db.session.add(config)
    db.session.commit()
    flash('Dias e horários salvos!', 'success')
    return redirect(url_for('config.index'))
