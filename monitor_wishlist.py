import os
import sys
import json
import time
import re
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright

# ==============================================================================
# ⚙️ CONFIGURAÇÕES
# ==============================================================================

TELEGRAM_TOKEN        = "8748572165:AAF2mKNmurwRf4cV4vC4uJnUiG1nyR3zyjY"
TELEGRAM_USER_ID      = "792758999"
WISHLIST_URL          = "https://www.amazon.com.br/hz/wishlist/ls/3VCIMEBP19W5X"
ARQUIVO_HISTORICO     = 'wishlist_history.json'
ARQUIVO_SESSAO_AM     = 'session.json'
INTERVALO_MINUTOS     = 45

# ==============================================================================

def send_personal_msg(texto: str) -> bool:
    """Envia mensagem ao Telegram pessoal."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_USER_ID,
        "text": texto,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    try:
        res = requests.post(url, json=payload, timeout=15)
        data = res.json()
        if data.get("ok"):
            print("  ✅ Mensagem enviada ao Telegram!")
            return True
        else:
            print(f"  ❌ Telegram recusou: {data.get('description', data)}")
            return False
    except Exception as e:
        print(f"  ❌ Erro ao enviar Telegram: {e}")
        return False


def parse_price(texto: str) -> float | None:
    """Converte string de preço BR para float."""
    if not texto:
        return None
    try:
        limpo = "".join(c for c in texto if c.isdigit() or c in ",.")
        if ',' in limpo and '.' in limpo:
            limpo = limpo.replace('.', '').replace(',', '.')
        elif ',' in limpo:
            limpo = limpo.replace(',', '.')
        val = float(limpo)
        return val if val > 0 else None
    except Exception:
        return None


def format_price(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')


def load_history() -> dict:
    if os.path.exists(ARQUIVO_HISTORICO):
        try:
            with open(ARQUIVO_HISTORICO, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_history(history: dict):
    with open(ARQUIVO_HISTORICO, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def coletar_asins(page) -> list[str]:
    """Acessa a wishlist e retorna lista de ASINs."""
    print("  🌐 Acessando wishlist...")
    page.goto(WISHLIST_URL, wait_until='domcontentloaded', timeout=60000)

    try:
        page.wait_for_selector('li[data-asin], li[id^="item_"], li.g-item-sortable', timeout=15000)
    except Exception:
        print("  ⚠️ Timeout aguardando itens — continuando mesmo assim...")

    # Scroll para forçar carregamento de todos os itens
    for _ in range(5):
        page.mouse.wheel(0, 2000)
        time.sleep(0.8)
    time.sleep(1)

    asins: list[str] = []
    html = page.content()

    # Método 1: data-asin direto no <li>
    for item in page.locator('li[data-asin]').all():
        asin = (item.get_attribute('data-asin') or '').strip()
        if asin and asin not in asins:
            asins.append(asin)

    # Método 2: data-reposition-action-params contém "ASIN:B0XXXX|..."
    if not asins:
        for item in page.locator('[data-reposition-action-params]').all():
            param = item.get_attribute('data-reposition-action-params') or ''
            m = re.search(r'ASIN:([A-Z0-9]{10})', param)
            if m and m.group(1) not in asins:
                asins.append(m.group(1))

    # Método 3: id="item_ITEMID" + extrair ASIN do HTML interno
    if not asins:
        for item in page.locator('li[id^="item_"]').all():
            outer = item.inner_html()[:600]
            m = re.search(r'ASIN:([A-Z0-9]{10})', outer) or re.search(r'/dp/([A-Z0-9]{10})/', outer)
            if m and m.group(1) not in asins:
                asins.append(m.group(1))

    # Método 4: regex no HTML completo (último recurso)
    if not asins:
        for pattern in [
            r'data-asin="([A-Z0-9]{10})"',
            r'ASIN:([A-Z0-9]{10})\|',
            r'"asin"\s*:\s*"([A-Z0-9]{10})"',
            r'/dp/([A-Z0-9]{10})/',
        ]:
            matches = re.findall(pattern, html)
            for a in matches:
                if a not in asins:
                    asins.append(a)
            if asins:
                break

    print(f"  📦 {len(asins)} ASINs: {asins}")
    return asins


def scrape_produto(page, asin: str) -> dict | None:
    """Abre a página do produto e retorna título e preço."""
    url = f"https://www.amazon.com.br/dp/{asin}/"
    try:
        page.goto(url, wait_until='domcontentloaded', timeout=45000)
        page.wait_for_selector('#productTitle', timeout=12000)
        time.sleep(1.5)
    except Exception as e:
        print(f"     ✗ Falha ao carregar {asin}: {e}")
        return None

    # Título
    titulo = ""
    try:
        titulo = page.locator('#productTitle').inner_text().strip()
    except Exception:
        pass

    if not titulo:
        print(f"     ✗ Título não encontrado para {asin}")
        return None

    # Preço
    preco_str = ""
    for sel in [
        '.a-price.priceToPay .a-offscreen',
        '.apexPriceToPay .a-offscreen',
        '#priceblock_ourprice',
        '#priceblock_dealprice',
        '.a-price .a-offscreen',
    ]:
        try:
            txt = page.locator(sel).first.inner_text().strip()
            if txt and parse_price(txt):
                preco_str = txt
                break
        except Exception:
            continue

    preco = parse_price(preco_str)
    print(f"     ✓ {titulo[:60]}")
    print(f"       Preço: {preco_str or '(não encontrado)'}")

    return {'titulo': titulo, 'preco': preco, 'url': url}


def monitorar():
    print(f"\n{'=' * 60}")
    print(f"🚀 Wishlist Monitor — {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"{'=' * 60}")

    history = load_history()

    with sync_playwright() as p:
        browser = p.firefox.launch(headless=False)
        ctx_args: dict = {
            'user_agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) '
                'Gecko/20100101 Firefox/122.0'
            ),
            'viewport': {'width': 1440, 'height': 900},
        }
        if os.path.exists(ARQUIVO_SESSAO_AM):
            ctx_args['storage_state'] = ARQUIVO_SESSAO_AM
            print("  🔐 Sessão Amazon carregada")

        context = browser.new_context(**ctx_args)
        page = context.new_page()

        try:
            asins = coletar_asins(page)

            if not asins:
                print("  ⚠️ Nenhum ASIN encontrado. Verifique a sessão ou URL.")
                return

            print(f"\n  🔎 Verificando {len(asins)} produtos individualmente...")

            for i, asin in enumerate(asins, 1):
                print(f"\n  [{i}/{len(asins)}] {asin}")
                dados = scrape_produto(page, asin)

                if not dados or not dados['preco']:
                    print("     ⚠️ Sem preço — ignorando.")
                    continue

                item_id   = f"https://www.amazon.com.br/dp/{asin}/"
                titulo    = dados['titulo']
                preco_now = dados['preco']

                if item_id in history:
                    old_price = history[item_id]['preco']
                    history[item_id].update({'preco': preco_now, 'titulo': titulo})

                    if preco_now < old_price:
                        reducao = old_price - preco_now
                        pct     = (reducao / old_price) * 100

                        msg = (
                            "📉 <b>QUEDA DE PREÇO NA WISHLIST!</b>\n\n"
                            f"📦 <b>{titulo}</b>\n\n"
                            f"❌ De: <s>{format_price(old_price)}</s>\n"
                            f"✅ Por: <b>{format_price(preco_now)}</b>\n"
                            f"🔥 Economia de {format_price(reducao)} ({pct:.1f}% OFF)\n\n"
                            f"🔗 <a href='{item_id}'>Ver na Amazon</a>"
                        )

                        print(f"     🔥 BAIXOU! {format_price(old_price)} → {format_price(preco_now)}")
                        send_personal_msg(msg)
                else:
                    history[item_id] = {
                        'titulo'         : titulo,
                        'preco'          : preco_now,
                        'data_registro'  : datetime.now().isoformat(),
                    }
                    print(f"     ✅ Novo item registrado em {format_price(preco_now)}")

                time.sleep(1.5)

            save_history(history)
            print(f"\n  ✅ Feito! Próxima verificação em {INTERVALO_MINUTOS} min.")

        except Exception as e:
            print(f"  ❌ Erro crítico: {e}")
        finally:
            browser.close()


def testar_telegram():
    """Envia mensagem de teste para o Telegram pessoal."""
    print("\n📨 Enviando mensagem de teste ao Telegram...")
    ok = send_personal_msg(
        "✅ <b>Monitor de Wishlist — Teste</b>\n\n"
        "Esta é uma mensagem de teste. O bot está configurado corretamente "
        "e vai te avisar quando um item da sua lista de compras baixar de preço! 🛒\n\n"
        f"<i>Enviado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</i>"
    )
    if not ok:
        print("❌ Falha. Verifique TELEGRAM_TOKEN e TELEGRAM_USER_ID.")


# ==============================================================================
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == 'teste':
        testar_telegram()
    else:
        while True:
            try:
                monitorar()
            except KeyboardInterrupt:
                print("\nEncerrando monitoramento...")
                break
            except Exception as e:
                print(f"Erro: {e}")
            time.sleep(INTERVALO_MINUTOS * 60)
