import sys
from app import app
from models import db, Categoria, Produto

CATEGORIAS = ['Espetos Tradicionais', 'Espetos Premium', 'Acompanhamentos',
              'Cervejas 600ml', 'Long Neck', 'Refrigerantes']

PRODUTOS = [
    # Espetos Tradicionais - R$10,00
    {'nome': 'Carne',               'preco': 10.00, 'tipo': 'espetinho',    'categoria': 'Espetos Tradicionais'},
    {'nome': 'Frango',              'preco': 10.00, 'tipo': 'espetinho',    'categoria': 'Espetos Tradicionais'},
    {'nome': 'Linguiça',            'preco': 10.00, 'tipo': 'espetinho',    'categoria': 'Espetos Tradicionais'},
    {'nome': 'Queijo',              'preco': 10.00, 'tipo': 'espetinho',    'categoria': 'Espetos Tradicionais'},
    {'nome': 'Coração de boi',      'preco': 10.00, 'tipo': 'espetinho',    'categoria': 'Espetos Tradicionais'},
    {'nome': 'Porco',               'preco': 10.00, 'tipo': 'espetinho',    'categoria': 'Espetos Tradicionais'},

    # Espetos Premium - R$12,00
    {'nome': 'Frango com bacon',    'preco': 12.00, 'tipo': 'espetinho',    'categoria': 'Espetos Premium'},
    {'nome': 'Queijo com bacon',    'preco': 12.00, 'tipo': 'espetinho',    'categoria': 'Espetos Premium'},
    {'nome': 'Carne com bacon',     'preco': 12.00, 'tipo': 'espetinho',    'categoria': 'Espetos Premium'},
    {'nome': 'Maminha',             'preco': 12.00, 'tipo': 'espetinho',    'categoria': 'Espetos Premium'},
    {'nome': 'Cupim',               'preco': 12.00, 'tipo': 'espetinho',    'categoria': 'Espetos Premium'},

    # Acompanhamentos
    {'nome': 'Pão de Alho',             'preco': 6.00,  'tipo': 'acompanhamento', 'categoria': 'Acompanhamentos'},
    {'nome': 'Batata e Macaxeira',      'preco': 20.00, 'tipo': 'acompanhamento', 'categoria': 'Acompanhamentos'},
    {'nome': 'Baião',                   'preco': 10.00, 'tipo': 'acompanhamento', 'categoria': 'Acompanhamentos'},
    {'nome': 'Maria Isabel',            'preco': 10.00, 'tipo': 'acompanhamento', 'categoria': 'Acompanhamentos'},

    # Cervejas 600ml
    {'nome': 'Skol 600ml',              'preco': 10.00, 'tipo': 'bebida', 'categoria': 'Cervejas 600ml'},
    {'nome': 'Brahma 600ml',            'preco': 10.00, 'tipo': 'bebida', 'categoria': 'Cervejas 600ml'},
    {'nome': 'Império 600ml',           'preco': 13.00, 'tipo': 'bebida', 'categoria': 'Cervejas 600ml'},
    {'nome': 'Stella 600ml',            'preco': 15.00, 'tipo': 'bebida', 'categoria': 'Cervejas 600ml'},
    {'nome': 'Heineken 600ml',          'preco': 15.00, 'tipo': 'bebida', 'categoria': 'Cervejas 600ml'},

    # Long Neck
    {'nome': 'Budweiser Long Neck',     'preco': 10.00, 'tipo': 'bebida', 'categoria': 'Long Neck'},
    {'nome': 'Heineken Long Neck',      'preco': 10.00, 'tipo': 'bebida', 'categoria': 'Long Neck'},
    {'nome': 'Império Verde Long Neck', 'preco': 10.00, 'tipo': 'bebida', 'categoria': 'Long Neck'},
    {'nome': 'Império Ultra Long Neck', 'preco': 10.00, 'tipo': 'bebida', 'categoria': 'Long Neck'},
    {'nome': 'Amstel Ultra Long Neck',  'preco': 10.00, 'tipo': 'bebida', 'categoria': 'Long Neck'},

    # Refrigerantes
    {'nome': 'Coca-Cola 1L',            'preco': 10.00, 'tipo': 'bebida', 'categoria': 'Refrigerantes'},
    {'nome': 'Coca-Cola Zero 1L',       'preco': 10.00, 'tipo': 'bebida', 'categoria': 'Refrigerantes'},
    {'nome': 'Cajuína 1L',              'preco': 10.00, 'tipo': 'bebida', 'categoria': 'Refrigerantes'},
    {'nome': 'Cajuína Zero 1L',         'preco': 10.00, 'tipo': 'bebida', 'categoria': 'Refrigerantes'},
    {'nome': 'Fanta 1L',                'preco': 10.00, 'tipo': 'bebida', 'categoria': 'Refrigerantes'},
    {'nome': 'Coca-Cola 2L',            'preco': 14.00, 'tipo': 'bebida', 'categoria': 'Refrigerantes'},
    {'nome': 'Coca-Cola Zero 2L',       'preco': 14.00, 'tipo': 'bebida', 'categoria': 'Refrigerantes'},
    {'nome': 'Cajuína 2L',              'preco': 14.00, 'tipo': 'bebida', 'categoria': 'Refrigerantes'},
    {'nome': 'Coca-Cola 1,5L',          'preco': 10.00, 'tipo': 'bebida', 'categoria': 'Refrigerantes'},
    {'nome': 'Coca-Cola Zero 1,5L',     'preco': 10.00, 'tipo': 'bebida', 'categoria': 'Refrigerantes'},
]

def seed():
    with app.app_context():
        db.create_all()

        cat_map = {}
        for nome_cat in CATEGORIAS:
            cat = Categoria.query.filter_by(nome=nome_cat).first()
            if not cat:
                cat = Categoria(nome=nome_cat)
                db.session.add(cat)
                print(f"  + Categoria '{nome_cat}' criada")
            else:
                print(f"  ~ Categoria '{nome_cat}' ja existe")
            cat_map[nome_cat] = cat
        db.session.flush()

        for p in PRODUTOS:
            existing = Produto.query.filter_by(nome=p['nome']).first()
            if existing:
                existing.preco = p['preco']
                existing.tipo = p['tipo']
                existing.categoria_id = cat_map[p['categoria']].id
                existing.ativo = True
                print(f"  ~ '{p['nome']}' atualizado")
            else:
                produto = Produto(
                    nome=p['nome'],
                    preco=p['preco'],
                    tipo=p['tipo'],
                    categoria_id=cat_map[p['categoria']].id,
                    ativo=True,
                )
                db.session.add(produto)
                print(f"  + '{p['nome']}' criado")

        db.session.commit()

        print("\nCategorias:")
        for c in Categoria.query.all():
            print(f"  - {c.nome} ({Categoria.query.count()} total)")

        print("\nProdutos por tipo:")
        for tipo in ['espetinho', 'bebida', 'acompanhamento']:
            prods = Produto.query.filter_by(tipo=tipo).all()
            print(f"  {tipo}: {len(prods)} produtos")
            for p in prods:
                print(f"    - {p.nome} (R${p.preco:.2f})")

if __name__ == '__main__':
    seed()
