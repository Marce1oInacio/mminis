"""
buscar_amazon.py — mminis
Busca produtos na Amazon BR pelo termo que você digitar,
raspa nome, preço, imagem e link afiliado,
e salva em produtos.json (lido pelo index.html automaticamente).

USO:
  python buscar_amazon.py
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
# CONFIGURAÇÕES — edite aqui se precisar
# =============================================
ARQUIVO_SESSAO   = 'session.json'       # sessão salva (login Amazon)
ARQUIVO_SAIDA    = 'produtos.json'      # lido pelo index.html
ARQUIVO_HISTORICO = 'deal_history.json' # evita repetir produtos
PRECO_MAXIMO     = 500.0                # ignora acima deste valor (0 = sem limite)
MAX_PAGINAS      = 3                    # quantas páginas de busca percorrer
MAX_PRODUTOS     = 20                   # máximo de produtos no JSON final
BASE_URL         = 'https://www.amazon.com.br'


# =============================================
# HISTÓRICO (evita duplicatas entre execuções)
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
        'id':    pid,
        'titulo': titulo,
        'data':  datetime.now().isoformat(),
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
        limpo = re.sub(r'[^\d,.]', '', texto.replace('\xa0', ''))
        # formato brasileiro: 1.234,56
        if ',' in limpo and '.' in limpo:
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
# SCRAPING — PÁGINA DE BUSCA
# =============================================

def coletar_urls_busca(page: Page, termo: str, max_produtos: int = MAX_PRODUTOS) -> list[str]:
    """Percorre as páginas de busca e coleta URLs de produtos."""
    urls = []
    termo_enc = quote_plus(termo)

    for num_pag in range(1, MAX_PAGINAS + 1):
        url_busca = f"{BASE_URL}/s?k={termo_enc}&page={num_pag}"
        print(f"  📄 Página {num_pag}: {url_busca}")

        try:
            page.goto(url_busca, wait_until='domcontentloaded', timeout=60000)
            time.sleep(random.uniform(2, 4))

            # scroll para carregar lazy-load
            for _ in range(4):
                page.mouse.wheel(0, 800)
                time.sleep(random.uniform(0.3, 0.7))
            time.sleep(1.5)

            html  = page.content()
            soup  = BeautifulSoup(html, 'html.parser')

            # seletor principal de resultado de busca
            cards = soup.select('div[data-component-type="s-search-result"]')
            print(f"     {len(cards)} cards encontrados")

            for card in cards:
                link = card.select_one('a.a-link-normal.s-no-outline, h2 a.a-link-normal')
                if not link:
                    continue
                href = link.get('href', '')
                if not href or '/dp/' not in href:
                    continue
                # limpa parâmetros desnecessários mantendo o ASIN
                href_limpo = href.split('?')[0].split('/ref=')[0]
                url_completa = urljoin(BASE_URL, href_limpo)
                if url_completa not in urls:
                    urls.append(url_completa)

            # para se já temos produtos suficientes
            if len(urls) >= max_produtos * 2:
                break

        except Exception as e:
            print(f"     ⚠️  Erro na página {num_pag}: {e}")
            break

        time.sleep(random.uniform(1, 2))

    print(f"\n  🔗 {len(urls)} URLs coletadas no total")
    return urls


# =============================================
# SCRAPING — PÁGINA DO PRODUTO
# =============================================

def scrape_produto(page: Page, url: str) -> dict | None:
    """Abre a página do produto e extrai todos os dados."""

    def texto(seletores: list, timeout: int = 5000) -> str | None:
        for sel in seletores:
            try:
                loc = page.locator(sel).first
                loc.wait_for(state='visible', timeout=timeout)
                t = loc.inner_text()
                if t and t.strip():
                    return t.strip()
            except Exception:
                pass
        return None

    def atributo(seletores: list, attr: str, timeout: int = 5000) -> str | None:
        for sel in seletores:
            try:
                loc = page.locator(sel).first
                loc.wait_for(state='visible', timeout=timeout)
                v = loc.get_attribute(attr)
                if v:
                    return v.strip()
            except Exception:
                pass
        return None

    try:
        page.goto(url, wait_until='domcontentloaded', timeout=60000)
        page.wait_for_selector('#productTitle', timeout=15000)
        time.sleep(random.uniform(1.5, 2.5))
    except Exception as e:
        print(f"       ✗ Não carregou: {e}")
        return None

    # — Título —
    titulo = texto(['#productTitle'])
    if not titulo:
        return None
    titulo = titulo.strip()

    # — Preço atual —
    preco_str = texto([
        '.a-price.priceToPay .a-offscreen',
        '.apexPriceToPay .a-offscreen',
        '#priceblock_ourprice',
        '#priceblock_dealprice',
        '.a-price .a-offscreen',
    ])
    preco_atual = parse_price(preco_str)
    if not preco_atual:
        return None  # sem preço, não vale

    # — Preço antigo —
    preco_ant_str = texto([
        '.a-price[data-a-strike="true"] .a-offscreen',
        '.basisPrice .a-offscreen',
        'span.a-text-price .a-offscreen',
    ])
    preco_antigo = parse_price(preco_ant_str)

    # — Desconto —
    pct_str = texto(['span.savingsPercentage', '.reinventPriceSavingsPercentageMargin'])
    if pct_str:
        m = re.search(r'(\d+)', pct_str)
        desconto = int(m.group(1)) if m else 0
    elif preco_antigo and preco_antigo > preco_atual:
        desconto = int(round((preco_antigo - preco_atual) / preco_antigo * 100))
    else:
        desconto = 0

    # — Imagem principal —
    foto_url = atributo(['#imgBlkFront', '#landingImage', '#main-image'], 'src')
    if not foto_url:
        foto_url = atributo(['#imgBlkFront', '#landingImage', '#main-image'], 'data-old-hires')

    # — Avaliação —
    avaliacao_str = texto(['#acrPopover span.a-icon-alt', 'span[data-hook="rating-out-of-text"]'])
    avaliacao = ''
    if avaliacao_str:
        m = re.search(r'([\d,\.]+)', avaliacao_str)
        avaliacao = m.group(1).replace(',', '.') if m else ''

    # — Número de avaliações —
    num_aval_str = texto(['#acrCustomerReviewText', 'span[data-hook="total-review-count"]'])
    num_aval = ''
    if num_aval_str:
        m = re.search(r'([\d\.,]+)', num_aval_str.replace('.', ''))
        num_aval = m.group(1) if m else ''

    # — Link afiliado —
    link_afiliado = get_affiliate_link(page, url)

    # — Descrição automática —
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
        'nome':       titulo,
        'descricao':  descricao,
        'preco':      format_price(preco_atual),
        'preco_num':  preco_atual,
        'preco_antigo': format_price(preco_antigo) if preco_antigo else '',
        'desconto':   desconto,
        'plataforma': 'Amazon',
        'link':       link_afiliado,
        'foto_url':   foto_url or '',
        'avaliacao':  avaliacao,
        'num_aval':   num_aval,
        'url_original': url,
        'atualizado': datetime.now().strftime('%d/%m/%Y %H:%M'),
    }


# =============================================
# LINK AFILIADO (reaproveitado do amazon_deals.py)
# =============================================

def get_affiliate_link(page: Page, url_original: str) -> str:
    try:
        seletores_botao = [
            '#amzn-ss-get-link-button',
            'button[title="Obter link"]',
            '#SL_text_link',
        ]
        botao_ok = False
        for sel in seletores_botao:
            try:
                btn = page.locator(sel).first
                btn.wait_for(state='visible', timeout=4000)
                btn.click()
                botao_ok = True
                break
            except Exception:
                pass

        if not botao_ok:
            return url_original

        time.sleep(2)

        seletores_link = [
            '#amzn-ss-text-shortlink-textarea',
            '#SL_text_short_link',
            'textarea[class*="shortlink"]',
        ]
        for sel in seletores_link:
            try:
                campo = page.locator(sel).first
                campo.wait_for(state='visible', timeout=3000)
                val = campo.get_attribute('value') or campo.input_value()
                if val and ('amzn.to' in val or 'amazon.com.br' in val):
                    return val
            except Exception:
                pass

        return url_original
    except Exception:
        return url_original


# =============================================
# CARREGAR JSON EXISTENTE (merge)
# =============================================

def carregar_existentes() -> list:
    """Carrega os produtos já no JSON para não perder os de outras plataformas."""
    if os.path.exists(ARQUIVO_SAIDA):
        try:
            with open(ARQUIVO_SAIDA, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
        except Exception:
            pass
    return []


# =============================================
# EXECUÇÃO PRINCIPAL
# =============================================

def main():
    print("=" * 55)
    print("  mminis — Buscador Amazon")
    print("=" * 55)

    termo = input("\n🔍 Digite o termo de busca (ex: Hot Wheels): ").strip()
    if not termo:
        print("Nenhum termo digitado. Encerrando.")
        return

    # opção de limite de preço
    limite_str = input(f"💰 Preço máximo em R$ (Enter para usar {PRECO_MAXIMO:.0f}): ").strip()
    limite = float(limite_str.replace(',', '.')) if limite_str else PRECO_MAXIMO

    # opção de quantidade
    qtd_str = input(f"📦 Quantos produtos quer baixar? (Enter para usar {MAX_PRODUTOS}): ").strip()
    qtd = int(qtd_str) if qtd_str.isdigit() and int(qtd_str) > 0 else MAX_PRODUTOS

    print(f"\n🚀 Buscando '{termo}' · preço máximo: R$ {limite:.2f} · limite: {qtd} produtos\n")

    history = load_history()
    produtos_novos = []
    ignorados_preco = 0
    ignorados_hist  = 0

    with sync_playwright() as p:
        browser = p.firefox.launch(headless=False)

        ctx_args = dict(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
            viewport={'width': 1440, 'height': 900},
        )
        if os.path.exists(ARQUIVO_SESSAO):
            ctx_args['storage_state'] = ARQUIVO_SESSAO
            print("  🔐 Sessão Amazon carregada\n")

        context = browser.new_context(**ctx_args)
        page    = context.new_page()

        # 1. Coleta URLs da busca
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

            # filtro preço
            if limite > 0 and dados['preco_num'] > limite:
                print(f"       ⏭ R$ {dados['preco_num']:.2f} > limite R$ {limite:.2f}\n")
                ignorados_preco += 1
                continue

            # filtro histórico
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

    # 4. Merge com existentes de outras plataformas e salva JSON
    existentes = [p for p in carregar_existentes() if p.get('plataforma') != 'Amazon']
    final      = existentes + produtos_novos

    with open(ARQUIVO_SAIDA, 'w', encoding='utf-8') as f:
        json.dump(final, f, indent=2, ensure_ascii=False)

    # 5. Resumo
    print("=" * 55)
    print(f"  ✅ {len(produtos_novos)} produtos novos salvos")
    print(f"  ⏭  {ignorados_preco} ignorados (preço acima do limite)")
    print(f"  ⏭  {ignorados_hist} ignorados (já vistos recentemente)")
    print(f"  📄 Total no arquivo: {len(final)} produtos")
    print(f"  💾 Arquivo salvo: {ARQUIVO_SAIDA}")
    print("=" * 55)
    print("\n📤 Próximo passo: faça upload do 'produtos.json' no GitHub.")
    print("   O site vai atualizar automaticamente em ~1 minuto.\n")


if __name__ == '__main__':
    main()