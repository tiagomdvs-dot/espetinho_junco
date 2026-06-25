import os
import sys
from dotenv import load_dotenv

load_dotenv()

from app import app
from models import db, User

USERS = [
    {'nome': 'admin', 'senha': 'admin', 'role': 'owner'},
    {'nome': 'bela', 'senha': '123456', 'role': 'owner'},
    {'nome': 'tiago', 'senha': '123456', 'role': 'garcom'},
    {'nome': 'sandra', 'senha': '123456', 'role': 'garcom'},
    {'nome': 'baixa', 'senha': '123456', 'role': 'cozinha'},
]

def seed():
    with app.app_context():
        db.create_all()
        for u in USERS:
            existing = User.query.filter_by(nome=u['nome']).first()
            if existing:
                existing.set_password(u['senha'])
                existing.role = u['role']
                print(f"  ~ '{u['nome']}' atualizado")
            else:
                user = User(nome=u['nome'], role=u['role'])
                user.set_password(u['senha'])
                db.session.add(user)
                print(f"  + '{u['nome']}' criado")
        db.session.commit()
        print("\nUsuarios no banco:")
        for u in User.query.all():
            print(f"  - {u.nome} ({u.role})")

if __name__ == '__main__':
    seed()
