import sys
from app import app
from models import db, Produto, Insumo

VINCULOS = [
    # Espetos Tradicionais
    ('Carne',               'Carne',          1),
    ('Frango',              'Frango',         1),
    ('Linguiça',            'Linguiça',       1),
    ('Queijo',              'Queijo',         1),
    ('Coração de boi',      'Coração de boi', 1),
    ('Porco',               'Porco',          1),

    # Espetos Premium
    ('Frango com bacon',    'Frango',         1),
    ('Queijo com bacon',    'Queijo',         1),
    ('Carne com bacon',     'Carne',          1),
    ('Maminha',             'Maminha',        1),
    ('Cupim',               'Cupim',          1),

    # Acompanhamentos
    ('Pão de Alho',         'Pão de Alho',    1),
    ('Batata e Macaxeira',  'Batata',         1),
    ('Baião',               'Baião',          1),
    ('Maria Isabel',        'Maria Isabel',   1),

    # Cervejas 600ml
    ('Skol 600ml',          'Skol 600ml',     1),
    ('Brahma 600ml',        'Brahma 600ml',   1),
    ('Império 600ml',       'Império 600ml',  1),
    ('Stella 600ml',        'Stella 600ml',   1),
    ('Heineken 600ml',      'Heineken 600ml', 1),

    # Long Neck
    ('Budweiser Long Neck',     'Budweiser LN',     1),
    ('Heineken Long Neck',      'Heineken LN',      1),
    ('Império Verde Long Neck', 'Império Verde LN', 1),
    ('Império Ultra Long Neck', 'Império Ultra LN', 1),
    ('Amstel Ultra Long Neck',  'Amstel Ultra LN',  1),

    # Refrigerantes
    ('Coca-Cola 1L',        'Coca-Cola 1L',      1),
    ('Coca-Cola Zero 1L',   'Coca-Cola Zero 1L', 1),
    ('Cajuína 1L',          'Cajuína 1L',        1),
    ('Cajuína Zero 1L',     'Cajuína Zero 1L',   1),
    ('Fanta 1L',            'Fanta 1L',          1),
    ('Coca-Cola 2L',        'Coca-Cola 2L',      1),
    ('Coca-Cola Zero 2L',   'Coca-Cola Zero 2L', 1),
    ('Cajuína 2L',          'Cajuína 2L',        1),
    ('Coca-Cola 1,5L',      'Coca-Cola 1,5L',    1),
    ('Coca-Cola Zero 1,5L', 'Coca-Cola Zero 1,5L', 1),
]


def vincular():
    with app.app_context():
        count = 0
        for prod_nome, ins_nome, qtd in VINCULOS:
            produto = Produto.query.filter_by(nome=prod_nome).first()
            insumo = Insumo.query.filter_by(nome=ins_nome).first()
            if not produto:
                print(f"  ! Produto '{prod_nome}' nao encontrado")
                continue
            if not insumo:
                print(f"  ! Insumo '{ins_nome}' nao encontrado")
                continue
            produto.insumo_id = insumo.id
            produto.qtd_insumo = qtd
            count += 1
            print(f"  + '{prod_nome}' -> '{ins_nome}' ({qtd} {insumo.unidade})")

        db.session.commit()
        print(f"\n{count} produtos vinculados a insumos!")


if __name__ == '__main__':
    vincular()
