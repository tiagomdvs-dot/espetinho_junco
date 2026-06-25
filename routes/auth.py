from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User

bp = Blueprint('auth', __name__, url_prefix='/auth')


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        try:
            nome = request.form.get('nome', '').strip()
            senha = request.form.get('senha', '')

            user = User.query.filter_by(nome=nome).first()
            if user and user.check_password(senha):
                login_user(user)
                next_page = request.args.get('next')
                if next_page:
                    return redirect(next_page)
                if user.role == 'entregador':
                    return redirect(url_for('delivery.listar'))
                if user.role == 'garcom':
                    return redirect(url_for('pedidos.garcom'))
                if user.role == 'cozinha':
                    return redirect(url_for('pedidos.cozinha'))
                return redirect(url_for('dashboard.index'))
            flash('Usuário ou senha inválidos', 'error')
        except Exception:
            flash('Erro interno do servidor. Tente novamente.', 'error')

    return render_template('login.html')


@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
