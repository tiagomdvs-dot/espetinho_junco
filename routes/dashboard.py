from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from utils import dashboard_data
from models import db, Pedido, ItemPedido, CaixaRegistro, MovimentoEstoque

bp = Blueprint('dashboard', __name__, url_prefix='/')

@bp.route('/')
@bp.route('/dashboard')
@login_required
def index():
    if current_user.role == 'garcom':
        return redirect(url_for('pedidos.garcom'))
    if current_user.role == 'cozinha':
        return redirect(url_for('pedidos.cozinha'))
    if current_user.role == 'entregador':
        return redirect(url_for('delivery.listar'))
    dados = dashboard_data()
    return render_template('dashboard.html', dados=dados)


@bp.route('/resetar-dados', methods=['POST'])
@login_required
def resetar_dados():
    if current_user.role != 'owner':
        return jsonify({'ok': False, 'erro': 'Acesso restrito ao proprietário'}), 403

    try:
        senha = request.form.get('senha', '')
        if not current_user.check_password(senha):
            return jsonify({'ok': False, 'erro': 'Senha incorreta'}), 400

        ItemPedido.query.delete()
        Pedido.query.delete()
        CaixaRegistro.query.delete()
        MovimentoEstoque.query.delete()
        db.session.commit()

        return jsonify({'ok': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'ok': False, 'erro': str(e)}), 500
