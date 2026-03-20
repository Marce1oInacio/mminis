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

TELEGRAM_TOKEN    = "8748572165:AAF2mKNmurwRf4cV4vC4uJnUiG1nyR3zyjY"
TELEGRAM_USER_ID  = "792758999"
WISHLIST_URL      = "https://www.amazon.com.br/hz/wishlist/ls/3VCIMEBP19W5X"
ARQUIVO_HISTORICO = 'wishlist_history.json'
ARQUIVO_SESSAO_AM = 'session.json'
INTERVALO_MINUTOS = 45

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
        # Remove tudo exceto dígitos, vírgula e ponto
        limpo = "".join(c for c in texto if c.isdigit() or c in ",.")
        if not limpo:
            return None
        if ',' in limpo and '.' in limpo:
            # Formato: 1.234,56
            limpo = limpo.replace('.', '').replace(',', '.')
        elif ',' in limpo:
            # Formato: 154,90
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


def garantir_list_view(page):
    """
    Garante que a wishlist está em MODO LISTA para expor campos de preço.
    Navega para a URL com viewType=list e clica no botão se ainda não estiver
    em lista (o botão aparece quando está em grade).
    """
    url_lista = WISHLIST_URL + "?viewType=list"
    print(f"  🌐 Acessando wishlist (modo lista)...")
    page.goto(url_lista, wait_until='domcontentloaded', timeout=60000)
    time.sleep(2)

    # Se ainda há o link para mudar para lista, clicamos nele
    btn_lista = page.get_by_role("link", name="Mudar para visualização de lista")
    if btn_lista.count() > 0:
        print("  🔄 Alternando para visualização de lista...")
        btn_lista.first.click()
        time.sleep(2)

    # Scroll para carregar todos os itens lazy-loaded
    for _ in range(6):
        page.mouse.wheel(0, 2500)
        time.sleep(0.6)
    time.sleep(1.5)


def verificar_indisponivel(page, url_produto: str) -> bool:
    """
    Abre a página do produto e verifica se está marcado como indisponível.
    Retorna True se estiver indisponível.
    """
    try:
        page.goto(url_produto, wait_until='domcontentloaded', timeout=45000)
        time.sleep(1.5)

        # Seletores comuns de indisponibilidade na Amazon BR
        sels_indisponivel = [
            '#availability',
            '#outOfStock',
            '.a-color-price',
        ]
        for sel in sels_indisponivel:
            try:
                txt = page.locator(sel).first.inner_text(timeout=4000).strip().lower()
                if any(kw in txt for kw in ['não disponível', 'indisponível', 'unavailable',
                                             'out of stock', 'esgotado', 'fora de estoque']):
                    return True
            except Exception:
                continue
    except Exception as e:
        print(f"     ⚠️ Erro ao verificar página do produto: {e}")
    return False


def coletar_itens_da_lista(page) -> list[dict]:
    """
    Lê todos os itens da wishlist em modo lista.
    Retorna lista de dicts com: item_id, titulo, preco (float|None), url_produto.
    """
    garantir_list_view(page)

    itens = []
    linhas = page.locator('li.g-item-sortable').all()
    print(f"  📋 {len(linhas)} itens encontrados na lista.")

    for li in linhas:
        # ── item_id (chave de histórico) ──────────────────────────────────
        item_id = (
            li.get_attribute('data-itemid') or
            li.get_attribute('id') or
            ''
        ).strip()

        # ── ASIN / URL do produto ─────────────────────────────────────────
        asin        = ''
        url_produto = ''
        try:
            outer = li.inner_html()
            m = re.search(r'data-asin="([A-Z0-9]{10})"', outer) or \
                re.search(r'ASIN:([A-Z0-9]{10})', outer) or \
                re.search(r'/dp/([A-Z0-9]{10})/', outer)
            if m:
                asin        = m.group(1)
                url_produto = f"https://www.amazon.com.br/dp/{asin}/"
        except Exception:
            pass

        if not item_id:
            item_id = asin or url_produto   # fallback

        if not item_id:
            continue   # item sem identificação — pula

        # ── Título ────────────────────────────────────────────────────────
        titulo = ''
        for sel_titulo in [
            'a[id^="itemName_"]',
            'a[id^="item-byline-"]',
            '.a-list-item a',
            'span[id^="item-byline-"]',
        ]:
            try:
                t = li.locator(sel_titulo).first.inner_text(timeout=3000).strip()
                if t:
                    titulo = t
                    break
            except Exception:
                continue

        # ── Preço — estratégias específicas para o modo lista ─────────────
        preco      = None
        preco_str  = ''
        sels_preco = [
            '.a-section.price-section .a-offscreen',   # Conforme mapeamento do usuário
            '.a-section.price-section',               # Alternativa no mapeamento
            '.a-price .a-offscreen',
            '.a-price-whole',
            '[data-a-color="price"] .a-offscreen',
        ]
        for sel in sels_preco:
            try:
                loc = li.locator(sel).first
                txt = loc.inner_text(timeout=2000).strip()
                if not txt:
                    # Tenta pegar via atributo se inner_text falhar em elementos ocultos
                    txt = loc.get_attribute('innerText') or ''
                
                p = parse_price(txt)
                if p:
                    preco_str = txt
                    preco     = p
                    break
            except Exception:
                continue

        # Se o preço veio só da parte inteira, tenta pegar os centavos também
        if preco and ',' not in preco_str and '.' not in preco_str:
            try:
                cents = li.locator('.a-price-fraction').first.inner_text(timeout=2000).strip()
                if cents.isdigit():
                    preco_str = f"{int(preco)},{cents}"
                    preco     = parse_price(preco_str)
            except Exception:
                pass

        itens.append({
            'item_id'    : item_id,
            'asin'       : asin,
            'titulo'     : titulo or f"(sem título) [{item_id}]",
            'preco'      : preco,
            'preco_str'  : preco_str,
            'url_produto': url_produto,
        })

    return itens


def monitorar():
    print(f"\n{'=' * 60}")
    print(f"🚀 Wishlist Monitor — {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"{'=' * 60}")

    history = load_history()

    with sync_playwright() as p:
        browser = p.firefox.launch(headless=False)
        ctx_args: dict = {
            'user_agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) '
                'Gecko/20100101 Firefox/123.0'
            ),
            'viewport': {'width': 1440, 'height': 900},
        }
        if os.path.exists(ARQUIVO_SESSAO_AM):
            ctx_args['storage_state'] = ARQUIVO_SESSAO_AM
            print("  🔐 Sessão Amazon carregada")

        context = browser.new_context(**ctx_args)
        page    = context.new_page()

        try:
            itens = coletar_itens_da_lista(page)

            if not itens:
                print("  ⚠️ Nenhum item encontrado. Verifique a sessão ou URL.")
                return

            print(f"\n  🔎 Analisando {len(itens)} itens...")

            for i, item in enumerate(itens, 1):
                item_id     = item['item_id']
                titulo      = item['titulo']
                preco_now   = item['preco']
                url_produto = item['url_produto']

                print(f"\n  [{i}/{len(itens)}] {titulo[:70]}")
                print(f"       Preço atual: {item['preco_str'] or '(não encontrado)'}")

                # ── Sem preço → verificar disponibilidade ─────────────────
                if preco_now is None:
                    disponivel = False
                    if url_produto:
                        print(f"     🔍 Abrindo página para verificar disponibilidade...")
                        indisponivel = verificar_indisponivel(page, url_produto)
                        if indisponivel:
                            print(f"     ❌ Item indisponível na Amazon.")
                            # Registra / mantém no histórico como indisponível
                            if item_id in history:
                                history[item_id]['indisponivel'] = True
                            else:
                                history[item_id] = {
                                    'titulo'        : titulo,
                                    'preco'         : None,
                                    'indisponivel'  : True,
                                    'data_registro' : datetime.now().isoformat(),
                                }
                        else:
                            print(f"     ⚠️ Preço não localizado (mas pode estar disponível).")
                    else:
                        print(f"     ⚠️ Sem URL do produto — não é possível verificar.")
                    continue

                # ── Com preço → análise fria vs histórico ─────────────────
                if item_id in history:
                    registro   = history[item_id]
                    old_price  = registro.get('preco')

                    # Atualiza histórico com preço atual
                    history[item_id].update({
                        'titulo'        : titulo,
                        'preco'         : preco_now,
                        'indisponivel'  : False,
                        'ultima_coleta' : datetime.now().isoformat(),
                    })

                    if old_price is not None and preco_now < old_price:
                        reducao = old_price - preco_now
                        pct     = (reducao / old_price) * 100

                        msg = (
                            "💎 <b>OFERTA ENCONTRADA!</b>\n"
                            "───────────────────\n"
                            f"📦 <b>{titulo}</b>\n\n"
                            f"📉 <b>Queda detectada:</b>\n"
                            f"❌ De: <s>{format_price(old_price)}</s>\n"
                            f"✅ Por: <b>{format_price(preco_now)}</b>\n\n"
                            f"🔥 <b>Economia de {format_price(reducao)} ({pct:.1f}% OFF)</b>\n"
                            "───────────────────\n"
                            f"🔗 <a href='{url_produto}'>COMPRAR NA AMAZON</a>"
                        )

                        print(f"     🔥 BAIXOU! {format_price(old_price)} → {format_price(preco_now)}")
                        send_personal_msg(msg)

                    elif old_price is not None and preco_now > old_price:
                        print(f"     📈 Subiu: {format_price(old_price)} → {format_price(preco_now)}")

                    else:
                        print(f"     ✅ Preço estável: {format_price(preco_now)}")

                else:
                    # Primeiro registro deste item
                    history[item_id] = {
                        'titulo'        : titulo,
                        'preco'         : preco_now,
                        'indisponivel'  : False,
                        'data_registro' : datetime.now().isoformat(),
                        'ultima_coleta' : datetime.now().isoformat(),
                    }
                    print(f"     ✅ Novo item registrado: {format_price(preco_now)}")

                time.sleep(0.8)

            save_history(history)
            print(f"\n  ✅ Feito! Próxima verificação em {INTERVALO_MINUTOS} min.")

        except Exception as e:
            print(f"  ❌ Erro crítico: {e}")
            import traceback; traceback.print_exc()
        finally:
            context.close()
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
