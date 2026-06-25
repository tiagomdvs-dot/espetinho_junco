from datetime import datetime, timedelta, timezone
from models import db, now_local, hoje_inicio, get_data_limite, Pedido, ItemPedido, Produto, Insumo, CaixaRegistro, Configuracao, PagamentoParcial
from sqlalchemy import func
import base64
import csv
import io


def total_parcial(pedido):
    return sum(pp.valor for pp in pedido.pagamentos_parciais)


def marcar_parcial(pedido, forma_pagamento, valor):
    if pedido.status == 'pago':
        return False, 'Pedido já está pago.'
    if pedido.status == 'cancelado':
        return False, 'Pedido cancelado.'
    if valor <= 0:
        return False, 'Valor inválido.'
    total_pedido = 0
    for i in pedido.itens:
        preco = i.preco_unitario
        if preco is None:
            preco = i.produto.preco if i.produto else 0
        total_pedido += preco * i.quantidade
    pedido.total = total_pedido
    ja_pago = total_parcial(pedido)
    if ja_pago + valor > total_pedido + 0.01:
        return False, f'Valor excede o total do pedido. Já pago: R$ {ja_pago:.2f}, Restante: R$ {total_pedido - ja_pago:.2f}'
    pp = PagamentoParcial(pedido_id=pedido.id, valor=valor, forma_pagamento=forma_pagamento)
    db.session.add(pp)
    return True, None


def marcar_pago(pedido, forma_pagamento='dinheiro'):
    if pedido.status == 'pago':
        return False, 'Pedido já está pago.'
    pedido.status = 'pago'
    pedido.forma_pagamento = forma_pagamento
    pedido.pago_em = now_local()
    total = 0
    for i in pedido.itens:
        preco = i.preco_unitario
        if preco is None:
            preco = i.produto.preco if i.produto else 0
        total += preco * i.quantidade
    pedido.total = total
    pp = PagamentoParcial(pedido_id=pedido.id, valor=total, forma_pagamento=forma_pagamento)
    db.session.add(pp)
    return True, None


def processar_pagamentos(pedido, pagamentos):
    if pedido.status == 'pago':
        return False, 'Pedido já está pago.'
    total_pedido = 0
    for i in pedido.itens:
        preco = i.preco_unitario
        if preco is None:
            preco = i.produto.preco if i.produto else 0
        total_pedido += preco * i.quantidade
    total_pago = sum(p['valor'] for p in pagamentos)
    if abs(total_pago - total_pedido) > 0.01:
        return False, f'Total dos pagamentos (R$ {total_pago:.2f}) difere do total do pedido (R$ {total_pedido:.2f}).'
    pedido.status = 'pago'
    pedido.pago_em = now_local()
    pedido.total = total_pedido
    formas = [p['forma'] for p in pagamentos]
    if len(formas) == 1:
        pedido.forma_pagamento = formas[0]
    else:
        pedido.forma_pagamento = 'multi'
    for p in pagamentos:
        pp = PagamentoParcial(pedido_id=pedido.id, valor=p['valor'], forma_pagamento=p['forma'])
        db.session.add(pp)
    return True, None


def get_config(chave, default=None):
    config = Configuracao.query.filter_by(chave=chave).first()
    return config.valor if config else default


def format_currency(value):
    if value is None:
        return "R$ 0,00"
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def dashboard_data():
    inicio_hoje = hoje_inicio()
    fim_hoje = inicio_hoje + timedelta(days=1)

    # Pedidos criados hoje (para contagem e andamento)
    criados_hoje = Pedido.query.filter(
        Pedido.criado_em >= inicio_hoje,
        Pedido.criado_em < fim_hoje
    ).all()

    # Pedidos pagos hoje (para faturamento)
    pagos_hoje = Pedido.query.filter(
        Pedido.status == 'pago',
        Pedido.pago_em >= inicio_hoje,
        Pedido.pago_em < fim_hoje
    ).all()

    pedidos_mesa = [p for p in criados_hoje if p.tipo == 'mesa']
    pedidos_delivery = [p for p in criados_hoje if p.tipo == 'delivery']
    total_pedidos = len(pedidos_mesa)
    faturamento = sum(p.total or 0 for p in pagos_hoje)
    em_andamento = [p for p in criados_hoje if p.status in ('em_preparo', 'pronto')]

    itens_vendidos = {}
    for p in pagos_hoje:
        for item in p.itens:
            nome = item.produto.nome if item.produto else f"Item #{item.produto_id}"
            itens_vendidos[nome] = itens_vendidos.get(nome, 0) + item.quantidade

    mais_vendidos = sorted(itens_vendidos.items(), key=lambda x: x[1], reverse=True)[:5]

    vendas_por_pagamento = {}
    parciais = db.session.query(
        PagamentoParcial.forma_pagamento,
        db.func.sum(PagamentoParcial.valor)
    ).join(Pedido, Pedido.id == PagamentoParcial.pedido_id).filter(
        Pedido.status == 'pago',
        Pedido.pago_em >= inicio_hoje,
        Pedido.pago_em < fim_hoje
    ).group_by(PagamentoParcial.forma_pagamento).all()
    for forma, total in parciais:
        vendas_por_pagamento[forma] = vendas_por_pagamento.get(forma, 0) + (total or 0)

    dias_semana_pt = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']
    inicio_semana = hoje_inicio() - timedelta(days=hoje_inicio().weekday())
    dias = [(inicio_semana + timedelta(days=i)) for i in range(7)]
    vendas_semana = []
    for d in dias:
        d_ini = d
        d_fim = d_ini + timedelta(days=1)
        total = db.session.query(func.sum(Pedido.total)).filter(
            Pedido.status == 'pago',
            Pedido.pago_em >= d_ini,
            Pedido.pago_em < d_fim
        ).scalar() or 0
        vendas_semana.append({'dia': dias_semana_pt[d.weekday()], 'total': total})

    estoque_baixo = Insumo.query.filter(
        db.or_(
            Insumo.quantidade <= 0,
            db.and_(
                Insumo.quantidade_minima > 0,
                Insumo.quantidade <= Insumo.quantidade_minima
            )
        )
    ).order_by(Insumo.quantidade).all()

    return {
        'faturamento': faturamento,
        'total_pedidos': total_pedidos,
        'em_andamento': len(em_andamento),
        'mais_vendidos': mais_vendidos,
        'vendas_por_pagamento': vendas_por_pagamento,
        'vendas_semana': vendas_semana,
        'delivery_hoje': pedidos_delivery,
        'estoque_baixo': estoque_baixo,
    }


def exportar_relatorio_csv(dados, colunas, nome_arquivo):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(colunas)
    for linha in dados:
        writer.writerow(linha)
    return output.getvalue().encode('utf-8')


def imprimir_pedido(pedido):
    try:
        import win32print
    except ImportError:
        return False, 'pywin32 nao instalado (pip install pywin32)'

    try:
        L = 40
        enc = lambda t: str(t).encode('cp1252', errors='replace')

        def center(text):
            s = str(text)
            return ' ' * max(0, (L - len(s)) // 2) + s

        def rjust(text):
            s = str(text)
            return ' ' * max(0, L - len(s)) + s

        buf = bytearray()
        buf += b'\x1b\x40'
        buf += b'\n'
        buf += enc(center('COMANDA') + '\n')
        buf += enc(center(f'Pedido #{pedido.id}') + '\n')
        buf += enc(center(pedido.criado_em.strftime('%d/%m/%Y %H:%M')) + '\n')
        buf += b'\n'
        buf += enc('-' * L + '\n')
        buf += b'\n'
        buf += enc(f'Tipo:     {pedido.tipo.capitalize()}\n')
        if pedido.tipo == 'mesa' and pedido.mesa:
            buf += enc(f'Mesa:     {pedido.mesa.numero}\n')
        if pedido.cliente_nome:
            buf += enc(f'Cliente:  {pedido.cliente_nome}\n')
        if pedido.observacao:
            for obs in pedido.observacao.split('\n'):
                buf += enc(obs + '\n')
        buf += enc(f'Status:   {pedido.status.replace("_", " ").capitalize()}\n')
        if pedido.forma_pagamento:
            if pedido.forma_pagamento == 'multi' and pedido.pagamentos_parciais:
                formas_str = ', '.join([f"{pp.forma_pagamento.capitalize()} R${pp.valor:.2f}" for pp in pedido.pagamentos_parciais])
                buf += enc(f'Pagamento: {formas_str}\n')
            else:
                buf += enc(f'Pagamento: {pedido.forma_pagamento.capitalize()}\n')
        buf += b'\n'
        buf += enc('-' * L + '\n')
        buf += enc(center('ITENS') + '\n')
        buf += enc('-' * L + '\n')
        buf += b'\n'
        for item in pedido.itens:
            nome = item.produto.nome if item.produto else f'Item #{item.produto_id}'
            qtd_str = f'{item.quantidade}x'
            preco_str = f'R$ {item.preco_unitario * item.quantidade:.2f}'
            nome_parte = f'{qtd_str} {nome}'
            espacos = max(1, L - len(nome_parte) - len(preco_str))
            buf += enc(f'{nome_parte}{" " * espacos}{preco_str}\n')
        buf += b'\n'
        buf += enc('=' * L + '\n')
        total_str = f'Total: R$ {pedido.total:.2f}' if pedido.total else 'Total: R$ 0,00'
        buf += enc(rjust(total_str) + '\n')
        buf += enc('=' * L + '\n')
        if pedido.observacao:
            buf += b'\n'
            buf += enc('Obs:\n')
            for obs in pedido.observacao.split('\n'):
                buf += enc(f'  {obs}\n')
        buf += b'\n'
        buf += enc(center('Obrigado pela preferencia!') + '\n')
        buf += enc(center('Espetinho Junco') + '\n')
        buf += b'\n\n\n'
        buf += b'\x1d\x56\x00'

        printer_name = None
        for p in win32print.EnumPrinters(2):
            if 'HPRT' in p[2].upper():
                printer_name = p[2]
                break
        if not printer_name:
            printer_name = win32print.GetDefaultPrinter()
        printer = win32print.OpenPrinter(printer_name)
        try:
            doc_info = (f'Pedido #{pedido.id}', None, 'RAW')
            win32print.StartDocPrinter(printer, 1, doc_info)
            win32print.StartPagePrinter(printer)
            win32print.WritePrinter(printer, bytes(buf))
            win32print.EndPagePrinter(printer)
            win32print.EndDocPrinter(printer)
        finally:
            win32print.ClosePrinter(printer)
        return True, None
    except Exception as e:
        return False, str(e)
