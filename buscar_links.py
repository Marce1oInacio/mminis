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
import csv
import requests
from playwright.sync_api import sync_playwright, Page
import tkinter as tk
from tkinter import simpledialog

# =============================================
# CONFIGURAÇÕES
# =============================================
ARQUIVO_LINKS     = r'\links.txt'
ARQUIVO_SAIDA     = 'produtos.json'
ARQUIVO_HISTORICO = 'deal_history.json'
ARQUIVO_SESSAO_AM = 'session.json'
ARQUIVO_SESSAO_ML = 'session_ml.json'

# --- ABAIXO: Link do Google Sheets (Opcional) ---
# 1. Crie uma planilha no Google Sheets e cole os links na primeira coluna.
# 2. Vá em Arquivo > Compartilhar > Publicar na web.
# 3. Escolha "Valores separados por vírgula (.csv)" e clique em Publicar.
# 4. Cole o link gerado abaixo:
GOOGLE_SHEET_URL  = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vSbBLKgjFglQH0JFpOx7XxKnWD1fDDVnia-ufRbOgdqm34ITVD5twQAd1Aw9drYTecWwV2XMzXTMdmn/pub?gid=0&single=true&output=csv' 

# — Config Telegram —
TELEGRAM_TOKEN    = "8748572165:AAF2mKNmurwRf4cV4vC4uJnUiG1nyR3zyjY"
TELEGRAM_USER_ID  = "792758999"


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
# LER links (Local + Google Sheets)
# =============================================

def ler_links() -> list[str]:
    """Lê links de fontes locais e remotas (Google Sheets)."""
    urls = []

    # 1. Tenta ler do Google Sheets se configurado
    if GOOGLE_SHEET_URL:
        print(f"🌐 Verificando Google Sheets...")
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
            else:
                print(f"  ⚠️  Erro ao acessar Google Sheets (Status: {res.status_code})")
        except Exception as e:
            print(f"  ⚠️  Falha ao conectar ao Google Sheets: {e}")

    # 2. Tenta ler do arquivo local links.txt
    if os.path.exists(ARQUIVO_LINKS):
        with open(ARQUIVO_LINKS, 'r', encoding='utf-8') as f:
            for linha in f:
                linha = linha.strip()
                if not linha or linha.startswith('#'):
                    continue
                # Se for uma linha de CSV colada por engano, tenta pegar a primeira parte
                url = linha.split(',')[0].strip() if ',' in linha and not linha.startswith('http') else linha
                if url.startswith('http'):
                    urls.append(url)
    else:
        # Cria arquivo local como backup se não existir
        os.makedirs(os.path.dirname(ARQUIVO_LINKS), exist_ok=True)
        with open(ARQUIVO_LINKS, 'w', encoding='utf-8') as f:
            f.write("# links.txt — mminis\n# Cole links aqui ou use o Google Sheets no buscar_links.py\n\n")

    # Filtra links válidos (Amazon ou ML) e remove duplicados
    urls_unicas = []
    seen = set()
    for u in urls:
        if u in seen: continue
        if any(d in u for d in ['amazon.com.br', 'amzn.to', 'mercadolivre.com.br', 'mercadolivre.com']):
            urls_unicas.append(u)
            seen.add(u)
        else:
            u_str = str(u)
            print(f"  ⚠️  Link ignorado (plataforma não reconhecida): {u_str[:60]}")

    return urls_unicas

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

def get_affiliate_link(page: Page, url_original: str, plataforma: str) -> str:
    try:
        if plataforma == 'Amazon':
            # Codegen: button "Obter link"
            try:
                btn = page.get_by_role("button", name="Obter link").first
                btn.wait_for(state='visible', timeout=5000)
                btn.click()
                time.sleep(2)
                campo = page.get_by_role("textbox", name="Generated short link").first
                campo.wait_for(state='visible', timeout=4000)
                val = campo.get_attribute('value') or campo.input_value()
                if val and ('amzn.to' in val or 'amazon.com.br' in val):
                    return val
            except Exception:
                pass
        elif plataforma == 'Mercado Livre':
            # Mercado Livre Codegen: test-id "generate_link_button"
            try:
                btn = page.get_by_test_id("generate_link_button").first
                btn.wait_for(state='visible', timeout=5000)
                btn.click()
                time.sleep(2)
                # Tenta pegar do label/input indicado pelo codegen
                val = page.get_by_test_id("text-field__label_link").inner_text() or \
                      page.get_by_test_id("text-field__label_link").get_attribute('value')
                if val and 'mercadolivre' in val:
                    return val
            except Exception:
                pass

        return url_original
    except Exception:
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

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    confirmar = simpledialog.askstring("Confirmar Processamento", f"Processar todos os {len(urls)} links?\nDigite 's' para sim ou clique Cancelar para não:", initialvalue="s")
    root.destroy()
    
    if not confirmar or confirmar.lower() != 's':
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
                root = tk.Tk()
                root.withdraw()
                root.attributes("-topmost", True)
                simpledialog.askstring("Login Mercado Livre", "Faça login no ML no navegador que abriu.\nDepois de logado, clique OK aqui.", initialvalue="OK")
                root.destroy()
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

    print(f"  💾 Arquivo salvo: {ARQUIVO_SAIDA}")
    print("=" * 55)

    # Enviar para Telegram
    if produtos_novos:
        print(f"📤 Enviando {len(produtos_novos)} itens para seu Telegram...")
        for p in produtos_novos:
            msg = (
                f"🔵 <b>ACHADO {p['plataforma'].upper()}!</b>\n\n"
                f"📦 <b>{p['nome'][:120]}</b>\n"
                f"✅ Por: <b>{p['preco']}</b>\n"
                f"📉 Desconto: {p.get('desconto', 0)}% OFF\n\n"
                f"🔗 <a href='{p['link']}'>COMPRAR AGORA</a>"
            )
            send_telegram_msg(msg, p.get('foto_url'))
            time.sleep(1)

    print("\n📤 Próximo passo: faça upload do 'produtos.json' no GitHub.")
    print("   O site vai atualizar automaticamente em ~1 minuto.\n")

    # opcional: pergunta se quer limpar os links processados
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    limpar = simpledialog.askstring("Limpar Links", "Deseja limpar o arquivo links.txt?\nDigite 's' para sim ou clique Cancelar para não:", initialvalue="n")
    root.destroy()
    
    if limpar and limpar.lower() == 's':
        with open(ARQUIVO_LINKS, 'w', encoding='utf-8') as f:
            f.write("# links.txt — mminis\n# Cole seus links aqui, um por linha.\n\n")
        print(f"  ✅ '{ARQUIVO_LINKS}' limpo.")


if __name__ == '__main__':
    main()