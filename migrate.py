from app import app, db
from sqlalchemy import inspect, text

with app.app_context():
    engine = db.engine
    inspector = inspect(engine)
    is_postgres = 'postgresql' in str(engine.url)

    if not inspector.has_table('categorias_insumo'):
        if is_postgres:
            sql = """
                CREATE TABLE categorias_insumo (
                    id SERIAL PRIMARY KEY,
                    nome VARCHAR(50) NOT NULL UNIQUE,
                    icone VARCHAR(30) DEFAULT 'fa-box'
                )
            """
        else:
            sql = """
                CREATE TABLE categorias_insumo (
                    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                    nome VARCHAR(50) NOT NULL UNIQUE,
                    icone VARCHAR(30) DEFAULT 'fa-box'
                )
            """
        db.session.execute(text(sql))
        print('Tabela categorias_insumo criada!')
    else:
        print('Tabela categorias_insumo já existe.')

    colunas_insumo = [c['name'] for c in inspector.get_columns('insumos')]
    if 'produzido_cozinha' not in colunas_insumo:
        db.session.execute(text(
            'ALTER TABLE insumos ADD COLUMN produzido_cozinha BOOLEAN DEFAULT FALSE'
        ))
        print('Coluna produzido_cozinha adicionada em insumos!')
    else:
        print('Coluna produzido_cozinha já existe em insumos.')

    colunas_produto = [c['name'] for c in inspector.get_columns('produtos')]
    if 'produzido_cozinha' not in colunas_produto:
        db.session.execute(text(
            'ALTER TABLE produtos ADD COLUMN produzido_cozinha BOOLEAN DEFAULT FALSE'
        ))
        print('Coluna produzido_cozinha adicionada em produtos!')
    else:
        print('Coluna produzido_cozinha já existe em produtos.')

    db.session.commit()
    print('Migração concluída!')
