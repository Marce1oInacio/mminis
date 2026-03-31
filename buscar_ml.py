"""
buscar_ml.py — mminis
Busca produtos no Mercado Livre pelo termo que você digitar,
raspa nome, preço, imagem e link afiliado,
e AGREGA ao produtos.json existente (não sobrescreve).

USO:
  python buscar_ml.py
  > Digite o termo de busca: Hot Wheels

DEPENDÊNCIAS:
  pip install playwright beautifulsoup4
  playwright install firefox
"""

import os
import json
import re
import time
import random
import hashlib
from datetime import datetime
from urllib.parse import urljoin, quote_plus
from playwright.sync_api import sync_playwright, Page
from bs4 import BeautifulSoup
import requests
import tkinter as tk
from tkinter import simpledialog

# =============================================
# CONFIGURAÇÕES
# =============================================
ARQUIVO_SESSAO    = 'session_ml.json'   # sessão separada da Amazon
ARQUIVO_SAIDA     = 'produtos.json'     # mesmo arquivo — agrega, não sobrescreve
ARQUIVO_HISTORICO = 'deal_history.json' # histórico compartilhado com buscar_amazon.py
PRECO_MAXIMO      = 500.0
MAX_PAGINAS       = 3
MAX_PRODUTOS      = 20
MIN_VENDAS        = 0                   # mínimo de vendas
BASE_URL          = 'https://www.mercadolivre.com.br'

# — Config Telegram —
TELEGRAM_TOKEN    = "8748572165:AAF2mKNmurwRf4cV4vC4uJnUiG1nyR3zyjY"
TELEGRAM_USER_ID  = "792758999"
PLATAFORMA        = 'Mercado Livre'


# =============================================
# HISTÓRICO (compartilhado com amazon)
# =============================================

def gerar_id(titulo: str) -> str:
    normalizado = ' '.join(titulo.lower().split())
    return hashlib.md5(normalizado.encode()).hexdigest()

def load_history() -> dict:
    if os.path.exists(ARQUIVO_HISTORICO):
        try:
            with open(ARQUIVO_HISTORICO, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, dict) and 'ofertas' in data:
                return data
            elif isinstance(data, list):
                return {'ofertas': data}
        except Exception:
            pass
    return {'ofertas': []}

def save_history(history: dict):
    with open(ARQUIVO_HISTORICO, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

def ja_visto(titulo: str, history: dict, days: int = 7) -> bool:
    pid = gerar_id(titulo)
    agora = datetime.now()
    for item in history.get('ofertas', []):
        if item.get('id') == pid:
            try:
                delta = agora - datetime.fromisoformat(item['data'])
                if delta.days < days:
                    return True
            except Exception:
                pass
    return False

def registrar(titulo: str, history: dict):
    pid = gerar_id(titulo)
    for item in history.get('ofertas', []):
        if item.get('id') == pid:
            return
    history['ofertas'].append({
        'id':        pid,
        'titulo':    titulo,
        'data':      datetime.now().isoformat(),
        'plataforma': PLATAFORMA,
    })
    if len(history['ofertas']) > 500:
        history['ofertas'] = history['ofertas'][-500:]


# =============================================
# UTILITÁRIOS DE PREÇO
# =============================================

def parse_price(texto: str) -> float | None:
    if not texto:
        return None
    try:
        limpo = re.sub(r'[^\d,.]', '', texto.replace('\xa0', '').replace('\u00a0', ''))
        if ',' in limpo and '.' in limpo:
            # formato: 1.234,56
            limpo = limpo.replace('.', '').replace(',', '.')
        elif ',' in limpo:
            limpo = limpo.replace(',', '.')
        return float(limpo)
    except Exception:
        return None

def format_price(valor: float | None) -> str:
    if valor is None:
        return ''
    return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

def send_telegram_msg(texto: str, foto_url: str | None = None):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto" if foto_url else f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_USER_ID, "parse_mode": "HTML"}
    if foto_url:
        payload["photo"] = foto_url
        payload["caption"] = texto
    else:
        payload["text"] = texto
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception:
        pass


# =============================================
# CARREGAR / SALVAR produtos.json (MERGE)
# =============================================

def carregar_existentes() -> list:
    """Carrega produtos já salvos — preserva Amazon, Shopee etc."""
    if os.path.exists(ARQUIVO_SAIDA):
        try:
            with open(ARQUIVO_SAIDA, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
        except Exception:
            pass
    return []

def salvar_merge(novos: list):
    """
    Agrega novos produtos ao JSON existente.
    - Remove entradas antigas do Mercado Livre
    - Mantém Amazon, Shopee e qualquer outra plataforma intactos
    - Adiciona os novos produtos do ML no final
    """
    existentes = carregar_existentes()

    # separa os que NÃO são ML (preserva tudo)
    outros = [p for p in existentes if p.get('plataforma') != PLATAFORMA]

    # mantém ML antigos que NÃO estão sendo substituídos agora
    # (opcional: se quiser limpar os ML antigos, deixe apenas `outros`)
    ml_antigos_ids = {gerar_id(p['nome']) for p in existentes if p.get('plataforma') == PLATAFORMA}
    novos_ids      = {gerar_id(p['nome']) for p in novos}

    # ML antigos que não vieram nesta busca — mantém
    ml_manter = [
        p for p in existentes
        if p.get('plataforma') == PLATAFORMA and gerar_id(p['nome']) not in novos_ids
    ]

    final = outros + ml_manter + novos

    with open(ARQUIVO_SAIDA, 'w', encoding='utf-8') as f:
        json.dump(final, f, indent=2, ensure_ascii=False)

    return len(outros), len(ml_manter), len(novos), len(final)


# =============================================
# SCRAPING — PÁGINA DE BUSCA
# Seletores validados via Playwright codegen
# =============================================

def coletar_urls_busca(page: Page, termo: str, max_produtos: int = MAX_PRODUTOS) -> list[str]:
    """
    Usa a busca nativa do ML (barra de pesquisa) em vez de URL montada,
    exatamente como o codegen gravou.
    """
    urls = []

    print(f"  🌐 Abrindo Mercado Livre...")
    page.goto(f"{BASE_URL}/", wait_until='domcontentloaded', timeout=60000)
    time.sleep(random.uniform(2, 3))

    # digita na barra de busca — seletor do codegen
    search = page.get_by_role("combobox", name="Digite o que você quer")
    search.click()
    time.sleep(0.5)
    search.fill(termo)
    time.sleep(0.5)
    search.press("Enter")
    time.sleep(random.uniform(3, 5))

    for num_pag in range(1, MAX_PAGINAS + 1):
        print(f"  📄 Coletando página {num_pag}...")

        # scroll para carregar lazy-load
        for _ in range(5):
            page.mouse.wheel(0, 800)
            time.sleep(random.uniform(0.3, 0.6))
        time.sleep(2)

        html  = page.content()
        soup  = BeautifulSoup(html, 'html.parser')

        # seletores reais do ML — confirmados via codegen
        cards = (
            soup.select('li.ui-search-layout__item') or
            soup.select('div.poly-card') or
            soup.select('li[class*="search-layout"]')
        )
        print(f"     {len(cards)} cards encontrados")

        for card in cards:
            # link do produto — ML usa <a> com href completo
            link = (
                card.select_one('a.poly-component__title') or
                card.select_one('a.ui-search-item__group__element') or
                card.select_one('h2 a') or
                card.select_one('a[href*="mercadolivre.com.br"]')
            )
            if not link:
                continue

            href = link.get('href', '')
            if not href or 'mercadolivre.com.br' not in href:
                continue

            # remove parâmetros de rastreamento
            href_limpo = href.split('?')[0].split('#')[0]
            if href_limpo not in urls:
                urls.append(href_limpo)

        if len(urls) >= max_produtos * 2:
            break

        # navega para próxima página se existir
        if num_pag < MAX_PAGINAS:
            try:
                prox = page.locator('a.andes-pagination__link[title="Seguinte"]').first
                prox.wait_for(state='visible', timeout=4000)
                prox.click()
                time.sleep(random.uniform(3, 5))
            except Exception:
                print("     (sem próxima página)")
                break

    print(f"\n  🔗 {len(urls)} URLs coletadas no total")
    return urls


# =============================================
# SCRAPING — PÁGINA DO PRODUTO
# Seletores validados via Playwright codegen
# =============================================

def scrape_produto(page: Page, url: str) -> dict | None:
    """
    Extrai dados do produto usando os seletores reais confirmados pelo codegen:
      - Título:  heading role  (page.get_by_role("heading"))
      - Preço:   #price        (page.locator("#price"))
      - Imagem:  data-testid   (page.get_by_test_id("image-..."))
    """

    try:
        page.goto(url, wait_until='domcontentloaded', timeout=60000)
        # aguarda o elemento de preço — seletor confirmado pelo codegen
        page.wait_for_selector('#price', timeout=15000)
        time.sleep(random.uniform(1.5, 2.5))
    except Exception as e:
        print(f"       ✗ Não carregou: {e}")
        return None

    # ── TÍTULO ──────────────────────────────────────────
    # codegen: page.get_by_role("heading", name="Hot Wheels Premium...")
    titulo = None
    try:
        # tenta o heading principal da página
        el = page.locator('h1.ui-pdp-title').first
        el.wait_for(state='visible', timeout=4000)
        titulo = el.inner_text().strip()
    except Exception:
        pass

    if not titulo:
        try:
            # fallback: primeiro heading da página
            el = page.get_by_role("heading").first
            titulo = el.inner_text().strip()
        except Exception:
            pass

    if not titulo:
        return None

    # ── PREÇO ATUAL ─────────────────────────────────────
    # codegen: page.locator("#price").get_by_text("119")
    # e:       div:has-text(r"^R\$119,90$")
    preco_atual = None
    try:
        bloco = page.locator('#price')
        bloco.wait_for(state='visible', timeout=5000)

        # fração (parte inteira)
        fracao = bloco.locator('.andes-money-amount__fraction').first.inner_text().strip()
        # centavos (pode não existir)
        try:
            centavos = bloco.locator('.andes-money-amount__cents').first.inner_text().strip()
        except Exception:
            centavos = '00'

        preco_atual = parse_price(f"{fracao},{centavos}")
    except Exception:
        pass

    # fallback: regex no texto da página
    if not preco_atual:
        try:
            # codegen revelou: div com texto exato "R$119,90"
            match = re.search(r'R\$\s*([\d\.]+,\d{2})', page.content())
            if match:
                preco_atual = parse_price(match.group(1))
        except Exception:
            pass

    if not preco_atual:
        return None

    # ── PREÇO ANTIGO ────────────────────────────────────
    preco_antigo = None
    try:
        # codegen: page.locator("#pricing_price_subtitle").get_by_text("R$")
        bloco_ant = page.locator('#pricing_price_subtitle, .ui-pdp-price__original-value').first
        texto_ant = bloco_ant.inner_text()
        preco_antigo = parse_price(texto_ant)
    except Exception:
        pass

    # ── DESCONTO ────────────────────────────────────────
    desconto = 0
    try:
        pct_el = page.locator('.ui-pdp-price__second-line .ui-pdp-price__discount, .poly-price__discount').first
        pct_txt = pct_el.inner_text()
        m = re.search(r'(\d+)', pct_txt)
        if m:
            desconto = int(m.group(1))
    except Exception:
        pass

    if desconto == 0 and preco_antigo and preco_antigo > preco_atual:
        desconto = int(round((preco_antigo - preco_atual) / preco_antigo * 100))

    # ── IMAGEM ──────────────────────────────────────────
    # codegen: page.get_by_test_id("image-894710-MLA...")
    # o test-id começa com "image-" mas o número muda por produto
    foto_url = None
    try:
        # busca qualquer elemento com data-testid começando com "image-"
        img_el = page.locator('[data-testid^="image-"]').first
        img_el.wait_for(state='visible', timeout=4000)
        foto_url = img_el.get_attribute('src') or img_el.get_attribute('data-zoom')
    except Exception:
        pass

    if not foto_url:
        try:
            foto_url = page.locator('figure.ui-pdp-gallery__figure img').first.get_attribute('src')
        except Exception:
            pass

    # ── AVALIAÇÃO ───────────────────────────────────────
    avaliacao = ''
    num_aval  = ''
    try:
        aval_el = page.locator('.ui-pdp-reviews__rating__average, [class*="reviews__rating"]').first
        txt = aval_el.inner_text().strip()
        m = re.search(r'([\d,\.]+)', txt)
        avaliacao = m.group(1).replace(',', '.') if m else ''
    except Exception:
        pass

    try:
        num_el = page.locator('.ui-pdp-reviews__rating__amount, [class*="reviews__amount"]').first
        txt = num_el.inner_text().strip()
        m = re.search(r'[\d\.,]+', txt.replace('.', ''))
        num_aval = m.group(0) if m else ''
    except Exception:
        pass

    # ── VENDAS ───────────────────────────────────────────
    vendas = 0
    try:
        # Pega do subtitulo: "Novo | +10 mil vendidos"
        sub_el = page.locator('.ui-pdp-subtitle, .ui-pdp-color--BLACK.ui-pdp-size--SMALL').first
        sub_txt = sub_el.inner_text().lower()
        if 'vendido' in sub_txt:
            # "5 vendidos", "+100 vendidos", "+10 mil vendidos"
            m = re.search(r'([\d\.,]+)\s*(mil)?\s*vendido', sub_txt)
            if m:
                num_str = m.group(1).replace('.', '').replace(',', '')
                vendas = int(num_str)
                if m.group(2) == 'mil':
                    vendas *= 1000
    except Exception:
        pass

    # ── LINK AFILIADO ────────────────────────────────────
    link_afiliado = get_affiliate_link_ml(page, url)

    # ── DESCRIÇÃO AUTOMÁTICA ─────────────────────────────
    descricao = ''
    if desconto > 0:
        descricao = f'{desconto}% de desconto'
        if preco_antigo:
            descricao += f' · era {format_price(preco_antigo)}'
    elif avaliacao:
        descricao = f'Avaliação {avaliacao}★'
        if num_aval:
            descricao += f' ({num_aval} avaliações)'

    return {
        'nome':         titulo,
        'descricao':    descricao,
        'preco':        format_price(preco_atual),
        'preco_num':    preco_atual,
        'preco_antigo': format_price(preco_antigo) if preco_antigo else '',
        'desconto':     desconto,
        'plataforma':   PLATAFORMA,
        'link':         link_afiliado,
        'vendas':       vendas,
        'foto_url':     foto_url or '',
        'avaliacao':    avaliacao,
        'num_aval':     num_aval,
        'url_original': url,
        'atualizado':   datetime.now().strftime('%d/%m/%Y %H:%M'),
    }


# =============================================
# LINK AFILIADO — MERCADO LIVRE
# =============================================

def get_affiliate_link_ml(page: Page, url_original: str) -> str:
    """
    O ML Afiliados usa uma interface diferente da Amazon.
    Tenta capturar via painel de afiliados ou retorna URL limpa.
    """
    try:
        # Seletor do codegen do usuário: get_by_test_id("generate_link_button")
        botao_ok = False
        try:
            btn = page.get_by_test_id("generate_link_button").first
            btn.wait_for(state='visible', timeout=5000)
            btn.click()
            botao_ok = True
        except Exception:
            # Fallback seletores antigos
            seletores_botao = ['button:has-text("Gerar link")', 'button:has-text("Obter link")']
            for sel in seletores_botao:
                try:
                    btn = page.locator(sel).first
                    btn.wait_for(state='visible', timeout=3000)
                    btn.click()
                    botao_ok = True
                    break
                except Exception:
                    pass

        if not botao_ok:
            # Se não achou botão, tenta ver se o link já está na página (alguns casos)
            pass
        else:
            time.sleep(2)

        # Seletor do codegen do usuário para capturar o link
        # O usuário passou: get_by_test_id("text-field__label_link")
        # Vamos tentar pegar o valor do input associado ou o texto do elemento
        seletores_link = [
            '[data-testid="text-field__label_link"]', 
            '[data-testid="affiliate-link-input"]',
            'input[class*="affiliate"]'
        ]
        
        for sel in seletores_link:
            try:
                el = page.locator(sel).first
                el.wait_for(state='visible', timeout=3000)
                # Tenta pegar value (se for input) ou inner_text (se for label/div)
                val = el.get_attribute('value') or el.input_value() or el.inner_text()
                if val and 'mercadolivre.com' in val:
                    print(f"       ✅ Link afiliado capturado: {val[:40]}...")
                    return val
            except Exception:
                pass

        print("       ⚠️  Não foi possível capturar o link afiliado. Usando original.")
        return url_original

    except Exception:
        return url_original


# =============================================
# LOGIN (session_ml.json)
# =============================================

def verificar_ou_fazer_login(browser):
    """Carrega sessão salva ou abre login manual."""
    ctx_args = {
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
        'viewport': {'width': 1440, 'height': 900},
    }
    if os.path.exists(ARQUIVO_SESSAO):
        ctx_args['storage_state'] = ARQUIVO_SESSAO
        print("  🔐 Sessão Mercado Livre carregada\n")
        return browser.new_context(**ctx_args)

    # Sem sessão: abre login manual
    print("""
  ⚠️  Sessão do Mercado Livre não encontrada.
  O navegador vai abrir para você fazer login.
  Após logar, volte aqui e pressione ENTER.
""")
    context = browser.new_context(**ctx_args)
    page    = context.new_page()
    page.goto('https://www.mercadolivre.com.br/', wait_until='domcontentloaded')

    print(f"  👉 Use a janela de pop-up para continuar...")
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    simpledialog.askstring("Login Mercado Livre", "Faça login no navegador que abriu.\nDepois de logado, clique OK aqui ou pressione Enter.", initialvalue="OK")
    root.destroy()

    # Salva sessão
    state = context.storage_state()
    with open(ARQUIVO_SESSAO, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    print(f"  ✅ Sessão salva em '{ARQUIVO_SESSAO}'\n")

    return context


# =============================================
# EXECUÇÃO PRINCIPAL
# =============================================

def main():
    print("=" * 55)
    print("  mminis — Buscador Mercado Livre")
    print("=" * 55)

    def gui_input(prompt, title="Mercado Livre Search", initial=""):
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        res = simpledialog.askstring(title, prompt, initialvalue=initial)
        root.destroy()
        return res

    termo = gui_input("🔍 Digite o termo de busca (ex: Hot Wheels):", "mminis — ML")
    if not termo:
        print("Cancelado ou nenhum termo digitado. Encerrando.")
        return
    termo = termo.strip()

    limite_str = gui_input(f"💰 Preço máximo em R$ (Vazio para {PRECO_MAXIMO:.0f}):", "Filtro de Preço", initial=str(int(PRECO_MAXIMO)))
    limite = float(limite_str.replace(',', '.')) if limite_str and limite_str.strip() else PRECO_MAXIMO

    qtd_str = gui_input(f"📦 Quantos produtos baixar? (Vazio para {MAX_PRODUTOS}):", "Quantidade", initial=str(MAX_PRODUTOS))
    qtd = int(qtd_str) if qtd_str and qtd_str.isdigit() else MAX_PRODUTOS

    min_vendas_str = gui_input(f"⭐ Mínimo de vendas (Vazio para {MIN_VENDAS}):", "Filtro Social", initial=str(MIN_VENDAS))
    min_vendas = int(min_vendas_str) if min_vendas_str and min_vendas_str.isdigit() else MIN_VENDAS

    print(f"\n🚀 Buscando '{termo}' no ML · R$ {limite:.2f} · {qtd} produtos · min {min_vendas} vendas\n")

    history       = load_history()
    produtos_novos = []
    ignorados_preco = 0
    ignorados_hist  = 0
    ignorados_vendas = 0

    with sync_playwright() as p:
        browser = p.firefox.launch(headless=False)
        context = verificar_ou_fazer_login(browser)
        page    = context.new_page()

        # 1. Coleta URLs
        print("📋 Coletando links dos produtos...")
        urls = coletar_urls_busca(page, termo, qtd)

        if not urls:
            print("❌ Nenhum produto encontrado. Verifique o termo e tente novamente.")
            browser.close()
            return

        # 2. Abre cada produto
        print(f"\n📦 Abrindo {min(len(urls), qtd * 2)} páginas de produto...\n")

        for i, url in enumerate(urls, 1):
            if len(produtos_novos) >= qtd:
                print(f"  ✅ Limite de {qtd} produtos atingido.")
                break

            print(f"  [{i}/{len(urls)}] {url[:70]}...")

            dados = scrape_produto(page, url)

            if not dados:
                print(f"       ✗ Sem dados\n")
                continue

            if limite > 0 and dados['preco_num'] > limite:
                print(f"       ⏭ R$ {dados['preco_num']:.2f} > limite R$ {limite:.2f}\n")
                ignorados_preco += 1
                continue

            if ja_visto(dados['nome'], history):
                print(f"       ⏭ Já visto recentemente\n")
                ignorados_hist += 1
                continue

            if min_vendas > 0 and dados.get('vendas', 0) < min_vendas:
                print(f"       ⏭ Poucas vendas ({dados.get('vendas', 0)} < {min_vendas})\n")
                ignorados_vendas += 1
                continue

            registrar(dados['nome'], history)
            produtos_novos.append(dados)

            print(f"       ✓ {dados['nome'][:55]}")
            print(f"         {dados['preco']} · {dados['desconto']}% off · {dados['avaliacao']}★\n")

            time.sleep(random.uniform(2, 4))

        browser.close()

    if not produtos_novos:
        print("❌ Nenhum produto novo foi coletado após os filtros.")
        return

    # 3. Seleção final do usuário
    print("\n" + "="*55)
    print(f"  📦 {len(produtos_novos)} PRODUTOS ENCONTRADOS")
    print("="*55)
    for idx, p in enumerate(produtos_novos, 1):
        vendas_txt = f"({p.get('vendas', 0)} vendidos)" if p.get('vendas') else ""
        print(f"  {idx:2d}. {p['nome'][:60]:60} | {p['preco']:10} {vendas_txt}")
    
    print("-" * 55)
    def gui_input(prompt, title="Excluir Produtos"):
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        res = simpledialog.askstring(title, prompt)
        root.destroy()
        return res

    excluir_str = gui_input("🚫 Digite os números para EXCLUIR (ex: 1-5,7,12)\nou deixe em branco para manter todos:", "Refinar Lista")
    
    if excluir_str:
        try:
            excluir_indices = set()
            partes = excluir_str.split(',')
            for parte in partes:
                parte = parte.strip()
                if not parte: continue
                if '-' in parte:
                    inicio, fim = map(int, parte.split('-'))
                    for i in range(inicio, fim + 1):
                        excluir_indices.add(i)
                elif parte.isdigit():
                    excluir_indices.add(int(parte))
            
            # Remove (ajustando para 0-based index)
            produtos_finais = [p for i, p in enumerate(produtos_novos, 1) if i not in excluir_indices]
            n_excluidos = len(produtos_novos) - len(produtos_finais)
            produtos_novos = produtos_finais
            print(f"  ✅ {n_excluidos} produtos removidos da lista final.")
        except Exception as e:
            print(f"  ⚠️ Erro ao processar exclusões: {e}. Mantendo lista original.")

    # 4. Salva histórico
    save_history(history)

    # 4. Merge inteligente com produtos.json
    n_outros, n_ml_antigos, n_novos, n_total = salvar_merge(produtos_novos)

    # 5. Resumo
    print("=" * 55)
    print(f"  ✅ {n_novos} produtos novos do ML adicionados")
    print(f"  🔒 {n_outros} produtos de outras plataformas preservados")
    print(f"  📦 {n_ml_antigos} produtos antigos do ML mantidos")
    print(f"  ⏭  {ignorados_preco} ignorados (preço acima do limite)")
    print(f"  ⏭  {ignorados_hist} ignorados (já vistos recentemente)")
    print(f"  ⏭  {ignorados_vendas} ignorados (poucas vendas)")
    print(f"  📄 Total no arquivo: {n_total} produtos")
    print(f"  💾 Arquivo salvo: {ARQUIVO_SAIDA}")
    print("=" * 55)

    # 6. Enviar para Telegram
    if produtos_novos:
        print(f"📤 Enviando {len(produtos_novos)} itens para seu Telegram...")
        for p in produtos_novos:
            msg = (
                f"🔵 <b>ACHADO MERCADO LIVRE!</b>\n\n"
                f"📦 <b>{p['nome'][:100]}</b>\n"
                f"✅ Por: <b>{p['preco']}</b>\n"
                f"📉 Desconto: <b>{p['desconto']}% OFF</b>\n"
                f"🏷️ Vendas: {p['vendas']}\n\n"
                f"🔗 <a href='{p['link']}'>COMPRAR AGORA</a>"
            )
            send_telegram_msg(msg, p.get('foto_url'))
            time.sleep(1)

    print("\n📤 Próximo passo: faça upload do 'produtos.json' no GitHub.")
    print("   O site vai atualizar automaticamente em ~1 minuto.\n")


if __name__ == '__main__':
    main()