import requests, json, re, sys, os
from datetime import datetime, timedelta

BASE = "http://127.0.0.1:5000"
erros = []
passos = 0

def test(nome, fn):
    global passos
    passos += 1
    try:
        fn()
        print(f"  OK - {nome}")
    except Exception as e:
        print(f"  FAIL - {nome}: {e}")
        erros.append(nome)


def get_ativos(s):
    return s.get(f"{BASE}/pedidos/api/pedidos-ativos").json()


def criar_pedido(s, mesa_id, prod_list):
    itens = json.dumps([{"produto_id": pid, "quantidade": qtd} for pid, qtd in prod_list])
    s.post(f"{BASE}/pedidos/criar-completo",
           data={"tipo": "mesa", "mesa_id": str(mesa_id), "itens": itens}, allow_redirects=True)
    ativos = get_ativos(s)
    if not ativos:
        return None
    return max(ativos, key=lambda x: x["id"])


print("=== TESTE FUNCIONAL COMPLETO ===")
print()

# -- Login como admin --
s = requests.Session()
s.post(f"{BASE}/auth/login", data={"nome": "admin", "senha": "admin"}, allow_redirects=True)

# -- Descobrir produtos --
r = s.get(f"{BASE}/cardapio/api/listar")
produtos = r.json()
test("Produtos carregados", lambda: len(produtos) > 0)
p1 = produtos[0]
print(f"  Produto exemplo: {p1['nome']} (ID {p1['id']}) R$ {p1['preco']}")

# -- Descobrir mesas --
r = s.get(f"{BASE}/pedidos/garcom")
mesa_ids = re.findall(r'<option value="(\d+)"\s*>', r.text)
test("Mesas encontradas", lambda: len(mesa_ids) >= 3)
print(f"  Mesas: {mesa_ids}")

if not produtos or len(mesa_ids) < 3:
    print("\nERRO: Produtos ou mesas insuficientes. Execute o seed primeiro.")
    sys.exit(1)

print()

# =============================================
print("--- PEDIDOS ---")

p = criar_pedido(s, mesa_ids[0], [(p1["id"], 2)])
test("Criar pedido completo", lambda: p is not None and p["id"] > 0)
if not p:
    print("  ERRO: Nao foi possivel criar pedido, abortando.")
    sys.exit(1)
pedido_id = p["id"]
print(f"  Pedido #{pedido_id} criado, Total: R$ {p['total']:.2f}")

# Adicionar item
r = s.post(f"{BASE}/pedidos/adicionar-item",
           data={"pedido_id": str(pedido_id), "produto_id": str(p1["id"]),
                 "quantidade": "1"}, allow_redirects=True)
test("Adicionar item ao pedido", lambda: r.status_code in (200, 302))

# Verificar nos ativos
ativos = get_ativos(s)
test("Pedido aparece nos ativos", lambda: pedido_id in [a["id"] for a in ativos])

# API pedidos ativos
r = s.get(f"{BASE}/pedidos/api/pedidos-ativos")
test("API pedidos ativos", lambda: r.status_code == 200 and len(r.json()) > 0)

# Bloquear 'entregue' em pedido mesa
r_ent = s.get(f"{BASE}/pedidos/status/{pedido_id}/entregue", allow_redirects=True)
test("Bloquear 'entregue' em pedido mesa", lambda: r_ent.status_code in (200, 302))
# Verificar pelo API que status NAO mudou para 'entregue'
r_after = s.get(f"{BASE}/pedidos/api/pedidos-ativos")
r_after_json = r_after.json()
pedido_after = next((a for a in r_after_json if a["id"] == pedido_id), None)
test("Status mesa permanece (nao virou entregue)", lambda: pedido_after is None or pedido_after["status"] != "entregue")

print()

# =============================================
print("--- PAGAMENTO ---")

ativos = get_ativos(s)
pedido_atual = next((a for a in ativos if a["id"] == pedido_id), None)
total = pedido_atual["total"] if pedido_atual else 0

r = s.post(f"{BASE}/caixa/pagar", data={
    "pedido_id": str(pedido_id),
    "pagamentos": json.dumps([{"forma": "dinheiro", "valor": total}])
}, allow_redirects=True)
test("Pagamento unico (dinheiro)", lambda: r.status_code in (200, 302))

ativos = get_ativos(s)
test("Pedido pago removido dos ativos", lambda: pedido_id not in [a["id"] for a in ativos])

print()

# =============================================
print("--- PAGAMENTO DIVIDIDO ---")

p_split = criar_pedido(s, mesa_ids[1], [(p1["id"], 1)])
test("Criar pedido para split", lambda: p_split is not None)
if p_split:
    total_s = p_split["total"]
    v1 = round(total_s / 3, 2)
    v2 = round(total_s / 3, 2)
    v3 = round(total_s - v1 - v2, 2)
    r = s.post(f"{BASE}/caixa/pagar", data={
        "pedido_id": str(p_split["id"]),
        "pagamentos": json.dumps([
            {"forma": "dinheiro", "valor": v1},
            {"forma": "pix", "valor": v2},
            {"forma": "cartao", "valor": v3}
        ])
    }, allow_redirects=True)
    test("Pagamento dividido (dinheiro+pix+cartao)", lambda: r.status_code in (200, 302))
    ativos = get_ativos(s)
    test("Split pedido removido dos ativos", lambda: p_split["id"] not in [a["id"] for a in ativos])

print()

# =============================================
print("--- GARCOM ---")

p_g = criar_pedido(s, mesa_ids[2], [(p1["id"], 1)])
test("Criar pedido p/ garcom", lambda: p_g is not None)
if p_g:
    r = s.post(f"{BASE}/pedidos/finalizar-mesa", data={
        "pedido_id": str(p_g["id"]),
        "forma_pagamento": "pix"
    }, allow_redirects=True)
    test("Finalizar mesa modo normal (pix)", lambda: r.status_code in (200, 302))

p_gs = criar_pedido(s, mesa_ids[0], [(p1["id"], 1)])
if p_gs:
    m = round(p_gs["total"] / 2, 2)
    r = s.post(f"{BASE}/pedidos/finalizar-mesa", data={
        "pedido_id": str(p_gs["id"]),
        "pagamentos": json.dumps([
            {"forma": "dinheiro", "valor": m},
            {"forma": "cartao", "valor": round(p_gs["total"] - m, 2)}
        ])
    }, allow_redirects=True)
    test("Finalizar mesa com split (dinheiro+cartao)", lambda: r.status_code in (200, 302))

print()

# =============================================
print("--- CANCELAMENTO ---")

p_c = criar_pedido(s, mesa_ids[1], [(p1["id"], 1)])
test("Criar pedido p/ cancelar", lambda: p_c is not None)
if p_c:
    r = s.get(f"{BASE}/pedidos/status/{p_c['id']}/cancelado", allow_redirects=True)
    test("Cancelar pedido", lambda: r.status_code in (200, 302))
    ativos = get_ativos(s)
    test("Pedido cancelado removido dos ativos", lambda: p_c["id"] not in [a["id"] for a in ativos])

print()

# =============================================
print("--- DELIVERY ---")

itens_del = json.dumps([{"produto_id": p1["id"], "quantidade": 1}])
r = s.post(f"{BASE}/cardapio/online/pedir",
           data={"cliente_nome": "Teste Delivery", "endereco": "Rua ABC, 123",
                 "telefone": "11999999999", "forma_pagamento": "dinheiro",
                 "troco": "50", "itens": itens_del}, allow_redirects=True)
test("Pedido delivery online", lambda: r.status_code in (200, 302))

# Avancar status delivery
r_all = s.get(f"{BASE}/delivery/")
ids_del = re.findall(r"Pedido #(\d+)", r_all.text)
if ids_del:
    last_del = ids_del[-1]
    for status in ["pronto", "saiu_para_entrega", "entregue"]:
        r2 = s.get(f"{BASE}/delivery/status/{last_del}/{status}", allow_redirects=True)
        test(f"Delivery status -> {status}", lambda r2=r2: r2.status_code in (200, 302))

print()

# =============================================
print("--- COZINHA ---")

# 1. Toggle produzi_cozinha em um produto de bebida (sem insumo) ou adicionar estoque
# Busca um produto existente e ativa produzi_cozinha nele
r = s.get(f"{BASE}/cardapio/")
# Find a product by scraping the edit button onclick
# editProduto(ID, 'NOME', PRECO, 'TIPO', 'CATEGORIA_ID', 'INSUMO_ID', 'QTD_INSUMO', BOOL)
match_coz = re.search(
    r"editProduto\((\d+),\s*'([^']*)',\s*([\d.]+),\s*'([^']*)',\s*'([^']*)',\s*'([^']*)',\s*'([^']*)',\s*(true|false)\)",
    r.text
)
if match_coz:
    coz_prod_id = int(match_coz.group(1))
    coz_prod_nome = match_coz.group(2)
    coz_preco = match_coz.group(3)
    coz_tipo = match_coz.group(4)
    coz_cat_id = match_coz.group(5)
    coz_insumo_id = match_coz.group(6)
    coz_qtd_insumo = match_coz.group(7)
    coz_flag_old = match_coz.group(8)  # 'true' or 'false'

    test("Produto encontrado para cozinha", lambda: coz_prod_id > 0)

    # Se ja tem produzi_cozinha, usa; se nao, ativa
    if coz_flag_old == 'false':
        r_salvar = s.post(f"{BASE}/cardapio/salvar", data={
            "id": str(coz_prod_id),
            "nome": coz_prod_nome,
            "preco": coz_preco,
            "tipo": coz_tipo,
            "categoria_id": coz_cat_id,
            "insumo_id": coz_insumo_id,
            "qtd_insumo": coz_qtd_insumo,
            "ativo": "on",
            "produzido_cozinha": "on"
        }, allow_redirects=True)
        test("Ativar produzi_cozinha no produto", lambda: r_salvar.status_code in (200, 302))

    # Adiciona estoque se o produto tiver insumo
    if coz_insumo_id and coz_insumo_id.isdigit():
        s.post(f"{BASE}/estoque/movimento", data={
            "insumo_id": coz_insumo_id,
            "tipo": "entrada",
            "quantidade": "100"
        }, allow_redirects=True)

    # 2. Criar pedido com esse produto
    p_coz = criar_pedido(s, mesa_ids[0], [(coz_prod_id, 1)])
    test("Criar pedido para cozinha", lambda: p_coz is not None)

    if p_coz:
        coz_pedido_id = p_coz["id"]
        print(f"  Pedido #{coz_pedido_id} criado para cozinha")

        # 3. Cozinha page mostra o pedido
        r_coz = s.get(f"{BASE}/pedidos/cozinha")
        test("Pagina cozinha carrega", lambda: r_coz.status_code == 200)
        test("Pedido aparece na cozinha", lambda: f"Pedido #{coz_pedido_id}" in r_coz.text)

        # 4. Scrape item-pronto URLs da pagina cozinha
        item_urls = re.findall(rf'href="[^"]*/pedidos/item-pronto/(\d+)"', r_coz.text)
        test("Items encontrados na cozinha", lambda: len(item_urls) > 0)

        if item_urls:
            first_item_id = item_urls[0]
            test(f"Item ID {first_item_id} encontrado na pagina", lambda: True)

            # 5. Toggle item como pronto
            r_toggle = s.get(f"{BASE}/pedidos/item-pronto/{first_item_id}", allow_redirects=True)
            test("Toggle item como pronto", lambda: r_toggle.status_code in (200, 302))

            # 6. Verificar riscado (item-feito) na cozinha
            r_coz2 = s.get(f"{BASE}/pedidos/cozinha")
            test("Pagina cozinha apos toggle", lambda: r_coz2.status_code == 200)
            test("Item marcado como pronto (riscado)", lambda: "item-feito" in r_coz2.text)

            # 7. Toggle de volta (desmarcar)
            r_toggle2 = s.get(f"{BASE}/pedidos/item-pronto/{first_item_id}", allow_redirects=True)
            test("Desmarcar item como pronto", lambda: r_toggle2.status_code in (200, 302))

            r_coz3 = s.get(f"{BASE}/pedidos/cozinha")
            test("Item desmarcado (sem riscado)", lambda: "item-feito" not in r_coz3.text or "fa-circle" in r_coz3.text)

        # 8. Batch Pronto
        r_pronto = s.get(f"{BASE}/pedidos/status/{coz_pedido_id}/pronto", allow_redirects=True)
        test("Batch Pronto (status->pronto)", lambda: r_pronto.status_code in (200, 302))

        # Verificar status na cozinha
        r_coz4 = s.get(f"{BASE}/pedidos/cozinha")
        test("Pedido aparece como Pronto", lambda: f"Pedido #{coz_pedido_id}" in r_coz4.text)

        # Pagar para limpeza
        ativos_coz = get_ativos(s)
        pedido_coz_ativo = next((a for a in ativos_coz if a["id"] == coz_pedido_id), None)
        if pedido_coz_ativo:
            total_coz = pedido_coz_ativo["total"]
            s.post(f"{BASE}/caixa/pagar", data={
                "pedido_id": str(coz_pedido_id),
                "pagamentos": json.dumps([{"forma": "dinheiro", "valor": total_coz}])
            }, allow_redirects=True)

        # 9. Restaurar flag original se mudou
        if coz_flag_old == 'false':
            s.post(f"{BASE}/cardapio/salvar", data={
                "id": str(coz_prod_id),
                "nome": coz_prod_nome,
                "preco": coz_preco,
                "tipo": coz_tipo,
                "categoria_id": coz_cat_id,
                "insumo_id": coz_insumo_id,
                "qtd_insumo": coz_qtd_insumo,
                "ativo": "on"
            }, allow_redirects=True)

    else:
        print("  AVISO: Nao foi possivel criar pedido de cozinha (estoque)")
else:
    print("  AVISO: Nao foi possivel extrair dados de produto do cardapio")

# =============================================
# Delivery na Cozinha: pedidos delivery mostram TODOS os itens (mesmo sem cozinha flag)
print()
print("--- DELIVERY NA COZINHA ---")

# Encontrar um produto SEM produzi_cozinha (bebida)
prod_bebida = None
for prod in produtos:
    if prod.get("tipo") == "bebida":
        prod_bebida = prod
        break
if prod_bebida is None:
    # fallback: qualquer produto que nao seja o primeiro
    prod_bebida = produtos[-1] if len(produtos) > 1 else None

if prod_bebida:
    bebida_id = prod_bebida["id"]
    bebida_nome = prod_bebida["nome"]
    print(f"  Produto nao-cozinha: {bebida_nome} (ID {bebida_id})")

    # Scrape cardapio page for this product's insumo_id
    r_card = s.get(f"{BASE}/cardapio/")
    pat_beb = rf"editProduto\(\s*{bebida_id}\s*,\s*'([^']*)'\s*,\s*([\d.]+)\s*,\s*'([^']*)'\s*,\s*'([^']*)'\s*,\s*'([^']*)'\s*,\s*'([^']*)'\s*,\s*(true|false)\)"
    match_beb = re.search(pat_beb, r_card.text)
    if match_beb:
        beb_insumo_id = match_beb.group(6)
        if beb_insumo_id and beb_insumo_id.isdigit():
            s.post(f"{BASE}/estoque/movimento", data={
                "insumo_id": beb_insumo_id,
                "tipo": "entrada",
                "quantidade": "100"
            }, allow_redirects=True)

    # Create delivery order with ONLY the non-cozinha product
    itens_del_coz = json.dumps([{"produto_id": bebida_id, "quantidade": 2}])
    s.post(f"{BASE}/cardapio/online/pedir",
           data={"cliente_nome": "Teste Cozinha Delivery",
                 "endereco": "Rua XYZ, 456",
                 "telefone": "11988888888",
                 "forma_pagamento": "dinheiro",
                 "troco": "50",
                 "itens": itens_del_coz}, allow_redirects=True)

    # Extract delivery pedido ID from delivery page
    r_del_list = s.get(f"{BASE}/delivery/")
    test("Pagina delivery carrega", lambda: r_del_list.status_code == 200)
    ids_del_coz = re.findall(r"Pedido #(\d+)", r_del_list.text)
    del_coz_pedido_id = ids_del_coz[0] if ids_del_coz else None
    if del_coz_pedido_id:
        print(f"  Delivery #{del_coz_pedido_id} criado")

        # Check cozinha page shows delivery order
        r_coz_del = s.get(f"{BASE}/pedidos/cozinha")
        test("Cozinha mostra delivery (bebida)", lambda: f"Pedido #{del_coz_pedido_id}" in r_coz_del.text)
        test("Cozinha mostra icone delivery", lambda: "fa-motorcycle" in r_coz_del.text)
        # The non-cozinha product name should appear as a kitchen item
        test("Item bebida visivel na cozinha", lambda: bebida_nome in r_coz_del.text)

        # Avancar status delivery
        for status in ["pronto", "saiu_para_entrega", "entregue"]:
            r2 = s.get(f"{BASE}/delivery/status/{del_coz_pedido_id}/{status}", allow_redirects=True)
            test(f"Delivery cozinha status -> {status}", lambda r2=r2: r2.status_code in (200, 302))
    else:
        test("Delivery pedido ID encontrado", lambda: False)
else:
    print("  AVISO: Nenhum produto bebida encontrado para teste")

print()

# =============================================
print("--- FINANCEIRO ---")

r = s.get(f"{BASE}/financeiro/")
test("Pagina financeiro carrega", lambda: r.status_code == 200)

# Criar despesa
r = s.post(f"{BASE}/financeiro/salvar", data={
    "descricao": "Conta de energia",
    "tipo": "saida",
    "valor": "350,00",
    "categoria": "Energia",
    "observacao": "teste automatizado"
}, allow_redirects=True)
test("Criar despesa", lambda: r.status_code in (200, 302))

# Criar outra despesa
r = s.post(f"{BASE}/financeiro/salvar", data={
    "descricao": "Aluguel",
    "tipo": "saida",
    "valor": "2500,00",
    "categoria": "Aluguel",
}, allow_redirects=True)
test("Criar segunda despesa", lambda: r.status_code in (200, 302))

# Verificar lancamentos na pagina
r = s.get(f"{BASE}/financeiro/")
test("Financeiro mostra despesas", lambda: "Conta de energia" in r.text and "Aluguel" in r.text)

# Verificar saldo mensal (vem dos pedidos pagos no sistema)
r3 = s.get(f"{BASE}/financeiro/")
test("Faturamento aparece na pagina", lambda: "Faturamento" in r3.text)
test("Saldo final calculado", lambda: "Saldo Final" in r3.text)

# Remover lancamento (excluir)
lanc_match = re.findall(r"financeiro/excluir/(\d+)", r.text)
if lanc_match:
    first = lanc_match[0]
    r_del = s.post(f"{BASE}/financeiro/excluir/{first}", allow_redirects=True)
    test(f"Excluir despesa #{first}", lambda: r_del.status_code in (200, 302))
    r2 = s.get(f"{BASE}/financeiro/")
    test("Despesa excluida da pagina", lambda: "Conta de energia" not in r2.text or "Aluguel" not in r2.text)

print()

# =============================================
print("--- CONTRATOS ---")

r = s.get(f"{BASE}/contratos/")
test("Pagina contratos carrega", lambda: r.status_code == 200)

r = s.post(f"{BASE}/contratos/salvar", data={
    "nome": "Empresa XYZ",
    "valor_mensal": "1500,00",
    "dia_vencimento": "10",
    "observacao": "Almoco empresarial"
}, allow_redirects=True)
test("Criar contrato", lambda: r.status_code in (200, 302))

r = s.get(f"{BASE}/contratos/")
test("Contrato na pagina", lambda: "Empresa XYZ" in r.text and "R$ 1500" in r.text)

# Pagar contrato
r = s.post(f"{BASE}/contratos/pagar/1", data={"valor": "1500,00"}, allow_redirects=True)
test("Pagar contrato", lambda: r.status_code in (200, 302))

r = s.get(f"{BASE}/contratos/")
test("Contrato marcado pago", lambda: "Pago" in r.text)

print()

# =============================================
print("--- RELATORIOS ---")

hoje = datetime.now()
ini30 = (hoje - timedelta(days=30)).strftime('%Y-%m-%d')
hj = hoje.strftime('%Y-%m-%d')
param_data = f"data_inicial={ini30}&data_final={hj}"

r = s.get(f"{BASE}/relatorios/api/vendas-por-pagamento?{param_data}")
test("API vendas por pagamento", lambda: r.status_code == 200)
data = r.json()
formas = {it["forma"] for it in data}
for f in ["dinheiro", "pix", "cartao"]:
    test(f"Forma '{f}' nos relatorios", lambda ff=f: ff in formas)

r = s.get(f"{BASE}/relatorios/api/vendas?{param_data}")
test("API vendas", lambda: r.status_code == 200)

r = s.get(f"{BASE}/relatorios/api/resumo?{param_data}")
test("API resumo", lambda: r.status_code == 200)

r = s.get(f"{BASE}/relatorios/api/vendas-por-produto?{param_data}")
test("API vendas por produto", lambda: r.status_code == 200)

r = s.get(f"{BASE}/relatorios/exportar/csv?{param_data}&tipo=vendas")
test("Exportar CSV vendas", lambda: r.status_code == 200)

r = s.get(f"{BASE}/relatorios/exportar/csv?{param_data}&tipo=produtos")
test("Exportar CSV produtos", lambda: r.status_code == 200)

print()

# =============================================
print("--- PAGINAS ---")

for nome, url in [
    ("Dashboard", "/"),
    ("Pedidos", "/pedidos/"),
    ("Garcom", "/pedidos/garcom/"),
    ("Cozinha", "/pedidos/cozinha/"),
    ("Caixa", "/caixa/"),
    ("Cardapio", "/cardapio/"),
    ("Estoque", "/estoque/"),
    ("Relatorios", "/relatorios/"),
    ("Configuracoes", "/configuracoes/"),
    ("Delivery", "/delivery/"),
    ("Cardapio Online", "/cardapio/online"),
    ("Consultar Pedido", "/cardapio/online/status"),
]:
    is_public = "Online" in nome or "Consultar" in nome
    r = (requests if is_public else s).get(f"{BASE}{url}")
    test(f"Pagina {nome}", lambda r=r: r.status_code == 200)

print()

# =============================================
print("=== RESUMO ===")
print(f"Passos: {passos}")
if not erros:
    print("TODOS OS TESTES PASSARAM!")
    sys.exit(0)
else:
    print(f"FALHAS ({len(erros)}):")
    for e in erros:
        print(f"  - {e}")
    sys.exit(1)
