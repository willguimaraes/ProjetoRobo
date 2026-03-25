import sys
import os
import threading
import asyncio
import requests
import random
from bs4 import BeautifulSoup
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
import schedule
import time
from http.server import HTTPServer, BaseHTTPRequestHandler

# --- 1. ESTABILIDADE (RENDER) ---
sys.stdout.reconfigure(line_buffering=True)

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot Categorias Ativo")
    def log_message(self, format, *args): return

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHandler)
    server.serve_forever()

def self_ping():
    app_url = os.environ.get("RENDER_EXTERNAL_URL")
    while True:
        if app_url:
            try: requests.get(app_url, timeout=10)
            except: pass
        time.sleep(300)

threading.Thread(target=run_server, daemon=True).start()
threading.Thread(target=self_ping, daemon=True).start()

# --- 2. CONFIGURAÇÕES ---
TOKEN = os.environ.get('TELEGRAM_TOKEN')
MATT_TOOL = os.environ.get('MATT_TOOL')
MATT_WORD = os.environ.get('MATT_WORD')
AMAZON_TAG = os.environ.get('AMAZON_TAG')
CHAVE_DO_CANAL = '@promodagota'
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'}

# --- 3. LISTA DE CATEGORIAS (MINAS DE OURO) ---
CATEGORIAS_ML = [
    {"nome": "TECNOLOGIA", "url": "https://www.mercadolivre.com.br/ofertas#c_id=MLB1051&category=MLB1051"},
    {"nome": "CASA E COZINHA", "url": "https://www.mercadolivre.com.br/ofertas#c_id=MLB1574&category=MLB1574"},
    {"nome": "BELEZA", "url": "https://www.mercadolivre.com.br/ofertas#c_id=MLB1246&category=MLB1246"},
    {"nome": "SUPERMERCADO", "url": "https://www.mercadolivre.com.br/ofertas#c_id=MLB1403&category=MLB1403"}
]

ofertas_postadas = []
indice_cat = 0
tentar_amazon = True # Alterna entre ML e Amazon

# --- 4. BUSCA E POSTAGEM ---

async def buscar_ml(cat_info):
    global ofertas_postadas
    print(f"🔎 [ML] Setor: {cat_info['nome']}")
    try:
        res = requests.get(cat_info['url'], headers=HEADERS, timeout=25)
        site = BeautifulSoup(res.text, 'html.parser')
        produtos = site.find_all(['li', 'div'], class_=['promotion-item', 'poly-card', 'promotion-item__container'])
        
        candidatos = []
        for p in produtos:
            link_e = p.find('a', href=True)
            if not link_e: continue
            link = link_e['href'].split("#")[0]
            if link in ofertas_postadas: continue
            
            nome_e = p.find(['p', 'h2', 'h3']) or p.select_one('.poly-component__title')
            c_novo = p.select_one('.andes-money-amount--current') or p.select_one('.poly-price__current')
            c_antigo = p.select_one('.andes-money-amount--previous')
            
            if nome_e and c_novo:
                p_novo = c_novo.find('span', class_='andes-money-amount__fraction').text.strip()
                p_antigo = c_antigo.find('span', class_='andes-money-amount__fraction').text.strip() if c_antigo else None
                img = p.find('img').get('data-src') or p.find('img').get('src') if p.find('img') else None
                candidatos.append({'nome': nome_e.text.strip(), 'novo': p_novo, 'antigo': p_antigo, 'link': link, 'img': img, 'loja': 'Mercado Livre'})

        if candidatos:
            item = random.choice(candidatos[:25])
            link_af = f"{item['link']}{'&' if '?' in item['link'] else '?'}matt_tool={MATT_TOOL}&matt_word={MATT_WORD}"
            await enviar_telegram(item, link_af)
            ofertas_postadas.append(item['link'])
            return True
    except Exception as e: print(f"❌ Erro ML: {e}")
    return False

async def buscar_amazon():
    # ... (mesma lógica do Plano B anterior) ...
    # Se falhar, ele retorna buscar_ml(CATEGORIAS_ML[0])
    # [Mantido conforme versão anterior para segurança]
    print("🔎 [AMZ] Tentando Amazon...")
    try:
        res = requests.get
