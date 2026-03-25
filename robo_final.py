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

# --- 1. SISTEMA DE SOBREVIVÊNCIA (RENDER & UPTIME) ---
sys.stdout.reconfigure(line_buffering=True)

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot @promodagota - Sistema Ativo")
    def log_message(self, format, *args): return

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHandler)
    server.serve_forever()

def self_ping():
    """ Faz o bot 'ligar' para si mesmo para o Render não dormir """
    app_url = os.environ.get("RENDER_EXTERNAL_URL")
    while True:
        if app_url:
            try:
                requests.get(app_url, timeout=10)
                print("💓 Heartbeat: Servidor acordado.")
            except: pass
        time.sleep(300) # A cada 5 min

threading.Thread(target=run_server, daemon=True).start()
threading.Thread(target=self_ping, daemon=True).start()

# --- 2. CONFIGURAÇÕES ---
TOKEN = os.environ.get('TELEGRAM_TOKEN')
MATT_TOOL = os.environ.get('MATT_TOOL')
MATT_WORD = os.environ.get('MATT_WORD')
AMAZON_TAG = os.environ.get('AMAZON_TAG')
CHAVE_DO_CANAL = '@promodagota'
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'}

ofertas_postadas = []
lojas = ["ML", "AMZ"]
ponteiro_loja = 0

# --- 3. MOTOR DE BUSCA INTELIGENTE ---

async def buscar_ml():
    global ofertas_postadas
    print("🔎 [ML] Vasculhando ofertas...")
    try:
        res = requests.get('https://www.mercadolivre.com.br/ofertas#nav-header', headers=HEADERS, timeout=25)
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
            item = random.choice(candidatos[:30])
            link_af = f"{item['link']}{'&' if '?' in item['link'] else '?'}matt_tool={MATT_TOOL}&matt_word={MATT_WORD}"
            await enviar_telegram(item, link_af)
            ofertas_postadas.append(item['link'])
            return True
    except Exception as e: print(f"❌ Erro ML: {e}")
    return False

async def buscar_amazon():
    global ofertas_postadas
    print("🔎 [AMZ] Tentando capturar ofertas...")
    try:
        res = requests.get('https://www.amazon.com.br/gp/goldbox', headers=HEADERS, timeout=25)
        site = BeautifulSoup(res.text, 'html.parser')
        
        # Múltiplos seletores para Amazon (Site instável)
        produtos = site.select('div[data-testid="grid-desktop-card"]') or site.select('.s-result-item')
        
        candidatos = []
        for p in produtos:
            link_e = p.find('a', href=True)
            if not link_e: continue
            
            raw_link = link_e['href'].split("?")[0].split("ref=")[0]
            link = "https://www.amazon.com.br" + raw_link if raw_link.startswith('/') else raw_link
            
            if link in ofertas_postadas or "slredirect" in link: continue
            
            nome_e = p.find('img', alt=True) or p.select_one('.a-size-base')
            preco_e = p.select_one('.a-price-whole') or p.select_one('.a-color-price')
            
            if nome_e and preco_e:
                nome = nome_e.get('alt') if nome_e.get('alt') else nome_e.text.strip()
                p_novo = preco_e.text.replace('R$', '').replace(',', '').replace('.', '').strip()
                img = p.find('img')['src'] if p.find('img') else None
                candidatos.append({'nome': nome[:80], 'novo': p_novo, 'antigo': None, 'link': link, 'img': img, 'loja': 'Amazon'})

        if candidatos:
            item = random.choice(candidatos[:15])
            link_af = f"{item['link']}?tag={AMAZON_TAG}"
            await enviar_telegram(item, link_af)
            ofertas_postadas.append(item['link'])
            return True
        else:
            print("⚠️ Amazon sem ofertas válidas agora. Acionando PLANO B (ML)...")
            return await buscar_ml() # Se a Amazon falhar, o ML assume na hora!

    except Exception as e: 
        print(f"❌ Erro Amazon: {e}")
        return await buscar_ml() # Plano B em caso de erro crítico

async def enviar_telegram(item, link):
    bot = Bot(token=TOKEN)
    preco_html = f"❌ De: <s>R$ {item['antigo']},00</s>\n✅ <b>Por: R$ {item['novo']},00</b>" if item['antigo'] else f"💰 <b>Preço: R$ {item['novo']},00</b>"
    texto = f"🔥 <b>OFERTA {item['loja'].upper()}!</b> 🔥\n\n📦 {item['nome']}\n\n{preco_html}\n\n⚡ <i>Aproveite na {item['loja']}!</i>"
    teclado = InlineKeyboardMarkup([[InlineKeyboardButton(f"🛒 VER NA {item['loja'].upper()}", url=link)]])
    try:
        if item['img']: await bot.send_photo(chat_id=CHAVE_DO_CANAL, photo=item['img'], caption=texto, parse_mode='HTML', reply_markup=teclado)
        else: await bot.send_message(chat_id=CHAVE_DO_CANAL, text=texto, parse_mode='HTML', reply_markup=teclado)
        print(f"✅ POSTADO: {item['loja']}")
    except Exception as e: print(f"Erro Telegram: {e}")

# --- 4. CICLO PRINCIPAL ---

def ciclo():
    global ponteiro_loja
    h_br = (time.gmtime().tm_hour - 3) % 24
    if 8 <= h_br <= 23:
        loja = lojas[ponteiro_loja]
        if loja == "ML": asyncio.run(buscar_ml())
        else: asyncio.run(buscar_amazon())
        ponteiro_loja = (ponteiro_loja + 1) % len(lojas)
    else:
        print(f"😴 Madrugada ({h_br}h).")

schedule.every(8).minutes.do(ciclo)

print("🚀 BOT @PROMODAGOTA INICIADO!")
ciclo() # Posta a primeira imediatamente

while True:
    schedule.run_pending()
    time.sleep(10)
