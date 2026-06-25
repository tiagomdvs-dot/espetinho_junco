from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from models import db, Contrato, ContratoPagamento
from utils import now_local

bp = Blueprint('contratos', __name__, url_prefix='/contratos')


@bp.route('/')
@login_required
def index():
    contratos = Contrato.query.order_by(Contrato.nome).all()
    agora = now_local()
    dados = []
    for c in contratos:
        pago = ContratoPagamento.query.filter_by(
            contrato_id=c.id, mes=agora.month, ano=agora.year
        ).first()
        dados.append({
            'contrato': c,
            'pago_mes': pago is not None,
            'pagamento': pago,
        })
    return render_template('contratos.html', contratos=dados, mes=agora.month, ano=agora.year)


@bp.route('/salvar', methods=['POST'])
@login_required
def salvar():
    nome = request.form.get('nome', '').strip()
    valor = request.form.get('valor_mensal', '0').replace(',', '.')
    dia = request.form.get('dia_vencimento', '5')
    obs = request.form.get('observacao', '').strip()

    if not nome:
        flash('Nome obrigatorio', 'error')
        return redirect(url_for('contratos.index'))

    try:
        valor = float(valor)
    except ValueError:
        valor = 0
    try:
        dia = int(dia)
    except ValueError:
        dia = 5

    c = Contrato(nome=nome, valor_mensal=valor, dia_vencimento=dia, observacao=obs or None)
    db.session.add(c)
    db.session.commit()
    flash(f'Contrato de {nome} criado!', 'success')
    return redirect(url_for('contratos.index'))


@bp.route('/editar/<int:id>', methods=['POST'])
@login_required
def editar(id):
    c = Contrato.query.get(id)
    if not c:
        flash('Contrato nao encontrado', 'error')
        return redirect(url_for('contratos.index'))

    c.nome = request.form.get('nome', c.nome).strip()
    val = request.form.get('valor_mensal', '').replace(',', '.')
    if val:
        try:
            c.valor_mensal = float(val)
        except ValueError:
            pass
    dia = request.form.get('dia_vencimento', '')
    if dia:
        try:
            c.dia_vencimento = int(dia)
        except ValueError:
            pass
    c.observacao = request.form.get('observacao', '').strip() or None
    db.session.commit()
    flash(f'Contrato de {c.nome} atualizado!', 'success')
    return redirect(url_for('contratos.index'))


@bp.route('/pagar/<int:id>', methods=['POST'])
@login_required
def pagar(id):
    c = Contrato.query.get(id)
    if not c:
        flash('Contrato nao encontrado', 'error')
        return redirect(url_for('contratos.index'))

    agora = now_local()
    existente = ContratoPagamento.query.filter_by(
        contrato_id=id, mes=agora.month, ano=agora.year
    ).first()
    if existente:
        flash('Este mes ja foi pago!', 'warning')
        return redirect(url_for('contratos.index'))

    valor = request.form.get('valor', str(c.valor_mensal)).replace(',', '.')
    try:
        valor = float(valor)
    except ValueError:
        valor = c.valor_mensal

    p = ContratoPagamento(
        contrato_id=id, mes=agora.month, ano=agora.year,
        valor_pago=valor, observacao=request.form.get('observacao', '').strip() or None
    )
    db.session.add(p)
    db.session.commit()
    flash(f'Pagamento de {c.nome} registrado!', 'success')
    return redirect(url_for('contratos.index'))


@bp.route('/estornar/<int:id>', methods=['POST'])
@login_required
def estornar(id):
    p = ContratoPagamento.query.get(id)
    if not p:
        flash('Pagamento nao encontrado', 'error')
        return redirect(url_for('contratos.index'))
    nome = p.contrato.nome
    db.session.delete(p)
    db.session.commit()
    flash(f'Pagamento de {nome} estornado!', 'success')
    return redirect(url_for('contratos.index'))


@bp.route('/excluir/<int:id>', methods=['POST'])
@login_required
def excluir(id):
    c = Contrato.query.get(id)
    if not c:
        flash('Contrato nao encontrado', 'error')
        return redirect(url_for('contratos.index'))
    nome = c.nome
    db.session.delete(c)
    db.session.commit()
    flash(f'Contrato de {nome} excluido!', 'success')
    return redirect(url_for('contratos.index'))
