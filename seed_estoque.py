import sys
from app import app
from models import db, Insumo, Produto

ESTOQUE = [
    # Carnes / Espetos
    {'nome': 'Carne',           'categoria': 'espetos',        'unidade': 'un',  'preco': 0},
    {'nome': 'Frango',          'categoria': 'espetos',        'unidade': 'un',  'preco': 0},
    {'nome': 'Linguiça',        'categoria': 'espetos',        'unidade': 'un',  'preco': 0},
    {'nome': 'Queijo',          'categoria': 'espetos',        'unidade': 'un',  'preco': 0},
    {'nome': 'Coração de boi',  'categoria': 'espetos',        'unidade': 'un',  'preco': 0},
    {'nome': 'Porco',           'categoria': 'espetos',        'unidade': 'un',  'preco': 0},
    {'nome': 'Bacon',           'categoria': 'espetos',        'unidade': 'un',  'preco': 0},
    {'nome': 'Maminha',         'categoria': 'espetos',        'unidade': 'un',  'preco': 0},
    {'nome': 'Cupim',           'categoria': 'espetos',        'unidade': 'un',  'preco': 0},

    # Acompanhamentos (espetos)
    {'nome': 'Pão de Alho',     'categoria': 'espetos',        'unidade': 'un',    'preco': 0},
    {'nome': 'Arroz',           'categoria': 'espetos',        'unidade': 'kg',    'preco': 0},
    {'nome': 'Feijão',          'categoria': 'espetos',        'unidade': 'kg',    'preco': 0},

    # Acompanhamentos (porções)
    {'nome': 'Batata',          'categoria': 'acompanhamentos', 'unidade': 'porção', 'preco': 0},
    {'nome': 'Macaxeira',       'categoria': 'acompanhamentos', 'unidade': 'porção', 'preco': 0},
    {'nome': 'Baião',           'categoria': 'acompanhamentos', 'unidade': 'porção', 'preco': 0},
    {'nome': 'Maria Isabel',    'categoria': 'acompanhamentos', 'unidade': 'porção', 'preco': 0},

    # Cervejas 600ml
    {'nome': 'Skol 600ml',      'categoria': 'cervejas',       'unidade': 'un',  'preco': 0},
    {'nome': 'Brahma 600ml',    'categoria': 'cervejas',       'unidade': 'un',  'preco': 0},
    {'nome': 'Império 600ml',   'categoria': 'cervejas',       'unidade': 'un',  'preco': 0},
    {'nome': 'Stella 600ml',    'categoria': 'cervejas',       'unidade': 'un',  'preco': 0},
    {'nome': 'Heineken 600ml',  'categoria': 'cervejas',       'unidade': 'un',  'preco': 0},

    # Long Neck
    {'nome': 'Budweiser LN',    'categoria': 'cervejas',       'unidade': 'un',  'preco': 0},
    {'nome': 'Heineken LN',     'categoria': 'cervejas',       'unidade': 'un',  'preco': 0},
    {'nome': 'Império Verde LN','categoria': 'cervejas',       'unidade': 'un',  'preco': 0},
    {'nome': 'Império Ultra LN','categoria': 'cervejas',       'unidade': 'un',  'preco': 0},
    {'nome': 'Amstel Ultra LN', 'categoria': 'cervejas',       'unidade': 'un',  'preco': 0},

    # Refrigerantes
    {'nome': 'Coca-Cola 1L',    'categoria': 'refrigerantes',  'unidade': 'un',  'preco': 0},
    {'nome': 'Coca-Cola Zero 1L',  'categoria': 'refrigerantes', 'unidade': 'un', 'preco': 0},
    {'nome': 'Cajuína 1L',      'categoria': 'refrigerantes',  'unidade': 'un',  'preco': 0},
    {'nome': 'Cajuína Zero 1L', 'categoria': 'refrigerantes',  'unidade': 'un',  'preco': 0},
    {'nome': 'Fanta 1L',        'categoria': 'refrigerantes',  'unidade': 'un',  'preco': 0},
    {'nome': 'Coca-Cola 2L',    'categoria': 'refrigerantes',  'unidade': 'un',  'preco': 0},
    {'nome': 'Coca-Cola Zero 2L',  'categoria': 'refrigerantes', 'unidade': 'un', 'preco': 0},
    {'nome': 'Cajuína 2L',      'categoria': 'refrigerantes',  'unidade': 'un',  'preco': 0},
    {'nome': 'Coca-Cola 1,5L',  'categoria': 'refrigerantes',  'unidade': 'un',  'preco': 0},
    {'nome': 'Coca-Cola Zero 1,5L', 'categoria': 'refrigerantes', 'unidade': 'un', 'preco': 0},
]


def seed():
    with app.app_context():
        db.create_all()

        for item in ESTOQUE:
            existing = Insumo.query.filter_by(nome=item['nome']).first()
            if existing:
                existing.categoria = item['categoria']
                existing.unidade = item['unidade']
                existing.preco_unitario = item['preco']
                print(f"  ~ '{item['nome']}' atualizado")
            else:
                insumo = Insumo(
                    nome=item['nome'],
                    categoria=item['categoria'],
                    unidade=item['unidade'],
                    preco_unitario=item['preco'],
                    quantidade=0,
                    quantidade_minima=0,
                )
                db.session.add(insumo)
                print(f"  + '{item['nome']}' criado")

        db.session.commit()

        print("\nInsumos por categoria:")
        from models import CATEGORIAS_INSUMO
        for cat in CATEGORIAS_INSUMO:
            itens = Insumo.query.filter_by(categoria=cat).all()
            if itens:
                print(f"  {cat}:")
                for i in itens:
                    print(f"    - {i.nome} ({i.unidade})")

        print(f"\nTotal: {Insumo.query.count()} insumos")


if __name__ == '__main__':
    seed()
