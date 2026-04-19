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
ML_FAVORITOS_URL  = "https://myaccount.mercadolivre.com.br/bookmarks/list"
ARQUIVO_HISTORICO = 'wishlist_history.json'
ARQUIVO_SESSAO_AM = 'session.json'
ARQUIVO_SESSAO_ML = 'session_ml.json'
INTERVALO_MINUTOS = 120
THRESHOLD_PCT     = 2.0
ARQUIVO_SUMMARY   = 'last_summary.txt'

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


def _get_affiliate_amazon(page, url: str) -> str:
    """Gera link de afiliado Amazon via SiteStripe (Codegen do usuário)."""
    try:
        print(f"     🔗 Gerando link de afiliado...")
        page.goto(url, wait_until='domcontentloaded', timeout=45000)
        time.sleep(1.5)

        # Codegen: button "Obter link"
        try:
            btn = page.get_by_role("button", name="Obter link").first
            btn.wait_for(state='visible', timeout=5000)
            btn.click()
            time.sleep(2)
            
            campo = page.get_by_role("textbox", name="Generated short link").first
            campo.wait_for(state='visible', timeout=4000)
            val = campo.get_attribute('value') or campo.input_value()
            if val and ('amzn.to' in val or 'amazon.com' in val):
                print(f"       ✅ Link capturado: {val[:30]}...")
                return val
        except Exception:
            pass
        
        # Fallback seletores antigos
        for sel in ['#amzn-ss-get-link-button', '#SL_text_link']:
            try:
                btn = page.locator(sel).first
                btn.wait_for(state='visible', timeout=3000)
                btn.click()
                time.sleep(2)
                
                for fsel in ['#amzn-ss-text-shortlink-textarea', '#SL_text_short_link']:
                    campo = page.locator(fsel).first
                    if campo.count() > 0:
                        val = campo.get_attribute('value') or campo.input_value()
                        if val and 'amzn.to' in val:
                            return val
            except Exception:
                pass
                
        print("     ⚠️  Usando link original.")
        return url
    except Exception:
        return url


def _get_affiliate_ml(page, url: str) -> str:
    """Gera link de afiliado Mercado Livre (Codegen do usuário)."""
    try:
        print(f"     🔗 Gerando link de afiliado ML...")
        # Usa o mesmo seletor que buscar_ml.py
        try:
            btn = page.get_by_test_id("generate_link_button").first
            btn.wait_for(state='visible', timeout=5000)
            btn.click()
            time.sleep(2)
            
            el = page.locator('[data-testid="text-field__label_link"]').first
            el.wait_for(state='visible', timeout=3000)
            val = el.get_attribute('value') or el.input_value() or el.inner_text()
            if val and 'mercadolivre.com' in val:
                print(f"       ✅ Link capturado: {val[:30]}...")
                return val
        except Exception:
            pass
            
        print("     ⚠️  Usando link original.")
        return url
    except Exception:
        return url


def enviar_resumo_diario(history: dict):
    """Envia uma lista de todos os itens sendo monitorados."""
    try:
        agora = datetime.now()
        data_hoje = agora.strftime('%Y-%m-%d')
        
        # Só envia se for 9h da manhã (ou depois) e ainda não enviou hoje
        if agora.hour < 9:
            return

        if os.path.exists(ARQUIVO_SUMMARY):
            with open(ARQUIVO_SUMMARY, 'r') as f:
                if f.read().strip() == data_hoje:
                    return

        print("\n📅 Gerando resumo diário de monitoramento...")
        
        itens_amz = [v for k, v in history.items() if v.get('plataforma') == 'Amazon']
        itens_ml  = [v for k, v in history.items() if v.get('plataforma') == 'Mercado Livre']
        
        msg = f"🌅 <b>BOM DIA! RESUMO DE MONITORAMENTO</b>\n{agora.strftime('%d/%m/%Y %H:%M')}\n"
        msg += "───────────────────\n\n"
        
        if itens_amz:
            msg += f"🛒 <b>AMAZON ({len(itens_amz)} itens):</b>\n"
            for it in itens_amz:
                status = "❌ Indisponível" if it.get('indisponivel') else format_price(it.get('preco', 0))
                msg += f"• {it['titulo'][:40]}...: <b>{status}</b>\n"
            msg += "\n"
            
        if itens_ml:
            msg += f"🔵 <b>MERCADO LIVRE ({len(itens_ml)} itens):</b>\n"
            for it in itens_ml:
                status = format_price(it.get('preco', 0)) if it.get('preco') else "❓ s/ preço"
                msg += f"• {it['titulo'][:40]}...: <b>{status}</b>\n"
        
        if not itens_amz and not itens_ml:
            msg += "⚠️ Ninguém sendo monitorado no momento."

        ok = send_personal_msg(msg)
        if ok:
            with open(ARQUIVO_SUMMARY, 'w') as f:
                f.write(data_hoje)
            print("  ✅ Resumo diário enviado!")

    except Exception as e:
        print(f"  ⚠️ Erro ao enviar resumo diário: {e}")


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


def coletar_itens_ml(page) -> list[dict]:
    """
    Lê todos os itens dos favoritos do Mercado Livre.
    """
    print(f"  🌐 Acessando favoritos do Mercado Livre...")
    page.goto(ML_FAVORITOS_URL, wait_until='domcontentloaded', timeout=60000)
    time.sleep(2)

    # Scroll para carregar favoritos
    for _ in range(5):
        page.mouse.wheel(0, 1500)
        time.sleep(0.5)
    time.sleep(1)

    itens = []
    # Seletores baseados em buscar_ml e estrutura comum de favoritos
    cards = page.locator('div.ui-favorites-item, .ui-search-result, .poly-card').all()
    print(f"  📋 {len(cards)} itens encontrados nos favoritos ML.")

    for card in cards:
        try:
            # ── Link e ID ──────────────────
            link_el = card.locator('a[href*="mercadolivre.com.br"]').first
            url = link_el.get_attribute('href') or ''
            if not url: continue
            
            # ID do produto no ML costuma estar na URL (MLB...)
            match = re.search(r'(MLB-?\d+)', url)
            item_id = match.group(1) if match else url.split('?')[0].split('/')[-1]
            
            # ── Título ──────────────────
            titulo = ""
            for t_sel in ['.ui-favorites-item__title', '.poly-component__title', 'h2']:
                try:
                    t = card.locator(t_sel).first.inner_text(timeout=1000).strip()
                    if t:
                        titulo = t
                        break
                except: continue
            
            # ── Preço ──────────────────
            preco = None
            preco_str = ""
            try:
                # Tenta fragmentos de preço (andes-money-amount)
                frac = card.locator('.andes-money-amount__fraction').first.inner_text(timeout=1000).strip()
                try:
                    cents = card.locator('.andes-money-amount__cents').first.inner_text(timeout=500).strip()
                except: cents = "00"
                
                preco_str = f"{frac},{cents}"
                preco = parse_price(preco_str)
            except:
                # Fallback texto direto
                try:
                    txt = card.inner_text().replace('\n', ' ')
                    m = re.search(r'R\$\s*([\d\.]+,?\d*)', txt)
                    if m:
                        preco_str = m.group(1)
                        preco = parse_price(preco_str)
                except: pass

            itens.append({
                'item_id': f"ml_{item_id}",
                'titulo': titulo or f"Produto ML [{item_id}]",
                'preco': preco,
                'preco_str': preco_str,
                'url_produto': url,
                'plataforma': 'Mercado Livre'
            })
        except Exception as e:
            print(f"     ⚠️ Erro ao processar card ML: {e}")

    return itens


def monitorar():
    print(f"\n{'=' * 60}")
    print(f"🚀 Wishlist Monitor — {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"{'=' * 60}")

    history = load_history()

    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True)
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
            # --- COLETA AMAZON ---
            itens_amz = []
            amz_success = False
            if os.path.exists(ARQUIVO_SESSAO_AM):
                try:
                    itens_amz = coletar_itens_da_lista(page)
                    for it in itens_amz: it['plataforma'] = 'Amazon'
                    amz_success = True
                except Exception as e:
                    print(f"  ❌ Erro ao coletar Amazon: {e}")
            
            # --- COLETA MERCADO LIVRE ---
            itens_ml = []
            ml_success = False
            if os.path.exists(ARQUIVO_SESSAO_ML):
                try:
                    # Troca de contexto para carregar sessão ML
                    context_ml = browser.new_context(
                        storage_state=ARQUIVO_SESSAO_ML,
                        user_agent=ctx_args['user_agent'],
                        viewport=ctx_args['viewport']
                    )
                    page_ml = context_ml.new_page()
                    itens_ml = coletar_itens_ml(page_ml)
                    ml_success = True
                    page_ml.close()
                    context_ml.close()
                except Exception as e:
                    print(f"  ❌ Erro ao coletar Mercado Livre: {e}")
            else:
                print("  ⚠️ Sessão Mercado Livre não encontrada (session_ml.json).")

            itens = itens_amz + itens_ml

            if not itens:
                print("  ⚠️ Nenhum item encontrado em nenhuma plataforma.")
                return

            print(f"\n  🔎 Analisando {len(itens)} itens ({len(itens_amz)} Amz, {len(itens_ml)} ML)...")

            itens_baixaram = []
            ids_vistos = set()
            for i, item in enumerate(itens, 1):
                item_id     = item['item_id']
                # Garante prefixo se não tiver (compatibilidade com histórico antigo)
                if not item_id.startswith('ml_') and item.get('plataforma') == 'Amazon' and not item_id.startswith('amz_'):
                    item_id = f"amz_{item_id}"
                
                ids_vistos.add(item_id)
                
                titulo      = item['titulo']
                preco_now   = item['preco']
                url_produto = item['url_produto']
                plat        = item.get('plataforma', 'Amazon')

                print(f"\n  [{i}/{len(itens)}] [{plat}] {titulo[:70]}")
                print(f"       Preço atual: {item['preco_str'] or '(não encontrado)'}")

                # ── Sem preço → verificar disponibilidade (Só Amazon por enquanto) ──
                if preco_now is None:
                    if plat == 'Amazon' and url_produto:
                        print(f"     🔍 Abrindo página para verificar disponibilidade...")
                        indisponivel = verificar_indisponivel(page, url_produto)
                        if indisponivel:
                            print(f"     ❌ Item indisponível na Amazon.")
                            if item_id in history:
                                history[item_id]['indisponivel'] = True
                            else:
                                history[item_id] = {
                                    'titulo'        : titulo,
                                    'preco'         : None,
                                    'indisponivel'  : True,
                                    'plataforma'    : plat,
                                    'data_registro' : datetime.now().isoformat(),
                                }
                        else:
                            print(f"     ⚠️ Preço não localizado (mas pode estar disponível).")
                    else:
                        print(f"     ⚠️ Preço não localizado.")
                    continue

                # ── Com preço → análise vs histórico ─────────────────
                if item_id in history:
                    registro   = history[item_id]
                    old_price  = registro.get('preco')

                    # Atualiza histórico
                    history[item_id].update({
                        'titulo'        : titulo,
                        'preco'         : preco_now,
                        'indisponivel'  : False,
                        'plataforma'    : plat,
                        'ultima_coleta' : datetime.now().isoformat(),
                    })

                    if old_price is not None and preco_now < old_price:
                        reducao = old_price - preco_now
                        pct     = (reducao / old_price) * 100

                        if pct < THRESHOLD_PCT:
                            print(f"     ✅ Queda ignorada ({pct:.2f}% < {THRESHOLD_PCT}%: centavos/variação mínima)")
                            # Mesmo assim atualiza o preço no histórico para acompanhar a variação
                            history[item_id].update({
                                'titulo'        : titulo,
                                'preco'         : preco_now,
                                'plataforma'    : plat,
                                'ultima_coleta' : datetime.now().isoformat(),
                            })
                            continue

                        print(f"     🔥 BAIXOU! {format_price(old_price)} → {format_price(preco_now)}")
                        
                        try:
                            # Tenta gerar link de afiliado e mensagem completa
                            link_final = url_produto
                            btn_text   = "COMPRAR"
                            emoji      = "💎" if plat == 'Amazon' else "🔵"

                            if plat == 'Amazon':
                                link_final = _get_affiliate_amazon(page, url_produto)
                                btn_text = "COMPRAR NA AMAZON"
                            else:
                                context_ml = browser.new_context(
                                    storage_state=ARQUIVO_SESSAO_ML,
                                    user_agent=ctx_args.get('user_agent'),
                                    viewport=ctx_args.get('viewport')
                                )
                                p_ml = context_ml.new_page()
                                try:
                                    link_final = _get_affiliate_ml(p_ml, url_produto)
                                finally:
                                    p_ml.close()
                                    context_ml.close()
                                btn_text = "COMPRAR NO MERCADO LIVRE"

                            msg = (
                                f"{emoji} <b>OFERTA ENCONTRADA!</b>\n"
                                "───────────────────\n"
                                f"📦 <b>{titulo}</b>\n\n"
                                f"📉 <b>Queda detectada:</b>\n"
                                f"❌ De: <s>{format_price(old_price)}</s>\n"
                                f"✅ Por: <b>{format_price(preco_now)}</b>\n\n"
                                f"🔥 <b>Economia de {format_price(reducao)} ({pct:.1f}% OFF)</b>\n"
                                "───────────────────\n"
                                f"🔗 <a href='{link_final}'>{btn_text}</a>"
                            )
                            send_personal_msg(msg)

                        except Exception as e_alert:
                            print(f"     ⚠️ Erro ao gerar alerta detalhado: {e_alert}. Enviando fallback básico.")
                            # Fallback básico: apenas dados essenciais sem link de afiliado "limpo"
                            msg_fallback = (
                                f"⚠️ <b>BAIXOU DE PREÇO (ALERTA BÁSICO)</b>\n"
                                f"📦 {titulo}\n"
                                f"💰 {format_price(old_price)} → <b>{format_price(preco_now)}</b>\n"
                                f"🔗 <a href='{url_produto}'>ABRIR PRODUTO</a>"
                            )
                            send_personal_msg(msg_fallback)

                        # Adiciona à relação para o resumo final
                        itens_baixaram.append({
                            'titulo': titulo,
                            'de': old_price,
                            'por': preco_now,
                            'plat': plat
                        })

                    elif old_price is not None and preco_now > old_price:
                        print(f"     📈 Subiu: {format_price(old_price)} → {format_price(preco_now)}")
                    else:
                        print(f"     ✅ Preço estável: {format_price(preco_now)}")

                else:
                    # Novo registro
                    history[item_id] = {
                        'titulo'        : titulo,
                        'preco'         : preco_now,
                        'indisponivel'  : False,
                        'plataforma'    : plat,
                        'data_registro' : datetime.now().isoformat(),
                        'ultima_coleta' : datetime.now().isoformat(),
                    }
                    print(f"     ✅ Novo item registrado: {format_price(preco_now)}")

                time.sleep(0.5)

            # --- LIMPEZA DE REMOVIDOS ---
            removidos = 0
            keys_to_delete = []
            for k, v in list(history.items()):
                plat = v.get('plataforma')
                if plat == 'Amazon' and amz_success:
                    if k not in ids_vistos:
                        keys_to_delete.append(k)
                elif plat == 'Mercado Livre' and ml_success:
                    if k not in ids_vistos:
                        keys_to_delete.append(k)
            
            for k in keys_to_delete:
                del history[k]
                removidos += 1
            
            if removidos > 0:
                print(f"  🧹 Removidos {removidos} itens que não estão mais nos favoritos.")

            save_history(history)
            enviar_resumo_diario(history)

            # --- RESUMO FINAL (Fallback de Redação) ---
            if itens_baixaram:
                print(f"  📝 Enviando resumo de {len(itens_baixaram)} quedas detectedas...")
                summary = "📋 <b>RESUMO DE QUEDAS (Rodada Atual)</b>\n"
                summary += "───────────────────\n"
                for alert in itens_baixaram:
                    p_de  = format_price(alert['de'])
                    p_por = format_price(alert['por'])
                    summary += f"• <b>[{alert['plat']}]</b> {alert['titulo'][:40]}...\n  <s>{p_de}</s> ➔ <b>{p_por}</b>\n\n"
                
                send_personal_msg(summary)

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
