"""
buscar_links.py — mminis
Você cola os links que achou (Amazon ou ML) no arquivo links.txt,
um por linha, e este script entra em cada um, extrai as informações
e agrega ao produtos.json.

USO:
  1. Adicione os links em links.txt (um por linha)
  2. python buscar_links.py

FORMATO DO links.txt:
  # linhas com # são comentários — ignoradas
  # Amazon
  https://www.amazon.com.br/dp/B0XXXXX
  https://amzn.to/XXXXX

  # Mercado Livre
  https://www.mercadolivre.com.br/...

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
from playwright.sync_api import sync_playwright, Page

# =============================================
# CONFIGURAÇÕES
# =============================================
ARQUIVO_LINKS     = 'links.txt'
ARQUIVO_SAIDA     = 'produtos.json'
ARQUIVO_HISTORICO = 'deal_history.json'
ARQUIVO_SESSAO_AM = 'session.json'
ARQUIVO_SESSAO_ML = 'session_ml.json'


# =============================================
# UTILITÁRIOS COMPARTILHADOS
# =============================================

def gerar_id(titulo: str) -> str:
    return hashlib.md5(' '.join(titulo.lower().split()).encode()).hexdigest()

def parse_price(texto: str) -> float | None:
    if not texto:
        return None
    try:
        limpo = re.sub(r'[^\d,.]', '', str(texto).replace('\xa0', ''))
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
                if (agora - datetime.fromisoformat(item['data'])).days < days:
                    return True
            except Exception:
                pass
    return False

def registrar(titulo: str, history: dict, plataforma: str):
    pid = gerar_id(titulo)
    for item in history.get('ofertas', []):
        if item.get('id') == pid:
            return
    history['ofertas'].append({
        'id': pid, 'titulo': titulo,
        'data': datetime.now().isoformat(),
        'plataforma': plataforma,
    })
    if len(history['ofertas']) > 500:
        history['ofertas'] = history['ofertas'][-500:]


# =============================================
# LER links.txt
# =============================================

def ler_links() -> list[str]:
    """Lê links.txt e retorna lista de URLs válidas."""
    if not os.path.exists(ARQUIVO_LINKS):
        # cria o arquivo de exemplo se não existir
        with open(ARQUIVO_LINKS, 'w', encoding='utf-8') as f:
            f.write("""# links.txt — mminis
# Cole aqui os links que você encontrou, um por linha.
# Linhas começando com # são comentários e serão ignoradas.
# Funciona com Amazon e Mercado Livre.
#
# Exemplos:
# https://www.amazon.com.br/dp/B0XXXXXXX
# https://amzn.to/XXXXXXX
# https://www.mercadolivre.com.br/...
#
""")
        print(f"\n📄 Arquivo '{ARQUIVO_LINKS}' criado.")
        print("   Cole seus links lá e rode o script novamente.\n")
        return []

    urls = []
    with open(ARQUIVO_LINKS, 'r', encoding='utf-8') as f:
        for linha in f:
            linha = linha.strip()
            if not linha or linha.startswith('#'):
                continue
            # aceita amazon, amzn.to e mercadolivre
            if any(d in linha for d in ['amazon.com.br', 'amzn.to', 'mercadolivre.com.br', 'mercadolivre.com']):
                if linha not in urls:
                    urls.append(linha)
            else:
                print(f"  ⚠️  Link ignorado (plataforma não reconhecida): {linha[:60]}")

    return urls

def detectar_plataforma(url: str) -> str:
    if 'amazon.com.br' in url or 'amzn.to' in url:
        return 'Amazon'
    if 'mercadolivre.com' in url:
        return 'Mercado Livre'
    return 'Desconhecido'


# =============================================
# SCRAPER AMAZON
# =============================================

def scrape_amazon(page: Page, url: str) -> dict | None:
    try:
        page.goto(url, wait_until='domcontentloaded', timeout=60000)
        page.wait_for_selector('#productTitle', timeout=15000)
        time.sleep(random.uniform(1.5, 2.5))
    except Exception as e:
        print(f"       ✗ Não carregou: {e}")
        return None

    def txt(sels, timeout=5000):
        for s in sels:
            try:
                el = page.locator(s).first
                el.wait_for(state='visible', timeout=timeout)
                t = el.inner_text()
                if t and t.strip():
                    return t.strip()
            except Exception:
                pass
        return None

    def attr(sels, a, timeout=5000):
        for s in sels:
            try:
                el = page.locator(s).first
                el.wait_for(state='visible', timeout=timeout)
                v = el.get_attribute(a)
                if v:
                    return v.strip()
            except Exception:
                pass
        return None

    titulo = txt(['#productTitle'])
    if not titulo:
        return None

    preco_atual  = parse_price(txt([
        '.a-price.priceToPay .a-offscreen',
        '.apexPriceToPay .a-offscreen',
        '#priceblock_ourprice', '#priceblock_dealprice',
        '.a-price .a-offscreen',
    ]))
    if not preco_atual:
        return None

    preco_antigo = parse_price(txt([
        '.a-price[data-a-strike="true"] .a-offscreen',
        '.basisPrice .a-offscreen',
        'span.a-text-price .a-offscreen',
    ]))

    pct_str  = txt(['span.savingsPercentage', '.reinventPriceSavingsPercentageMargin'])
    desconto = 0
    if pct_str:
        m = re.search(r'(\d+)', pct_str)
        desconto = int(m.group(1)) if m else 0
    elif preco_antigo and preco_antigo > preco_atual:
        desconto = int(round((preco_antigo - preco_atual) / preco_antigo * 100))

    foto_url  = attr(['#imgBlkFront', '#landingImage', '#main-image'], 'src')
    aval_str  = txt(['#acrPopover span.a-icon-alt'])
    avaliacao = ''
    if aval_str:
        m = re.search(r'([\d,\.]+)', aval_str)
        avaliacao = m.group(1).replace(',', '.') if m else ''

    num_aval_str = txt(['#acrCustomerReviewText'])
    num_aval = ''
    if num_aval_str:
        m = re.search(r'[\d\.,]+', num_aval_str.replace('.', ''))
        num_aval = m.group(0) if m else ''

    # link afiliado
    link = get_affiliate_amazon(page, url)

    descricao = ''
    if desconto > 0:
        descricao = f'{desconto}% de desconto'
        if preco_antigo:
            descricao += f' · era {format_price(preco_antigo)}'
    elif avaliacao:
        descricao = f'Avaliação {avaliacao}★' + (f' ({num_aval})' if num_aval else '')

    return {
        'nome': titulo.strip(),
        'descricao': descricao,
        'preco': format_price(preco_atual),
        'preco_num': preco_atual,
        'preco_antigo': format_price(preco_antigo) if preco_antigo else '',
        'desconto': desconto,
        'plataforma': 'Amazon',
        'link': link,
        'foto_url': foto_url or '',
        'avaliacao': avaliacao,
        'num_aval': num_aval,
        'url_original': url,
        'atualizado': datetime.now().strftime('%d/%m/%Y %H:%M'),
    }

def get_affiliate_amazon(page: Page, url_original: str) -> str:
    try:
        for sel in ['#amzn-ss-get-link-button', 'button[title="Obter link"]', '#SL_text_link']:
            try:
                btn = page.locator(sel).first
                btn.wait_for(state='visible', timeout=4000)
                btn.click()
                time.sleep(2)
                break
            except Exception:
                pass
        for sel in ['#amzn-ss-text-shortlink-textarea', '#SL_text_short_link', 'textarea[class*="shortlink"]']:
            try:
                campo = page.locator(sel).first
                campo.wait_for(state='visible', timeout=3000)
                val = campo.get_attribute('value') or campo.input_value()
                if val and ('amzn.to' in val or 'amazon.com.br' in val):
                    return val
            except Exception:
                pass
    except Exception:
        pass
    return url_original


# =============================================
# SCRAPER MERCADO LIVRE
# =============================================

def scrape_ml(page: Page, url: str) -> dict | None:
    try:
        page.goto(url, wait_until='domcontentloaded', timeout=60000)
        page.wait_for_selector('#price', timeout=15000)
        time.sleep(random.uniform(1.5, 2.5))
    except Exception as e:
        print(f"       ✗ Não carregou: {e}")
        return None

    # título
    titulo = None
    try:
        titulo = page.locator('h1.ui-pdp-title').first.inner_text().strip()
    except Exception:
        pass
    if not titulo:
        try:
            titulo = page.get_by_role("heading").first.inner_text().strip()
        except Exception:
            pass
    if not titulo:
        return None

    # preço
    preco_atual = None
    try:
        bloco  = page.locator('#price')
        fracao = bloco.locator('.andes-money-amount__fraction').first.inner_text().strip()
        try:
            cents = bloco.locator('.andes-money-amount__cents').first.inner_text().strip()
        except Exception:
            cents = '00'
        preco_atual = parse_price(f"{fracao},{cents}")
    except Exception:
        pass
    if not preco_atual:
        m = re.search(r'R\$\s*([\d\.]+,\d{2})', page.content())
        if m:
            preco_atual = parse_price(m.group(1))
    if not preco_atual:
        return None

    # preço antigo
    preco_antigo = None
    try:
        txt = page.locator('#pricing_price_subtitle, .ui-pdp-price__original-value').first.inner_text()
        preco_antigo = parse_price(txt)
    except Exception:
        pass

    # desconto
    desconto = 0
    try:
        pct = page.locator('.ui-pdp-price__second-line .ui-pdp-price__discount').first.inner_text()
        m   = re.search(r'(\d+)', pct)
        desconto = int(m.group(1)) if m else 0
    except Exception:
        pass
    if desconto == 0 and preco_antigo and preco_antigo > preco_atual:
        desconto = int(round((preco_antigo - preco_atual) / preco_antigo * 100))

    # imagem
    foto_url = None
    try:
        foto_url = page.locator('[data-testid^="image-"]').first.get_attribute('src')
    except Exception:
        pass
    if not foto_url:
        try:
            foto_url = page.locator('figure.ui-pdp-gallery__figure img').first.get_attribute('src')
        except Exception:
            pass

    # avaliação
    avaliacao = ''
    num_aval  = ''
    try:
        t = page.locator('.ui-pdp-reviews__rating__average').first.inner_text().strip()
        m = re.search(r'([\d,\.]+)', t)
        avaliacao = m.group(1).replace(',', '.') if m else ''
    except Exception:
        pass
    try:
        t = page.locator('.ui-pdp-reviews__rating__amount').first.inner_text().strip()
        m = re.search(r'[\d\.,]+', t.replace('.', ''))
        num_aval = m.group(0) if m else ''
    except Exception:
        pass

    descricao = ''
    if desconto > 0:
        descricao = f'{desconto}% de desconto'
        if preco_antigo:
            descricao += f' · era {format_price(preco_antigo)}'
    elif avaliacao:
        descricao = f'Avaliação {avaliacao}★' + (f' ({num_aval})' if num_aval else '')

    return {
        'nome': titulo,
        'descricao': descricao,
        'preco': format_price(preco_atual),
        'preco_num': preco_atual,
        'preco_antigo': format_price(preco_antigo) if preco_antigo else '',
        'desconto': desconto,
        'plataforma': 'Mercado Livre',
        'link': url,  # ML não tem gerador de link afiliado simples
        'foto_url': foto_url or '',
        'avaliacao': avaliacao,
        'num_aval': num_aval,
        'url_original': url,
        'atualizado': datetime.now().strftime('%d/%m/%Y %H:%M'),
    }


# =============================================
# MERGE INTELIGENTE
# =============================================

def carregar_existentes() -> list:
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
    Agrega novos produtos ao JSON sem sobrescrever outros.
    Para produtos manuais (de links.txt), usa o ID para
    atualizar se já existir, ou adicionar se for novo.
    """
    existentes = carregar_existentes()
    novos_por_id = {gerar_id(p['nome']): p for p in novos}

    # atualiza existentes que estão na lista de novos
    atualizados = 0
    resultado = []
    for p in existentes:
        pid = gerar_id(p['nome'])
        if pid in novos_por_id:
            resultado.append(novos_por_id.pop(pid))  # substitui com dados frescos
            atualizados += 1
        else:
            resultado.append(p)

    # adiciona os genuinamente novos
    adicionados = len(novos_por_id)
    resultado.extend(novos_por_id.values())

    with open(ARQUIVO_SAIDA, 'w', encoding='utf-8') as f:
        json.dump(resultado, f, indent=2, ensure_ascii=False)

    return atualizados, adicionados, len(resultado)


# =============================================
# EXECUÇÃO PRINCIPAL
# =============================================

def main():
    print("=" * 55)
    print("  mminis — Buscar por Links")
    print("=" * 55)

    urls = ler_links()
    if not urls:
        return

    print(f"\n📋 {len(urls)} links encontrados em '{ARQUIVO_LINKS}':\n")
    for i, url in enumerate(urls, 1):
        plat = detectar_plataforma(url)
        print(f"  {i:02d}. [{plat}] {url[:65]}...")

    confirmar = input(f"\n▶ Processar todos os {len(urls)} links? (Enter = sim / n = não): ").strip().lower()
    if confirmar == 'n':
        print("Cancelado.")
        return

    history       = load_history()
    produtos_novos = []
    erros          = []
    ignorados_hist = 0

    # verifica se precisa de sessões
    tem_amazon = any('amazon' in u or 'amzn' in u for u in urls)
    tem_ml     = any('mercadolivre' in u for u in urls)

    with sync_playwright() as p:
        browser = p.firefox.launch(headless=False)

        # contexto Amazon
        ctx_amazon = None
        if tem_amazon:
            ctx_args = dict(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
                viewport={'width': 1440, 'height': 900},
            )
            if os.path.exists(ARQUIVO_SESSAO_AM):
                ctx_args['storage_state'] = ARQUIVO_SESSAO_AM
                print("\n  🔐 Sessão Amazon carregada")
            ctx_amazon = browser.new_context(**ctx_args)
            page_amazon = ctx_amazon.new_page()

        # contexto ML
        ctx_ml = None
        if tem_ml:
            ctx_args = dict(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
                viewport={'width': 1440, 'height': 900},
            )
            if os.path.exists(ARQUIVO_SESSAO_ML):
                ctx_args['storage_state'] = ARQUIVO_SESSAO_ML
                print("  🔐 Sessão Mercado Livre carregada")
            else:
                print("\n  ⚠️  Sessão ML não encontrada. Abrindo login...")
                ctx_ml_tmp = browser.new_context(**ctx_args)
                pg_tmp = ctx_ml_tmp.new_page()
                pg_tmp.goto('https://www.mercadolivre.com.br/', wait_until='domcontentloaded')
                input("  👉 Faça login no ML e pressione ENTER...")
                state = ctx_ml_tmp.storage_state()
                with open(ARQUIVO_SESSAO_ML, 'w', encoding='utf-8') as f:
                    json.dump(state, f, indent=2)
                ctx_args['storage_state'] = ARQUIVO_SESSAO_ML
                ctx_ml_tmp.close()
            ctx_ml = browser.new_context(**ctx_args)
            page_ml = ctx_ml.new_page()

        print(f"\n{'─'*55}")

        for i, url in enumerate(urls, 1):
            plat = detectar_plataforma(url)
            print(f"\n  [{i}/{len(urls)}] {plat} — {url[:60]}...")

            dados = None

            if plat == 'Amazon' and ctx_amazon:
                dados = scrape_amazon(page_amazon, url)
            elif plat == 'Mercado Livre' and ctx_ml:
                dados = scrape_ml(page_ml, url)
            else:
                print(f"       ✗ Plataforma não suportada")
                erros.append(url)
                continue

            if not dados:
                print(f"       ✗ Não foi possível extrair dados")
                erros.append(url)
                continue

            if ja_visto(dados['nome'], history):
                print(f"       ⏭ Já visto recentemente — atualizando mesmo assim")
                # para links manuais, força atualização mesmo se recente

            registrar(dados['nome'], history, plat)
            produtos_novos.append(dados)

            print(f"       ✓ {dados['nome'][:55]}")
            print(f"         {dados['preco']} · {dados['desconto']}% off · ⭐{dados['avaliacao']}")

            time.sleep(random.uniform(1.5, 3))

        if ctx_amazon:
            ctx_amazon.close()
        if ctx_ml:
            ctx_ml.close()
        browser.close()

    # salva histórico e merge
    save_history(history)
    atualizados, adicionados, total = salvar_merge(produtos_novos)

    print(f"\n{'='*55}")
    print(f"  ✅ {adicionados} produtos novos adicionados")
    print(f"  🔄 {atualizados} produtos existentes atualizados")
    print(f"  ❌ {len(erros)} links com erro")
    print(f"  📄 Total no arquivo: {total} produtos")
    print(f"  💾 Arquivo salvo: {ARQUIVO_SAIDA}")
    print(f"{'='*55}")

    if erros:
        print(f"\n  Links com erro:")
        for e in erros:
            print(f"    - {e}")

    print("\n📤 Próximo passo: faça upload do 'produtos.json' no GitHub.")
    print("   O site vai atualizar automaticamente em ~1 minuto.\n")

    # opcional: pergunta se quer limpar os links processados
    limpar = input("🗑️  Limpar links.txt após processar? (s = sim / Enter = não): ").strip().lower()
    if limpar == 's':
        with open(ARQUIVO_LINKS, 'w', encoding='utf-8') as f:
            f.write("# links.txt — mminis\n# Cole seus links aqui, um por linha.\n\n")
        print(f"  ✅ '{ARQUIVO_LINKS}' limpo.")


if __name__ == '__main__':
    main()
