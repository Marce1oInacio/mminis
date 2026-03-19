import os
import time
from playwright.sync_api import sync_playwright

WISHLIST_ID = "3VCIMEBP19W5X"
PRINT_URL = f"https://www.amazon.com.br/hz/wishlist/printview/{WISHLIST_ID}?filter=all&sort=default&layout=standard"
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
        
        print(f"  🌐 Indo para Print View: {PRINT_URL}")
        try:
            page.goto(PRINT_URL, wait_until='domcontentloaded', timeout=60000)
            time.sleep(5)
            print(f"  📖 Título: {page.title()}")
            page.screenshot(path="wishlist_print_debug.png")
            
            # No print view, items are usually in a table with class 'g-print-view-layout'
            # Selectors: table.g-print-view-layout tr
            rows = page.locator('table.g-print-view-layout tr').all()
            print(f"  📦 Linhas encontradas (print view): {len(rows)}")
            
            for i, row in enumerate(rows[:5]):
                txt = row.inner_text().replace('\n', ' ')
                print(f"    - Linha {i}: {txt[:100]}...")
                
        except Exception as e:
            print(f"  ❌ Erro: {e}")
        
        browser.close()

if __name__ == "__main__":
    debug()
