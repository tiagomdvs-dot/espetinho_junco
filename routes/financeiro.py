from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, LancamentoFinanceiro, Pedido, CATEGORIAS_FINANCEIRO
from utils import now_local
from datetime import datetime
from sqlalchemy import func

bp = Blueprint('financeiro', __name__, url_prefix='/financeiro')


@bp.route('/')
@login_required
def index():
    agora = now_local()
    mes = request.args.get('mes', type=int) or agora.month
    ano = request.args.get('ano', type=int) or agora.year

    mes_inicio = datetime(ano, mes, 1)
    if mes == 12:
        mes_fim = datetime(ano + 1, 1, 1)
    else:
        mes_fim = datetime(ano, mes + 1, 1)

    lancamentos = LancamentoFinanceiro.query.filter(
        LancamentoFinanceiro.data_lancamento >= mes_inicio,
        LancamentoFinanceiro.data_lancamento < mes_fim
    ).order_by(
        LancamentoFinanceiro.data_lancamento.desc(),
        LancamentoFinanceiro.criado_em.desc()
    ).all()

    total_despesas = db.session.query(func.sum(LancamentoFinanceiro.valor)).filter(
        LancamentoFinanceiro.tipo == 'saida',
        LancamentoFinanceiro.data_lancamento >= mes_inicio,
        LancamentoFinanceiro.data_lancamento < mes_fim
    ).scalar() or 0

    saldo_mensal = db.session.query(func.sum(Pedido.total)).filter(
        Pedido.status == 'pago',
        Pedido.pago_em >= mes_inicio,
        Pedido.pago_em < mes_fim
    ).scalar() or 0

    saldo_final = saldo_mensal - total_despesas

    if mes == agora.month and ano == agora.year:
        hoje = agora.strftime('%Y-%m-%d')
    else:
        hoje = mes_inicio.strftime('%Y-%m-%d')

    if mes == 1:
        mes_ant = 12; ano_ant = ano - 1
    else:
        mes_ant = mes - 1; ano_ant = ano
    if mes == 12:
        mes_prox = 1; ano_prox = ano + 1
    else:
        mes_prox = mes + 1; ano_prox = ano

    return render_template('financeiro.html',
                           lancamentos=lancamentos,
                           categorias=CATEGORIAS_FINANCEIRO,
                           total_despesas=total_despesas,
                           saldo_mensal=saldo_mensal,
                           saldo_final=saldo_final,
                           hoje=hoje,
                           mes=mes, ano=ano,
                           mes_ant=mes_ant, ano_ant=ano_ant,
                           mes_prox=mes_prox, ano_prox=ano_prox)


@bp.route('/salvar', methods=['POST'])
@login_required
def salvar():
    descricao = request.form.get('descricao', '').strip()
    tipo = request.form.get('tipo', 'saida')
    valor = request.form.get('valor', '0').replace(',', '.')
    categoria = request.form.get('categoria', 'outros').strip()
    data_lancamento = request.form.get('data_lancamento', '').strip()
    observacao = request.form.get('observacao', '').strip()

    if not descricao:
        flash('Descricao obrigatoria', 'error')
        return redirect(url_for('financeiro.index'))

    try:
        valor = float(valor)
    except ValueError:
        valor = 0

    if valor <= 0:
        flash('Valor deve ser positivo', 'error')
        return redirect(url_for('financeiro.index'))

    if tipo not in ('entrada', 'saida'):
        tipo = 'saida'

    data = now_local()
    if data_lancamento:
        try:
            from datetime import datetime as dt
            data = dt.strptime(data_lancamento, '%d/%m/%Y')
        except ValueError:
            try:
                data = dt.strptime(data_lancamento, '%Y-%m-%d')
            except ValueError:
                pass

    Lancamento = LancamentoFinanceiro(
        descricao=descricao,
        tipo=tipo,
        valor=valor,
        categoria=categoria,
        data_lancamento=data,
        observacao=observacao or None,
        usuario_id=current_user.id,
    )
    db.session.add(Lancamento)
    db.session.commit()

    flash('Despesa registrada!', 'success')
    return redirect(url_for('financeiro.index'))


@bp.route('/excluir/<int:id>', methods=['POST'])
@login_required
def excluir(id):
    Lancamento = LancamentoFinanceiro.query.get(id)
    if not Lancamento:
        flash('Lancamento nao encontrado', 'error')
        return redirect(url_for('financeiro.index'))
    db.session.delete(Lancamento)
    db.session.commit()
    flash('Lancamento removido!', 'success')
    return redirect(url_for('financeiro.index'))
