import os
import sys

from app import app
from models import db, User, Categoria, Produto, Insumo

# ─── CATEGORIAS DO CARDÁPIO ───
CATEGORIAS = [
    'Espetos Tradicionais', 'Espetos Premium', 'Acompanhamentos',
    'Cervejas 600ml', 'Long Neck', 'Refrigerantes',
]

# ─── PRODUTOS DO CARDÁPIO ───
PRODUTOS = [
    {'nome': 'Carne',               'preco': 10.00, 'tipo': 'espetinho',    'categoria': 'Espetos Tradicionais', 'cozinha': True},
    {'nome': 'Frango',              'preco': 10.00, 'tipo': 'espetinho',    'categoria': 'Espetos Tradicionais', 'cozinha': True},
    {'nome': 'Linguiça',            'preco': 10.00, 'tipo': 'espetinho',    'categoria': 'Espetos Tradicionais', 'cozinha': True},
    {'nome': 'Queijo',              'preco': 10.00, 'tipo': 'espetinho',    'categoria': 'Espetos Tradicionais', 'cozinha': True},
    {'nome': 'Coração de boi',      'preco': 10.00, 'tipo': 'espetinho',    'categoria': 'Espetos Tradicionais', 'cozinha': True},
    {'nome': 'Porco',               'preco': 10.00, 'tipo': 'espetinho',    'categoria': 'Espetos Tradicionais', 'cozinha': True},
    {'nome': 'Frango com bacon',    'preco': 12.00, 'tipo': 'espetinho',    'categoria': 'Espetos Premium', 'cozinha': True},
    {'nome': 'Queijo com bacon',    'preco': 12.00, 'tipo': 'espetinho',    'categoria': 'Espetos Premium', 'cozinha': True},
    {'nome': 'Carne com bacon',     'preco': 12.00, 'tipo': 'espetinho',    'categoria': 'Espetos Premium', 'cozinha': True},
    {'nome': 'Maminha',             'preco': 12.00, 'tipo': 'espetinho',    'categoria': 'Espetos Premium', 'cozinha': True},
    {'nome': 'Cupim',               'preco': 12.00, 'tipo': 'espetinho',    'categoria': 'Espetos Premium', 'cozinha': True},
    {'nome': 'Pão de Alho',         'preco': 6.00,  'tipo': 'acompanhamento', 'categoria': 'Acompanhamentos', 'cozinha': True},
    {'nome': 'Batata e Macaxeira',  'preco': 20.00, 'tipo': 'acompanhamento', 'categoria': 'Acompanhamentos', 'cozinha': True},
    {'nome': 'Baião',               'preco': 10.00, 'tipo': 'acompanhamento', 'categoria': 'Acompanhamentos', 'cozinha': True},
    {'nome': 'Maria Isabel',        'preco': 10.00, 'tipo': 'acompanhamento', 'categoria': 'Acompanhamentos', 'cozinha': True},
    {'nome': 'Skol 600ml',          'preco': 10.00, 'tipo': 'bebida', 'categoria': 'Cervejas 600ml', 'cozinha': False},
    {'nome': 'Brahma 600ml',        'preco': 10.00, 'tipo': 'bebida', 'categoria': 'Cervejas 600ml', 'cozinha': False},
    {'nome': 'Império 600ml',       'preco': 13.00, 'tipo': 'bebida', 'categoria': 'Cervejas 600ml', 'cozinha': False},
    {'nome': 'Stella 600ml',        'preco': 15.00, 'tipo': 'bebida', 'categoria': 'Cervejas 600ml', 'cozinha': False},
    {'nome': 'Heineken 600ml',      'preco': 15.00, 'tipo': 'bebida', 'categoria': 'Cervejas 600ml', 'cozinha': False},
    {'nome': 'Budweiser Long Neck',     'preco': 10.00, 'tipo': 'bebida', 'categoria': 'Long Neck', 'cozinha': False},
    {'nome': 'Heineken Long Neck',      'preco': 10.00, 'tipo': 'bebida', 'categoria': 'Long Neck', 'cozinha': False},
    {'nome': 'Império Verde Long Neck', 'preco': 10.00, 'tipo': 'bebida', 'categoria': 'Long Neck', 'cozinha': False},
    {'nome': 'Império Ultra Long Neck', 'preco': 10.00, 'tipo': 'bebida', 'categoria': 'Long Neck', 'cozinha': False},
    {'nome': 'Amstel Ultra Long Neck',  'preco': 10.00, 'tipo': 'bebida', 'categoria': 'Long Neck', 'cozinha': False},
    {'nome': 'Coca-Cola 1L',        'preco': 10.00, 'tipo': 'bebida', 'categoria': 'Refrigerantes', 'cozinha': False},
    {'nome': 'Coca-Cola Zero 1L',   'preco': 10.00, 'tipo': 'bebida', 'categoria': 'Refrigerantes', 'cozinha': False},
    {'nome': 'Cajuína 1L',          'preco': 10.00, 'tipo': 'bebida', 'categoria': 'Refrigerantes', 'cozinha': False},
    {'nome': 'Cajuína Zero 1L',     'preco': 10.00, 'tipo': 'bebida', 'categoria': 'Refrigerantes', 'cozinha': False},
    {'nome': 'Fanta 1L',            'preco': 10.00, 'tipo': 'bebida', 'categoria': 'Refrigerantes', 'cozinha': False},
    {'nome': 'Coca-Cola 2L',        'preco': 14.00, 'tipo': 'bebida', 'categoria': 'Refrigerantes', 'cozinha': False},
    {'nome': 'Coca-Cola Zero 2L',   'preco': 14.00, 'tipo': 'bebida', 'categoria': 'Refrigerantes', 'cozinha': False},
    {'nome': 'Cajuína 2L',          'preco': 14.00, 'tipo': 'bebida', 'categoria': 'Refrigerantes', 'cozinha': False},
    {'nome': 'Coca-Cola 1,5L',      'preco': 10.00, 'tipo': 'bebida', 'categoria': 'Refrigerantes', 'cozinha': False},
    {'nome': 'Coca-Cola Zero 1,5L', 'preco': 10.00, 'tipo': 'bebida', 'categoria': 'Refrigerantes', 'cozinha': False},
]

# ─── INSUMOS (ESTOQUE) ───
INSUMOS = [
    # ── Acompanhamentos ──
    {'nome': 'Baião',           'categoria': 'acompanhamentos', 'unidade': 'porção'},
    {'nome': 'Batata',          'categoria': 'acompanhamentos', 'unidade': 'porção'},
    {'nome': 'Macaxeira',       'categoria': 'acompanhamentos', 'unidade': 'porção'},
    {'nome': 'Maria Isabel',    'categoria': 'acompanhamentos', 'unidade': 'porção'},
    {'nome': 'Pão de Alho',     'categoria': 'acompanhamentos', 'unidade': 'porção'},
    {'nome': 'Meio baião',      'categoria': 'acompanhamentos', 'unidade': 'porção'},
    {'nome': 'Pedaço de carne', 'categoria': 'acompanhamentos', 'unidade': 'un'},
    # ── Água Mineral ──
    {'nome': 'Agua mineral com gás', 'categoria': 'agua_mineral', 'unidade': 'un'},
    {'nome': 'Agua sem gás',         'categoria': 'agua_mineral', 'unidade': 'un'},
    # ── Cervejas ──
    {'nome': 'Amstel Ultra LN', 'categoria': 'cervejas',       'unidade': 'un'},
    {'nome': 'Brahma 600ml',    'categoria': 'cervejas',       'unidade': 'un'},
    {'nome': 'Budweiser LN',    'categoria': 'cervejas',       'unidade': 'un'},
    {'nome': 'Heineken 600ml',  'categoria': 'cervejas',       'unidade': 'un'},
    {'nome': 'Heineken LN',     'categoria': 'cervejas',       'unidade': 'un'},
    {'nome': 'Império 600ml',   'categoria': 'cervejas',       'unidade': 'un'},
    {'nome': 'Império Ultra LN','categoria': 'cervejas',       'unidade': 'un'},
    {'nome': 'Império Verde LN','categoria': 'cervejas',       'unidade': 'un'},
    {'nome': 'Skol 600ml',      'categoria': 'cervejas',       'unidade': 'un'},
    {'nome': 'Stella 600ml',    'categoria': 'cervejas',       'unidade': 'un'},
    {'nome': 'Ice',             'categoria': 'cervejas',       'unidade': 'un'},
    # ── Destilados ──
    {'nome': 'Dreher',          'categoria': 'destilados',     'unidade': 'un'},
    {'nome': 'Pitú',            'categoria': 'destilados',     'unidade': 'un'},
    {'nome': 'Montila',         'categoria': 'destilados',     'unidade': 'un'},
    {'nome': 'Ypioca',          'categoria': 'destilados',     'unidade': 'un'},
    # ── Espetos ──
    {'nome': 'Carne',           'categoria': 'espetos',        'unidade': 'un'},
    {'nome': 'Carne com bacon', 'categoria': 'espetos',        'unidade': 'un'},
    {'nome': 'Coração de boi',  'categoria': 'espetos',        'unidade': 'un'},
    {'nome': 'Cupim',           'categoria': 'espetos',        'unidade': 'un'},
    {'nome': 'Frango',          'categoria': 'espetos',        'unidade': 'un'},
    {'nome': 'Frango com bacon','categoria': 'espetos',        'unidade': 'un'},
    {'nome': 'Linguiça Caseira','categoria': 'espetos',        'unidade': 'un'},
    {'nome': 'Linguiça Toscana','categoria': 'espetos',        'unidade': 'un'},
    {'nome': 'Maminha',         'categoria': 'espetos',        'unidade': 'un'},
    {'nome': 'Porco',           'categoria': 'espetos',        'unidade': 'un'},
    {'nome': 'Queijo',          'categoria': 'espetos',        'unidade': 'un'},
    {'nome': 'Queijo com bacon','categoria': 'espetos',        'unidade': 'un'},
    {'nome': 'Lingua',          'categoria': 'espetos',        'unidade': 'un'},
    {'nome': 'Linguiça fina',   'categoria': 'espetos',        'unidade': 'un'},
    # ── Refrigerantes ──
    {'nome': 'Cajuína 1L',          'categoria': 'refrigerantes', 'unidade': 'un'},
    {'nome': 'Cajuína 2L',          'categoria': 'refrigerantes', 'unidade': 'un'},
    {'nome': 'Cajuína Zero 1L',     'categoria': 'refrigerantes', 'unidade': 'un'},
    {'nome': 'Coca-Cola 1,5L',      'categoria': 'refrigerantes', 'unidade': 'un'},
    {'nome': 'Coca-Cola 1L',        'categoria': 'refrigerantes', 'unidade': 'un'},
    {'nome': 'Coca-Cola 2L',        'categoria': 'refrigerantes', 'unidade': 'un'},
    {'nome': 'Coca-Cola Zero 1,5L', 'categoria': 'refrigerantes', 'unidade': 'un'},
    {'nome': 'Coca-Cola Zero 1L',   'categoria': 'refrigerantes', 'unidade': 'un'},
    {'nome': 'Coca-Cola Zero 2L',   'categoria': 'refrigerantes', 'unidade': 'un'},
    {'nome': 'Fanta 1L',            'categoria': 'refrigerantes', 'unidade': 'un'},
    {'nome': 'Cajuína em lata zero','categoria': 'refrigerantes', 'unidade': 'un'},
    {'nome': 'Cajuína',             'categoria': 'refrigerantes', 'unidade': 'un'},
    {'nome': 'Cajuína em lata',     'categoria': 'refrigerantes', 'unidade': 'un'},
    {'nome': 'Cajuína em lata fanta','categoria': 'refrigerantes', 'unidade': 'un'},
    {'nome': 'Coca em lata',        'categoria': 'refrigerantes', 'unidade': 'un'},
    {'nome': 'Coca em lata zero',   'categoria': 'refrigerantes', 'unidade': 'un'},
    {'nome': 'Fanta uva em lata',   'categoria': 'refrigerantes', 'unidade': 'un'},
    {'nome': 'Guaraná em lata',     'categoria': 'refrigerantes', 'unidade': 'un'},
    # ── Sucos ──
    {'nome': 'Acerola',             'categoria': 'sucos', 'unidade': 'un'},
    {'nome': 'Maracujá',            'categoria': 'sucos', 'unidade': 'un'},
    {'nome': 'Cajá',                'categoria': 'sucos', 'unidade': 'un'},
    {'nome': 'Caju',                'categoria': 'sucos', 'unidade': 'un'},
    {'nome': 'Goiaba',              'categoria': 'sucos', 'unidade': 'un'},
]

# ─── VÍNCULOS PRODUTO → INSUMO ───
VINCULOS = [
    ('Carne',               'Carne',           1),
    ('Frango',              'Frango',          1),
    ('Linguiça',            'Linguiça Caseira', 1),
    ('Queijo',              'Queijo',          1),
    ('Coração de boi',      'Coração de boi',  1),
    ('Porco',               'Porco',           1),
    ('Frango com bacon',    'Frango',          1),
    ('Queijo com bacon',    'Queijo',          1),
    ('Carne com bacon',     'Carne',           1),
    ('Maminha',             'Maminha',         1),
    ('Cupim',               'Cupim',           1),
    ('Pão de Alho',         'Pão de Alho',     1),
    ('Batata e Macaxeira',  'Batata',          1),
    ('Baião',               'Baião',           1),
    ('Maria Isabel',        'Maria Isabel',    1),
    ('Skol 600ml',          'Skol 600ml',      1),
    ('Brahma 600ml',        'Brahma 600ml',    1),
    ('Império 600ml',       'Império 600ml',   1),
    ('Stella 600ml',        'Stella 600ml',    1),
    ('Heineken 600ml',      'Heineken 600ml',  1),
    ('Budweiser Long Neck',     'Budweiser LN',      1),
    ('Heineken Long Neck',      'Heineken LN',       1),
    ('Império Verde Long Neck', 'Império Verde LN',  1),
    ('Império Ultra Long Neck', 'Império Ultra LN',  1),
    ('Amstel Ultra Long Neck',  'Amstel Ultra LN',   1),
    ('Coca-Cola 1L',        'Coca-Cola 1L',       1),
    ('Coca-Cola Zero 1L',   'Coca-Cola Zero 1L',  1),
    ('Cajuína 1L',          'Cajuína 1L',         1),
    ('Cajuína Zero 1L',     'Cajuína Zero 1L',    1),
    ('Fanta 1L',            'Fanta 1L',           1),
    ('Coca-Cola 2L',        'Coca-Cola 2L',       1),
    ('Coca-Cola Zero 2L',   'Coca-Cola Zero 2L',  1),
    ('Cajuína 2L',          'Cajuína 2L',         1),
    ('Coca-Cola 1,5L',      'Coca-Cola 1,5L',     1),
    ('Coca-Cola Zero 1,5L', 'Coca-Cola Zero 1,5L', 1),
]


def seed():
    with app.app_context():
        db.create_all()

        # ── Usuários ──
        if User.query.count() == 0:
            admin = User(nome='admin', role='owner')
            admin.set_password('admin')
            db.session.add(admin)
            bela = User(nome='bela', role='owner')
            bela.set_password('123456')
            db.session.add(bela)
            db.session.commit()
            print('  + Usuarios admin e bela criados')
        else:
            print('  ~ Usuarios ja existem')

        # ── Categorias do cardápio ──
        cat_map = {}
        for nome_cat in CATEGORIAS:
            cat = Categoria.query.filter_by(nome=nome_cat).first()
            if not cat:
                cat = Categoria(nome=nome_cat)
                db.session.add(cat)
                print(f"  + Categoria '{nome_cat}'")
            cat_map[nome_cat] = cat
        db.session.flush()

        # ── Produtos ──
        for p in PRODUTOS:
            existing = Produto.query.filter_by(nome=p['nome']).first()
            if existing:
                existing.preco = p['preco']
                existing.tipo = p['tipo']
                existing.categoria_id = cat_map[p['categoria']].id
                existing.ativo = True
                existing.produzido_cozinha = p.get('cozinha', False)
            else:
                produto = Produto(
                    nome=p['nome'], preco=p['preco'],
                    tipo=p['tipo'], categoria_id=cat_map[p['categoria']].id,
                    ativo=True, produzido_cozinha=p.get('cozinha', False),
                )
                db.session.add(produto)
        db.session.commit()
        print(f'  + {Produto.query.count()} produtos')

        # ── Insumos ──
        # Limpa vínculos e insumos antigos para recriar do zero
        for p in Produto.query.all():
            p.insumo_id = None
            p.qtd_insumo = None
        db.session.flush()
        for item in Insumo.query.all():
            db.session.delete(item)
        db.session.flush()
        # Cria os novos insumos
        for item in INSUMOS:
            insumo = Insumo(
                nome=item['nome'], categoria=item['categoria'],
                unidade=item['unidade'], quantidade=0,
                quantidade_minima=0, preco_unitario=0,
            )
            db.session.add(insumo)
        db.session.commit()
        print(f'  + {Insumo.query.count()} insumos (recriados)')

        # ── Vínculos ──
        for prod_nome, ins_nome, qtd in VINCULOS:
            produto = Produto.query.filter_by(nome=prod_nome).first()
            insumo = Insumo.query.filter_by(nome=ins_nome).first()
            if produto and insumo:
                produto.insumo_id = insumo.id
                produto.qtd_insumo = qtd
        db.session.commit()
        print(f'  + {len(VINCULOS)} vinculos')

        print('\n✅ Seed completo no PostgreSQL!')


if __name__ == '__main__':
    seed()
