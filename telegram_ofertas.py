"""
telegram_ofertas.py — Fiveten Garage
Busca promoções com desconto alto na Amazon e ML
e posta automaticamente no canal do Telegram.

Também salva no produtos.json (alimenta o site).

USO:
  python telegram_ofertas.py

CONFIGURAÇÃO (edite a seção abaixo):
  TELEGRAM_TOKEN   → token do @BotFather
  TELEGRAM_CANAL   → ID do canal (ex: -1001234567890)

DEPENDÊNCIAS:
  pip install playwright beautifulsoup4 requests
  playwright install firefox
"""

import os
import json
import re
import time
import random
import hashlib
import requests
import csv
from datetime import datetime
from urllib.parse import quote_plus
from playwright.sync_api import sync_playwright, Page
from bs4 import BeautifulSoup

# =============================================
# ⚙️  CONFIGURAÇÕES — EDITE AQUI
# =============================================
TELEGRAM_TOKEN  = "8748572165:AAF2mKNmurwRf4cV4vC4uJnUiG1nyR3zyjY"          # token do @BotFather
TELEGRAM_CANAL  = "-1002962498795"       # ex: -1001234567890

# Critérios de seleção de ofertas
DESCONTO_MINIMO = 0          # % mínimo de desconto para considerar
PRECO_MAXIMO    = 500.0       # ignora produtos acima deste valor
MAX_POR_BUSCA   = 5           # máximo de produtos por termo buscado
INTERVALO_POSTS = 30          # segundos entre posts no Telegram

# Termos de busca — adicione os que quiser
TERMOS_AMAZON = [
    "Hot Wheels Premium",
    "Hot Wheels Car Culture",
    "Hot Wheels Treasure Hunt",
    "Hot Wheels Boulevard",
    "Matchbox",
]
TERMOS_ML = [
    "Hot Wheels Premium",
    "Hot Wheels Treasure Hunt",
    "Hot Wheels Car Culture",
]

# Arquivos
ARQUIVO_SAIDA     = 'produtos.json'
ARQUIVO_HISTORICO = 'deal_history.json'
ARQUIVO_SESSAO_AM = 'session.json'
ARQUIVO_SESSAO_ML = 'session_ml.json'
ARQUIVO_LOG_TELEGRAM = 'log_telegram.json'

# --- ABAIXO: Link do Google Sheets ---
# Colado automaticamente ou manualmente para ler links do celular
GOOGLE_SHEET_URL  = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vSbBLKgjFglQH0JFpOx7XxKnWD1fDDVnia-ufRbOgdqm34ITVD5twQAd1Aw9drYTecWwV2XMzXTMdmn/pub?gid=0&single=true&output=csv'


# =============================================
# TELEGRAM
# =============================================

def telegram_send(texto: str, foto_url: str | None = None) -> bool:
    """Envia mensagem (com foto se disponível) para o canal do Telegram."""
    if TELEGRAM_TOKEN == "SEU_TOKEN_AQUI" or not TELEGRAM_TOKEN:
        print("  ⚠️  Configure TELEGRAM_TOKEN antes de usar.")
        return False

    # Trata string vazia como None
    if not foto_url:
        foto_url = None

    if foto_url:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
        payload = {
            "chat_id":    TELEGRAM_CANAL,
            "photo":      foto_url,
            "caption":    texto,
            "parse_mode": "HTML",
        }
    else:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id":    TELEGRAM_CANAL,
            "text":       texto,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        }

    try:
        res = requests.post(url, json=payload, timeout=15)
        data = res.json()
        if data.get("ok"):
            return True
        else:
            # Se falhou com foto (ex: URL inválida), tenta enviar apenas o texto como fallback
            if foto_url:
                print(f"  ⚠️  Erro ao enviar foto: {data.get('description')}. Tentando apenas texto...")
                return telegram_send(texto, foto_url=None)

            print(f"  ❌ Telegram erro: {data.get('description')}")
            return False
    except Exception as e:
        print(f"  ❌ Telegram falhou: {e}")
        return False

def formatar_mensagem(p: dict) -> str:
    """Formata a mensagem de oferta para o Telegram."""
    frases = [
        "🔥 <b>OFERTA IMPERDÍVEL!</b>",
        "⚡ <b>PREÇO BAIXOU!</b>",
        "🚨 <b>ACHADO DO DIA!</b>",
        "💥 <b>OFERTA RELÂMPAGO!</b>",
        "⚡⚡ <b>ACHADO DE HOJE!</b>",
    ]
    gancho = random.choice(frases)
    plat   = p.get('plataforma', '')
    emoji_plat = {'Amazon': '📦', 'Mercado Livre': '🏷️', 'Shopee': '🛍️'}.get(plat, '🛒')

    linhas = [gancho, ""]
    linhas.append(f"🟡 <b>{p['nome'][:80]}</b>")
    linhas.append("")

    if p.get('preco_antigo'):
        linhas.append(f"💸 De: <s>{p['preco_antigo']}</s>")
    linhas.append(f"✅ Por: <b>{p['preco']}</b>")

    if p.get('desconto', 0) > 0:
        linhas.append(f"📉 Desconto: <b>{p['desconto']}% OFF</b>")

    if p.get('avaliacao'):
        aval = p['avaliacao']
        num  = f" ({p['num_aval']} avaliações)" if p.get('num_aval') else ""
        linhas.append(f"⭐ Avaliação: {aval}{num}")

    linhas.append("")
    linhas.append(f"{emoji_plat} Plataforma: {plat}")
    linhas.append(f"🔗 <a href=\"{p['link']}\">👉 COMPRAR AGORA</a>")
    # linhas.append("")
    # linhas.append("━━━━━━━━━━━━━━━━━━━━━")
    # linhas.append(f"📲 Grupo VIP Telegram: https://t.me/fivetenvip")
    # linhas.append("🟡 <b>Fiveten Garage</b> — Curadoria de colecionáveis")

    return "\n".join(linhas)


# =============================================
# HISTÓRICO
# =============================================

def gerar_id(titulo: str) -> str:
    return hashlib.md5(' '.join(titulo.lower().split()).encode()).hexdigest()

def load_history() -> dict:
    if os.path.exists(ARQUIVO_HISTORICO):
        try:
            with open(ARQUIVO_HISTORICO, 'r', encoding='utf-8') as f:
                d = json.load(f)
            return d if isinstance(d, dict) and 'ofertas' in d else {'ofertas': d if isinstance(d, list) else []}
        except Exception:
            pass
    return {'ofertas': []}

def save_history(h: dict):
    with open(ARQUIVO_HISTORICO, 'w', encoding='utf-8') as f:
        json.dump(h, f, indent=2, ensure_ascii=False)

def ja_postado(titulo: str, history: dict, days: int = 3) -> bool:
    """Para o Telegram, não repete em 3 dias (mais agressivo que o site)."""
    pid   = gerar_id(titulo)
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
# UTILITÁRIOS
# =============================================

def parse_price(texto) -> float | None:
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

def format_price(v: float | None) -> str:
    if v is None:
        return ''
    return f"R$ {v:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

def salvar_no_site(novos: list):
    """Agrega os produtos ao produtos.json do site."""
    existentes = []
    if os.path.exists(ARQUIVO_SAIDA):
        try:
            with open(ARQUIVO_SAIDA, 'r', encoding='utf-8') as f:
                existentes = json.load(f)
        except Exception:
            pass

    novos_ids = {gerar_id(p['nome']) for p in novos}
    outros    = [p for p in existentes if gerar_id(p.get('nome','')) not in novos_ids]
    final     = outros + novos

    with open(ARQUIVO_SAIDA, 'w', encoding='utf-8') as f:
        json.dump(final, f, indent=2, ensure_ascii=False)
    print(f"  💾 {len(novos)} produtos salvos no produtos.json ({len(final)} total)")


# =============================================
# SCRAPER AMAZON
# =============================================

def buscar_amazon(page: Page, termo: str, history: dict,
                  desconto_min: int = DESCONTO_MINIMO,
                  preco_max: float = PRECO_MAXIMO,
                  qtd_max: int = MAX_POR_BUSCA) -> list:
    produtos = []
    print(f"\n  🔍 Amazon: '{termo}'")

    try:
        page.goto(f"https://www.amazon.com.br/s?k={quote_plus(termo)}&s=price-asc-rank",
                  wait_until='domcontentloaded', timeout=60000)
        time.sleep(random.uniform(2, 4))

        for _ in range(3):
            page.mouse.wheel(0, 800)
            time.sleep(0.4)
        time.sleep(1.5)

        soup  = BeautifulSoup(page.content(), 'html.parser')
        cards = soup.select('div[data-component-type="s-search-result"]')
        print(f"     {len(cards)} resultados")

        urls_vistas = []
        for card in cards:
            if len(urls_vistas) >= qtd_max * 2:
                break
            link = card.select_one('a.a-link-normal.s-no-outline, h2 a.a-link-normal')
            if not link:
                continue
            href = link.get('href', '')
            if '/dp/' not in href:
                continue
            url = 'https://www.amazon.com.br' + href.split('?')[0].split('/ref=')[0]
            if url not in urls_vistas:
                urls_vistas.append(url)

        for url in urls_vistas:
            if len(produtos) >= qtd_max:
                break
            dados = _scrape_produto_amazon(page, url)
            if not dados:
                continue
            if dados['preco_num'] > preco_max:
                continue
            if dados['desconto'] < desconto_min:
                print(f"       ⏭ {dados['desconto']}% < mínimo {desconto_min}%")
                continue
            if ja_postado(dados['nome'], history):
                print(f"       ⏭ Já postado recentemente")
                continue
            produtos.append(dados)
            print(f"       ✓ {dados['nome'][:50]} | {dados['preco']} | -{dados['desconto']}%")
            time.sleep(random.uniform(1.5, 3))

    except Exception as e:
        print(f"     ⚠️  Erro: {e}")

    return produtos

def _scrape_produto_amazon(page: Page, url: str) -> dict | None:
    try:
        page.goto(url, wait_until='domcontentloaded', timeout=60000)
        page.wait_for_selector('#productTitle', timeout=12000)
        time.sleep(random.uniform(1, 2))
    except Exception:
        return None

    def txt(sels):
        for s in sels:
            try:
                el = page.locator(s).first
                el.wait_for(state='visible', timeout=3000)
                t = el.inner_text().strip()
                if t:
                    return t
            except Exception:
                pass
        return None

    titulo = txt(['#productTitle'])
    if not titulo:
        return None

    preco_atual = parse_price(txt([
        '.a-price.priceToPay .a-offscreen', '.apexPriceToPay .a-offscreen',
        '#priceblock_ourprice', '.a-price .a-offscreen',
    ]))
    if not preco_atual:
        return None

    preco_antigo = parse_price(txt([
        '.a-price[data-a-strike="true"] .a-offscreen',
        '.basisPrice .a-offscreen', 'span.a-text-price .a-offscreen',
    ]))

    desconto = 0
    pct_str  = txt(['span.savingsPercentage', '.reinventPriceSavingsPercentageMargin'])
    if pct_str:
        m = re.search(r'(\d+)', pct_str)
        desconto = int(m.group(1)) if m else 0
    elif preco_antigo and preco_antigo > preco_atual:
        desconto = int(round((preco_antigo - preco_atual) / preco_antigo * 100))

    # só prossegue se tiver desconto relevante (evita páginas sem info)
    if desconto < DESCONTO_MINIMO:
        return None

    foto_url  = None
    try:
        foto_url = page.locator('#imgBlkFront,#landingImage').first.get_attribute('src')
    except Exception:
        pass

    aval = ''
    try:
        t = txt(['#acrPopover span.a-icon-alt'])
        if t:
            m = re.search(r'([\d,\.]+)', t)
            aval = m.group(1).replace(',', '.') if m else ''
    except Exception:
        pass

    num_aval = ''
    try:
        t = txt(['#acrCustomerReviewText'])
        if t:
            m = re.search(r'[\d\.]+', t.replace('.', ''))
            num_aval = m.group(0) if m else ''
    except Exception:
        pass

    # link afiliado
    link = _get_affiliate_amazon(page, url)

    descricao = f"{desconto}% de desconto"
    if preco_antigo:
        descricao += f" · era {format_price(preco_antigo)}"

    return {
        'nome': titulo.strip(), 'descricao': descricao,
        'preco': format_price(preco_atual), 'preco_num': preco_atual,
        'preco_antigo': format_price(preco_antigo) if preco_antigo else '',
        'desconto': desconto, 'plataforma': 'Amazon',
        'link': link, 'foto_url': foto_url or '',
        'avaliacao': aval, 'num_aval': num_aval,
        'url_original': url, 'atualizado': datetime.now().strftime('%d/%m/%Y %H:%M'),
    }

def _get_affiliate_amazon(page: Page, url: str) -> str:
    try:
        for sel in ['#amzn-ss-get-link-button', 'button[title="Obter link"]']:
            try:
                page.locator(sel).first.click(timeout=4000)
                time.sleep(2)
                break
            except Exception:
                pass
        for sel in ['#amzn-ss-text-shortlink-textarea', '#SL_text_short_link']:
            try:
                val = page.locator(sel).first.input_value(timeout=3000)
                if val and 'amzn.to' in val:
                    return val
            except Exception:
                pass
    except Exception:
        pass
    return url


# =============================================
# SCRAPER MERCADO LIVRE
# =============================================

def buscar_ml(page: Page, termo: str, history: dict,
              desconto_min: int = DESCONTO_MINIMO,
              preco_max: float = PRECO_MAXIMO,
              qtd_max: int = MAX_POR_BUSCA) -> list:
    produtos = []
    print(f"\n  🔍 Mercado Livre: '{termo}'")

    try:
        page.goto('https://www.mercadolivre.com.br/', wait_until='domcontentloaded', timeout=60000)
        time.sleep(random.uniform(2, 3))

        search = page.get_by_role("combobox", name="Digite o que você quer")
        search.click()
        time.sleep(0.4)
        search.fill(termo)
        search.press("Enter")
        time.sleep(random.uniform(3, 5))

        for _ in range(4):
            page.mouse.wheel(0, 800)
            time.sleep(0.4)
        time.sleep(2)

        soup  = BeautifulSoup(page.content(), 'html.parser')
        cards = soup.select('li.ui-search-layout__item') or soup.select('div.poly-card')
        print(f"     {len(cards)} resultados")

        urls_vistas = []
        for card in cards:
            if len(urls_vistas) >= qtd_max * 2:
                break
            link = (card.select_one('a.poly-component__title') or
                    card.select_one('a.ui-search-item__group__element') or
                    card.select_one('a[href*="mercadolivre.com.br"]'))
            if not link:
                continue
            href = link.get('href', '').split('?')[0].split('#')[0]
            if 'mercadolivre.com.br' in href and href not in urls_vistas:
                urls_vistas.append(href)

        for url in urls_vistas:
            if len(produtos) >= qtd_max:
                break
            dados = _scrape_produto_ml(page, url)
            if not dados:
                continue
            if dados['preco_num'] > preco_max:
                continue
            if dados['desconto'] < desconto_min:
                print(f"       ⏭ {dados['desconto']}% < mínimo {desconto_min}%")
                continue
            if ja_postado(dados['nome'], history):
                print(f"       ⏭ Já postado recentemente")
                continue
            produtos.append(dados)
            print(f"       ✓ {dados['nome'][:50]} | {dados['preco']} | -{dados['desconto']}%")
            time.sleep(random.uniform(1.5, 3))

    except Exception as e:
        print(f"     ⚠️  Erro: {e}")

    return produtos

def _scrape_produto_ml(page: Page, url: str) -> dict | None:
    try:
        page.goto(url, wait_until='domcontentloaded', timeout=60000)
        page.wait_for_selector('#price', timeout=12000)
        time.sleep(random.uniform(1, 2))
    except Exception:
        return None

    titulo = None
    try:
        titulo = page.locator('h1.ui-pdp-title').first.inner_text().strip()
    except Exception:
        pass
    if not titulo:
        try:
            titulo = page.get_by_role("heading").first.inner_text().strip()
        except Exception:
            return None

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

    preco_antigo = None
    try:
        t = page.locator('#pricing_price_subtitle,.ui-pdp-price__original-value').first.inner_text()
        preco_antigo = parse_price(t)
    except Exception:
        pass

    desconto = 0
    try:
        t = page.locator('.ui-pdp-price__second-line .ui-pdp-price__discount').first.inner_text()
        m = re.search(r'(\d+)', t)
        desconto = int(m.group(1)) if m else 0
    except Exception:
        pass
    if desconto == 0 and preco_antigo and preco_antigo > preco_atual:
        desconto = int(round((preco_antigo - preco_atual) / preco_antigo * 100))

    if desconto < DESCONTO_MINIMO:
        return None

    foto_url = None
    try:
        foto_url = page.locator('[data-testid^="image-"]').first.get_attribute('src')
    except Exception:
        pass

    aval = ''
    try:
        t = page.locator('.ui-pdp-reviews__rating__average').first.inner_text().strip()
        m = re.search(r'([\d,\.]+)', t)
        aval = m.group(1).replace(',', '.') if m else ''
    except Exception:
        pass

    num_aval = ''
    try:
        t = page.locator('.ui-pdp-reviews__rating__amount').first.inner_text().strip()
        m = re.search(r'[\d\.,]+', t.replace('.', ''))
        num_aval = m.group(0) if m else ''
    except Exception:
        pass

    descricao = f"{desconto}% de desconto"
    if preco_antigo:
        descricao += f" · era {format_price(preco_antigo)}"

    return {
        'nome': titulo, 'descricao': descricao,
        'preco': format_price(preco_atual), 'preco_num': preco_atual,
        'preco_antigo': format_price(preco_antigo) if preco_antigo else '',
        'desconto': desconto, 'plataforma': 'Mercado Livre',
        'link': url, 'foto_url': foto_url or '',
        'avaliacao': aval, 'num_aval': num_aval,
        'url_original': url, 'atualizado': datetime.now().strftime('%d/%m/%Y %H:%M'),
    }

def _scrape_produto_generico(page: Page, url: str) -> dict | None:
    """Fallback para qualquer site: tenta pegar o título da página e imagem og:image."""
    try:
        # Tenta carregar o link
        page.goto(url, wait_until='domcontentloaded', timeout=30000)
        time.sleep(2)
        
        titulo = page.title()
        if not titulo or len(titulo) < 3:
            titulo = "Oferta Especial"

        # Tenta pegar imagem das meta tags
        foto_url = ""
        try:
            meta_img = page.query_selector("meta[property='og:image']")
            if meta_img:
                foto_url = meta_img.get_attribute("content")
        except:
            pass

        return {
            'nome': titulo.strip()[:100],
            'descricao': f"Confira esta oferta no link abaixo!",
            'preco': 'Ver no site',
            'preco_num': 0.0,
            'preco_antigo': '',
            'desconto': 0,
            'plataforma': 'Outros',
            'link': url,
            'foto_url': foto_url or '',
            'avaliacao': '?',
            'num_aval': 0,
            'url_original': url,
            'atualizado': datetime.now().strftime('%d/%m/%Y %H:%M'),
        }
    except Exception as e:
        print(f"       ✗ Erro no scraper genérico: {e}")
        return {
            'nome': "Oferta Especial",
            'descricao': "Acesse o link para conferir os detalhes desta oferta!",
            'preco': 'Ver no site',
            'preco_num': 0.0,
            'preco_antigo': '',
            'desconto': 0,
            'plataforma': 'Outros',
            'link': url,
            'foto_url': '',
            'avaliacao': '?',
            'num_aval': 0,
            'url_original': url,
            'atualizado': datetime.now().strftime('%d/%m/%Y %H:%M'),
        }

def processar_links_google(page_am, page_ml, history) -> list:
    """Busca links no Google Sheets e extrai os dados dos produtos."""
    if not GOOGLE_SHEET_URL:
        return []
        
    print(f"\n🌐 Verificando links no Google Sheets...")
    urls = []
    try:
        res = requests.get(GOOGLE_SHEET_URL, timeout=15)
        if res.ok:
            linhas = res.text.splitlines()
            reader = csv.reader(linhas)
            for row in reader:
                if row:
                    url = row[0].strip()
                    if url.startswith('http'):
                        urls.append(url)
    except Exception as e:
        print(f"  ⚠️  Erro ao ler Google Sheets: {e}")
        return []

    produtos = []
    for i, url in enumerate(urls, 1):
        print(f"  🔗 Link Extra [{i}/{len(urls)}]: {url[:60]}...")
        
        dados = None
        if 'amazon.com.br' in url or 'amzn.to' in url:
            dados = _scrape_produto_amazon(page_am, url)
        elif 'mercadolivre.com' in url:
            dados = _scrape_produto_ml(page_ml, url)
        else:
            # Novo: Tenta scraper genérico para outros sites
            print(f"       ℹ️ Plataforma não mapeada. Tentando extração básica...")
            dados = _scrape_produto_generico(page_am, url) # Usa o contexto da Amazon que já está aberto
            
        if dados:
            # Para links manuais, ignoramos o filtro de desconto mínimo 
            # e agora também removemos a trava de 'já postado', conforme pedido.
            produtos.append(dados)
            print(f"       ✓ {dados['nome'][:50]} | {dados['preco']}")
            time.sleep(random.uniform(1, 2))
        else:
            print(f"       ✗ Falha ao extrair dados")
            
    return produtos

def log_telegram_post(produto: dict):
    """Salva um log apartado dos itens postados no Telegram."""
    log_data = []
    if os.path.exists(ARQUIVO_LOG_TELEGRAM):
        try:
            with open(ARQUIVO_LOG_TELEGRAM, 'r', encoding='utf-8') as f:
                log_data = json.load(f)
        except:
            log_data = []
    
    item_log = produto.copy()
    item_log['postado_em'] = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    log_data.append(item_log)
    
    if len(log_data) > 1000:
        log_data = log_data[-1000:]
        
    with open(ARQUIVO_LOG_TELEGRAM, 'w', encoding='utf-8') as f:
        json.dump(log_data, f, indent=2, ensure_ascii=False)


# =============================================
# EXECUÇÃO PRINCIPAL
# =============================================

def main():
    print("=" * 55)
    print("  Fiveten Garage — Buscador de Ofertas + Telegram")
    print("=" * 55)

    # valida config do Telegram
    if TELEGRAM_TOKEN == "SEU_TOKEN_AQUI":
        print("\n⚠️  TELEGRAM_TOKEN não configurado.")
        print("   Edite o arquivo e insira seu token do @BotFather.\n")
        return

    # ── MODO ─────────────────────────────────────────
    print("\n🚀 O que deseja fazer hoje?")
    print("  1. 🔍 Buscar novos produtos + 📨 Postar + 🌐 Salvar site")
    print("  2. 🔍 Só buscar e salvar no site (sem postar)")
    print("  3. 📨 Só postar no Telegram (usar produtos.json já existente)")
    print("  4. 🔗 Só acessar links (Google Sheets) e postar no Telegram")
    opcao = input("\nEscolha (1/2/3/4): ").strip()

    if opcao not in ['1', '2', '3', '4']:
        print("Opção inválida.")
        return

    history = load_history()

    # -- Opção 3: Postagem Direta do JSON --
    if opcao == '3':
        if not os.path.exists(ARQUIVO_SAIDA):
            print("produtos.json não encontrado.")
            return
        with open(ARQUIVO_SAIDA, 'r', encoding='utf-8') as f:
            lista = json.load(f)
        nao_postados = [p for p in lista if not ja_postado(p.get('nome', ''), history)]
        print(f"\n{len(nao_postados)} produtos ainda não postados no Telegram.")
        if not nao_postados:
            return
            
        qtd_str = input(f"Quantos postar? (Enter = todos {len(nao_postados)}): ").strip()
        qtd = int(qtd_str) if qtd_str.isdigit() else len(nao_postados)
        selecionados = nao_postados[:qtd]
        
        print(f"\n⚠️  Confirmar postagem de {len(selecionados)} itens? (S/n): ", end="")
        if input().strip().lower() == 'n':
            print("❌ Cancelado.")
            return

        print(f"\n📨 Postando no Telegram ({INTERVALO_POSTS}s entre posts)...")
        for i, p in enumerate(selecionados):
            msg = formatar_mensagem(p)
            ok  = telegram_send(msg, p.get('foto_url'))
            if ok:
                log_telegram_post(p)
                registrar(p['nome'], history, p.get('plataforma', ''))
                print(f"  ✅ {p['nome'][:50]}")
            else:
                print(f"  ❌ Falha: {p['nome'][:50]}")
            
            if i < len(selecionados) - 1 and ok:
                time.sleep(INTERVALO_POSTS)
        save_history(history)
        return

    # -- Configuração para Opções 1, 2 e 4 --
    usar_google = True
    termos_amazon = []
    termos_ml = []
    
    if opcao in ['1', '2']:
        print("\n🔍 Configuração da busca:")
        usar_google_prompt = input("🌐 Processar links do Google Sheets? (S/n): ").strip().lower()
        usar_google = usar_google_prompt != 'n'

        print("\n📦 Digite os termos para AMAZON (um por linha, Enter vazio para encerrar):")
        while True:
            t = input("  + ").strip()
            if not t: break
            termos_amazon.append(t)

        print("\n🏷️  Digite os termos para MERCADO LIVRE (um por linha, Enter vazio para encerrar):")
        while True:
            t = input("  + ").strip()
            if not t: break
            termos_ml.append(t)
    
    # Se for opção 4, usar_google já é True e termos estão vazios, pronto.

    if not termos_amazon and not termos_ml and not usar_google:
        print("\n⚠️  Nenhum termo ou fonte de dados selecionada. Encerrando.")
        return

    # ── PARÂMETROS ────────────────────────────────────
    desconto_min = DESCONTO_MINIMO
    preco_max = PRECO_MAXIMO
    qtd_max = MAX_POR_BUSCA
    
    if opcao in ['1', '2']:
        desc_str = input(f"\n📉 Desconto mínimo % (Enter = {DESCONTO_MINIMO}): ").strip()
        desconto_min = int(desc_str) if desc_str.isdigit() else DESCONTO_MINIMO

        preco_str = input(f"💰 Preço máximo R$ (Enter = {PRECO_MAXIMO:.0f}): ").strip()
        preco_max = float(preco_str.replace(',', '.')) if preco_str else PRECO_MAXIMO

        qtd_str = input(f"📦 Máximo por termo (Enter = {MAX_POR_BUSCA}): ").strip()
        qtd_max = int(qtd_str) if qtd_str.isdigit() else MAX_POR_BUSCA

    postar = (opcao in ['1', '4'])

    postar = (opcao in ['1', '4'])

    print(f"\n🚀 Iniciando busca")
    if opcao in ['1', '2']:
        print(f"   Desconto mínimo: {desconto_min}% · Preço máximo: R$ {preco_max:.0f} · Máx por termo: {qtd_max}\n")
    else:
        print(f"   Modo: Extrair links do Google Sheets\n")

    with sync_playwright() as p:
        browser = p.firefox.launch(headless=False)

        ctx_am_args = dict(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
            viewport={'width': 1440, 'height': 900},
        )
        if os.path.exists(ARQUIVO_SESSAO_AM):
            ctx_am_args['storage_state'] = ARQUIVO_SESSAO_AM
            print("  🔐 Sessão Amazon carregada")
        ctx_am  = browser.new_context(**ctx_am_args)
        page_am = ctx_am.new_page()

        ctx_ml_args = dict(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
            viewport={'width': 1440, 'height': 900},
        )
        if os.path.exists(ARQUIVO_SESSAO_ML):
            ctx_ml_args['storage_state'] = ARQUIVO_SESSAO_ML
            print("  🔐 Sessão ML carregada")
        ctx_ml  = browser.new_context(**ctx_ml_args)
        page_ml = ctx_ml.new_page()

        todos = []

        if termos_amazon:
            print("\n" + "─"*55)
            print("📦 AMAZON")
            print("─"*55)
            for termo in termos_amazon:
                resultados = buscar_amazon(page_am, termo, history,
                                           desconto_min=desconto_min,
                                           preco_max=preco_max,
                                           qtd_max=qtd_max)
                todos.extend(resultados)

        if termos_ml:
            print("\n" + "─"*55)
            print("🏷️  MERCADO LIVRE")
            print("─"*55)
            for termo in termos_ml:
                resultados = buscar_ml(page_ml, termo, history,
                                       desconto_min=desconto_min,
                                       preco_max=preco_max,
                                       qtd_max=qtd_max)
                todos.extend(resultados)

        # ── NOVOS: Links do Google Sheets ────────────────
        if usar_google:
            links_google = processar_links_google(page_am, page_ml, history)
            todos.extend(links_google)

        ctx_am.close()
        ctx_ml.close()
        browser.close()

    if not todos:
        if opcao == '4' or usar_google:
            print(f"\nℹ️  Nenhuma oferta nova encontrada para processar.")
            print(f"    (Pode ser que todos os links já tenham sido postados recentemente ou houve erro na extração)")
        else:
            print(f"\n⚠️  Nenhuma oferta encontrada com desconto ≥ {desconto_min}%.")
            print(f"   Tente reduzir o desconto mínimo ou usar outros termos.")
        return

    todos.sort(key=lambda x: x.get('desconto', 0), reverse=True)

    print(f"\n{'='*55}")
    print(f"  🎯 {len(todos)} ofertas encontradas (maior desconto primeiro)")
    print(f"{'='*55}")
    for prod in todos:
        print(f"  {prod['desconto']:3d}% | {prod['plataforma']:<15} | {prod['preco']:<12} | {prod['nome'][:38]}")

    if postar and todos:
        print(f"\n⚠️  Tem certeza que deseja postar esses {len(todos)} itens no Telegram? (S/n): ", end="")
        confirma = input().strip().lower()
        if confirma == 'n':
            print("❌ Postagem cancelada pelo usuário.")
        else:
            print(f"\n📨 Postando no Telegram ({INTERVALO_POSTS}s entre posts)...")
            postados = 0
            for i, prod in enumerate(todos):
                msg = formatar_mensagem(prod)
                ok  = telegram_send(msg, prod.get('foto_url'))
                if ok:
                    log_telegram_post(prod)
                    registrar(prod['nome'], history, prod.get('plataforma', ''))
                    print(f"  ✅ {prod['nome'][:50]}")
                    postados += 1
                else:
                    print(f"  ❌ Falha: {prod['nome'][:50]}")
                
                if i < len(todos) - 1 and ok:
                    time.sleep(INTERVALO_POSTS)
            print(f"\n  📊 {postados} mensagens enviadas ao canal")

    save_history(history)
    salvar_no_site(todos)

    print("\n" + "="*55)
    print("  ✅ Concluído!")
    if postar:
        print("  📲 Verifique o canal do Telegram")
    print("  🌐 Faça upload do produtos.json no GitHub")
    print("="*55 + "\n")


if __name__ == '__main__':
    main()