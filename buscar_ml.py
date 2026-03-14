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

# =============================================
# CONFIGURAÇÕES
# =============================================
ARQUIVO_SESSAO    = 'session_ml.json'   # sessão separada da Amazon
ARQUIVO_SAIDA     = 'produtos.json'     # mesmo arquivo — agrega, não sobrescreve
ARQUIVO_HISTORICO = 'deal_history.json' # histórico compartilhado com buscar_amazon.py
PRECO_MAXIMO      = 500.0
MAX_PAGINAS       = 3
MAX_PRODUTOS      = 20
BASE_URL          = 'https://www.mercadolivre.com.br'
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
        # Tenta abrir o gerador de link do ML Afiliados
        seletores_botao = [
            'button[data-testid="get-link-button"]',
            'button:has-text("Gerar link")',
            'button:has-text("Obter link")',
            '#affiliate-link-button',
        ]
        for sel in seletores_botao:
            try:
                btn = page.locator(sel).first
                btn.wait_for(state='visible', timeout=3000)
                btn.click()
                time.sleep(2)
                break
            except Exception:
                pass

        # Tenta capturar o link gerado
        seletores_input = [
            'input[data-testid="affiliate-link-input"]',
            'input[class*="affiliate"]',
            'textarea[class*="affiliate"]',
        ]
        for sel in seletores_input:
            try:
                campo = page.locator(sel).first
                campo.wait_for(state='visible', timeout=2000)
                val = campo.get_attribute('value') or campo.input_value()
                if val and 'mercadolivre' in val:
                    return val
            except Exception:
                pass

        # fallback: retorna URL limpa (sem parâmetros de rastreamento do ML)
        return url_original

    except Exception:
        return url_original


# =============================================
# LOGIN (session_ml.json)
# =============================================

def verificar_ou_fazer_login(browser) -> object:
    """Carrega sessão salva ou abre login manual."""
    ctx_args = dict(
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
        viewport={'width': 1440, 'height': 900},
    )
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

    input("  👉 Pressione ENTER após estar logado no ML...")

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

    termo = input("\n🔍 Digite o termo de busca (ex: Hot Wheels): ").strip()
    if not termo:
        print("Nenhum termo digitado. Encerrando.")
        return

    limite_str = input(f"💰 Preço máximo em R$ (Enter para usar {PRECO_MAXIMO:.0f}): ").strip()
    limite = float(limite_str.replace(',', '.')) if limite_str else PRECO_MAXIMO

    qtd_str = input(f"📦 Quantos produtos quer baixar? (Enter para usar {MAX_PRODUTOS}): ").strip()
    qtd = int(qtd_str) if qtd_str.isdigit() and int(qtd_str) > 0 else MAX_PRODUTOS

    print(f"\n🚀 Buscando '{termo}' no ML · preço máximo: R$ {limite:.2f} · limite: {qtd} produtos\n")

    history       = load_history()
    produtos_novos = []
    ignorados_preco = 0
    ignorados_hist  = 0

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

            registrar(dados['nome'], history)
            produtos_novos.append(dados)

            print(f"       ✓ {dados['nome'][:55]}")
            print(f"         {dados['preco']} · {dados['desconto']}% off · {dados['avaliacao']}★\n")

            time.sleep(random.uniform(2, 4))

        browser.close()

    # 3. Salva histórico
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
    print(f"  📄 Total no arquivo: {n_total} produtos")
    print(f"  💾 Arquivo salvo: {ARQUIVO_SAIDA}")
    print("=" * 55)
    print("\n📤 Próximo passo: faça upload do 'produtos.json' no GitHub.")
    print("   O site vai atualizar automaticamente em ~1 minuto.\n")


if __name__ == '__main__':
    main()