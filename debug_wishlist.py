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
        
        print(f"  🌐 Indo para {WISHLIST_URL}")
        try:
            page.goto(WISHLIST_URL, wait_until='domcontentloaded', timeout=60000)
            time.sleep(5)
            print(f"  📖 Título: {page.title()}")
            page.screenshot(path="wishlist_debug.png")
            print("  📸 Screenshot salvo em wishlist_debug.png")
            
            # Tenta encontrar itens
            items = page.locator('li[id^="item_"], .g-item-sortable').all()
            print(f"  📦 Itens encontrados (seletor 1): {len(items)}")
            
            if not items:
                # Tenta outro seletor
                items = page.locator('.a-list-item').all()
                print(f"  📦 Itens encontrados (seletor 2): {len(items)}")
            
            # Se ainda 0, mostra HTML parcial
            if not items:
                print("  ⚠️ Nenhum item encontrado. HTML parcial:")
                print(page.content()[:1000])
                
        except Exception as e:
            print(f"  ❌ Erro: {e}")
        
        browser.close()

if __name__ == "__main__":
    debug()
