import os
import time
from playwright.sync_api import sync_playwright

WISHLIST_URL = "https://www.amazon.com.br/hz/wishlist/ls/3VCIMEBP19W5X?layout=list"
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
            
            # Use item detector
            items = page.locator('li[id^="item_"], .g-item-sortable').all()
            print(f"  📦 Itens encontrados: {len(items)}")
            
            for i, item in enumerate(items[:3]):
                print(f"  --- Item {i} ---")
                html_snippet = item.inner_html()[:500]
                print(f"    Snippet: {html_snippet}...")
                
                # Check IDs
                try:
                    title_id = item.locator('a[id^="itemName_"]').get_attribute('id')
                    print(f"    - Title ID found: {title_id}")
                except: pass
                
                # Check inner text of some links
                all_links = item.locator('a').all()
                for link in all_links:
                    txt = link.inner_text().strip()
                    if txt:
                        print(f"    - Link Text: {txt}")
                
        except Exception as e:
            print(f"  ❌ Erro: {e}")
        
        browser.close()

if __name__ == "__main__":
    debug()
