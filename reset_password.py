import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from models import db, User

app = create_app()
with app.app_context():
    user = User.query.filter_by(nome='bela').first()
    if user:
        nova_senha = input(f'Nova senha para usuário "{user.nome}" (atual role: {user.role}): ')
        user.set_password(nova_senha)
        db.session.commit()
        print(f'Senha atualizada para o usuário {user.nome}!')
    else:
        print('Usuário "bela" não encontrado.')
        nome = input('Nome do novo proprietário: ')
        senha = input('Senha: ')
        user = User(nome=nome, role='owner')
        user.set_password(senha)
        db.session.add(user)
        db.session.commit()
        print(f'Usuário {nome} criado como proprietário!')
