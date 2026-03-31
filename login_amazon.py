"""
login_amazon.py — mminis
Abre o Firefox, você faz o login normalmente na Amazon,
e o script salva a sessão em session.json.

A partir daí, o buscar_amazon.py usa essa sessão
automaticamente — sem precisar logar de novo.

USO:
  python login_amazon.py

QUANDO RODAR DE NOVO:
  - Se o buscar_amazon.py começar a pedir captcha
  - Se der erro de "não logado"
  - Aproximadamente a cada 30 dias (sessão expira)
"""

import json
import os
import time
from playwright.sync_api import sync_playwright
import tkinter as tk
from tkinter import simpledialog

ARQUIVO_SESSAO = 'session.json'

def salvar_sessao(page, context):
    """Salva cookies + localStorage em session.json"""
    state = context.storage_state()
    with open(ARQUIVO_SESSAO, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    print(f"\n✅ Sessão salva em '{ARQUIVO_SESSAO}'")
    print("   O buscar_amazon.py vai usar esse arquivo automaticamente.\n")

def main():
    print("=" * 55)
    print("  mminis — Login Amazon")
    print("=" * 55)
    print("""
O que vai acontecer:
  1. Um navegador Firefox vai abrir
  2. Você faz o login normal na Amazon
     (e-mail, senha, código 2FA se tiver)
  3. Quando estiver logado, volte aqui e
     pressione ENTER para salvar a sessão
  4. O navegador fecha e você está pronto

⚠️  Não feche o navegador manualmente.
""")
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    simpledialog.askstring("Abrir Navegador", "O Firefox vai abrir para você logar.\nClique OK para continuar.", initialvalue="OK")
    root.destroy()

    with sync_playwright() as p:
        browser = p.firefox.launch(
            headless=False,
            slow_mo=50,        # leve delay para parecer humano
        )
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
            viewport={'width': 1440, 'height': 900},
        )
        page = context.new_page()

        # Abre direto na página de login da Amazon BR
        print("\n🌐 Abrindo Amazon Brasil...")
        page.goto('https://www.amazon.com.br/ap/signin?openid.pape.max_auth_age=0&openid.return_to=https%3A%2F%2Fwww.amazon.com.br%2F&openid.identity=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid.assoc_handle=brflex&openid.mode=checkid_setup&openid.claimed_id=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid.ns=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0',
            wait_until='domcontentloaded'
        )

        print("\n👉 Faça o login no navegador que abriu.")
        print("   Depois que estiver na página principal da Amazon,")
        print("   volte aqui e pressione ENTER.\n")
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        simpledialog.askstring("Confirmar Login", "Após estar logado na Amazon (página principal),\nvolte aqui e clique OK.", initialvalue="OK")
        root.destroy()

        # Verifica se está logado de fato
        try:
            page.wait_for_selector('#nav-link-accountList', timeout=5000)
            nome_elem = page.locator('#nav-link-accountList-nav-line-1').first
            nome = nome_elem.inner_text() if nome_elem else ''
            if nome and 'Olá' in nome or 'Conta' in nome:
                print(f"\n✅ Login confirmado!")
        except Exception:
            # não conseguiu confirmar, mas tudo bem — salva mesmo assim
            pass

        # Navega para o Associates para garantir cookies de afiliado
        print("\n🔗 Acessando painel de afiliados para salvar cookies completos...")
        try:
            page.goto('https://associados.amazon.com.br/', wait_until='domcontentloaded', timeout=20000)
            time.sleep(3)
        except Exception:
            print("   (painel de afiliados não abriu, mas tudo bem)")

        # Salva
        salvar_sessao(page, context)
        browser.close()

    # Verifica se o arquivo foi criado
    if os.path.exists(ARQUIVO_SESSAO):
        tamanho = os.path.getsize(ARQUIVO_SESSAO)
        print(f"📁 Arquivo: {ARQUIVO_SESSAO} ({tamanho:,} bytes)")
        print("\n🚀 Próximo passo: rode o buscar_amazon.py normalmente.")
        print("   Ele vai usar essa sessão automaticamente.\n")
    else:
        print("⚠️  Algo deu errado — o arquivo não foi criado.")
        print("   Tente rodar o script novamente.\n")


if __name__ == '__main__':
    main()
