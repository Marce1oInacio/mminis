"""
Dump the wishlist HTML to file so we can find where ASINs are.
"""
import os, time, re
from playwright.sync_api import sync_playwright

WISHLIST_URL = "https://www.amazon.com.br/hz/wishlist/ls/3VCIMEBP19W5X"
SESSAO = 'session.json'

with sync_playwright() as p:
    browser = p.firefox.launch(headless=True)
    ctx = {}
    if os.path.exists(SESSAO):
        ctx['storage_state'] = SESSAO
        print("Sessão carregada")
    context = browser.new_context(
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
        viewport={'width': 1440, 'height': 900},
        **ctx
    )
    page = context.new_page()
    page.goto(WISHLIST_URL, wait_until='domcontentloaded', timeout=60000)
    time.sleep(4)
    
    # Screenshot
    page.screenshot(path="wishlist_dump.png")
    print(f"Título: {page.title()}")
    
    # Conta itens by various selectors
    for sel in ['li[data-asin]', 'li[id^="item_"]', '.g-item-sortable', '[data-item-prime-info]']:
        count = page.locator(sel).count()
        print(f"  '{sel}': {count}")
    
    # Salva o HTML
    html = page.content()
    with open('wishlist_dump.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("HTML salvo em wishlist_dump.html")
    
    # Procura padrões de ASIN
    asins_regex = re.findall(r'data-asin="([A-Z0-9]{10})"', html)
    asins_json  = re.findall(r'"asin"\s*:\s*"([A-Z0-9]{10})"', html)
    asins_item  = re.findall(r'id="item_([A-Z0-9]{10})"', html)
    print(f"ASINs via data-asin attr: {asins_regex[:5]}")
    print(f"ASINs via JSON: {asins_json[:5]}")  
    print(f"ASINs via item_ id: {asins_item[:5]}")
    
    browser.close()
