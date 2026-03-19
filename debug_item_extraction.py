import os
import time
from playwright.sync_api import sync_playwright

WISHLIST_URL = "https://www.amazon.com.br/hz/wishlist/ls/3VCIMEBP19W5X/ref=nav_wishlist_lists_1"
ARQUIVO_SESSAO_AM = 'session.json'

def debug():
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True)
        ctx_args = {
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
            'viewport': {'width': 1440, 'height': 900},
        }
        if os.path.exists(ARQUIVO_SESSAO_AM):
            ctx_args['storage_state'] = ARQUIVO_SESSAO_AM
            print("  🔐 Sessão Amazon carregada")
            
        context = browser.new_context(**ctx_args)
        page = context.new_page()
        
        try:
            page.goto(WISHLIST_URL, wait_until='domcontentloaded', timeout=60000)
            page.wait_for_load_state('networkidle')
            time.sleep(5)
            
            items = page.locator('li[id^="item_"], .g-item-sortable').all()
            print(f"  📦 Itens encontrados: {len(items)}")
            
            for i, item in enumerate(items[:3]):
                print(f"  --- Item {i} ---")
                # Tenta pegar name selectors
                name_els = ['[id^="itemName_"]', 'a.a-link-normal', 'span.a-size-base']
                for sel in name_els:
                    try:
                        t = item.locator(sel).first.inner_text().strip()
                        if t:
                            print(f"    - Nome ({sel}): {t}")
                            break
                    except: pass
                
                # Tenta pegar price selectors
                price_els = ['span.a-price span.a-offscreen', '[id^="itemPrice_"]', '.a-color-price']
                for sel in price_els:
                    try:
                        p_val = item.locator(sel).first.inner_text().strip()
                        if p_val:
                            print(f"    - Preço ({sel}): {p_val}")
                            break
                    except: pass
            
            page.screenshot(path="wishlist_final_debug.png")
            print("  📸 Screenshot salvo em wishlist_final_debug.png")
                
        except Exception as e:
            print(f"  ❌ Erro: {e}")
        
        browser.close()

if __name__ == "__main__":
    debug()
