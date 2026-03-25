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

# --- 1. SERVIDOR PARA UPTIME ROBOT ---
sys.stdout.reconfigure(line_buffering=True)

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot @promodagota - ML + Amazon Ativos!")
    def log_message(self, format, *args): return

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHandler)
    server.serve_forever()

threading.Thread(target=run_server, daemon=True).start()

# --- 2. CONFIGURAÇÕES PROTEGIDAS ---
TOKEN = os.environ.get('TELEGRAM_TOKEN')
# Mercado Livre
MATT_TOOL = os.environ.get('MATT_TOOL')
MATT_WORD = os.environ.get('MATT_WORD')
# Amazon
AMAZON_TAG = os.environ.get('AMAZON_TAG')

CHAVE_DO_CANAL = '@promodagota'
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'}

ofertas_postadas = []
proxima_loja = "ML" # Controle de rodízio

# --- 3. FUNÇÕES DE GARIMPO ---

async def garimpar_ml():
    global ofertas_postadas
    bot = Bot(token=TOKEN)
    url_ml = 'https://www.mercadolivre.com.br/ofertas#nav-header'
    
    try:
        print("🕵️‍♂️ Garimpando Mercado Livre...")
        res = requests.get(url_ml, headers=HEADERS, timeout=15)
        site = BeautifulSoup(res.text, 'html.parser')
        produtos = site.find_all(['li', 'div'], class_=['promotion-item', 'poly-card', 'promotion-item__container'])
        
        novos = []
        for p in produtos:
            link_e = p.find('a', href=True)
            if not link_e: continue
            link = link_e['href'].split("#")[0]
            if link in ofertas_postadas: continue
            
            nome = (p.find(['p', 'h2', 'h3']) or p.select_one('.poly-component__title')).text.strip()
            c_novo = p.select_one('.andes-money-amount--current') or p.select_one('.poly-price__current')
            c_antigo = p.select_one('.andes-money-amount--previous')
            
            p_novo = c_novo.find('span', class_='andes-money-amount__fraction').text.strip() if c_novo else None
            p_antigo = c_antigo.find('span', class_='andes-money-amount__fraction').text.strip() if c_antigo else None
            img = p.find('img').get('data-src') or p.find('img').get('src') if p.find('img') else None

            if nome and p_novo:
                novos.append({'nome': nome, 'novo': p_novo, 'antigo': p_antigo, 'link': link, 'img': img, 'loja': 'Mercado Livre'})

        if novos:
            item = random.choice(novos[:10])
            link_afiliado = f"{item['link']}{'&' if '?' in item['link'] else '?'}matt_tool={MATT_TOOL}&matt_word={MATT_WORD}"
            await enviar_telegram(item, link_afiliado)
            ofertas_postadas.append(item['link'])
    except Exception as e: print(f"Erro ML: {e}")

async def garimpar_amazon():
    global ofertas_postadas
    bot = Bot(token=TOKEN)
    # URL de Ofertas do Dia da Amazon
    url_amz = 'https://www.amazon.com.br/gp/goldbox'
    
    try:
        print("🕵️‍♂️ Garimpando Amazon Brasil...")
        res = requests.get(url_amz, headers=HEADERS, timeout=15)
        site = BeautifulSoup(res.text, 'html.parser')
        
        # Seleção básica de cards de oferta da Amazon
        produtos = site.select('div[data-testid="grid-desktop-card"]') or site.select('.s-result-item')
        
        novos = []
        for p in produtos:
            link_e = p.find('a', href=True)
            if not link_e: continue
            link = "https://www.amazon.com.br" + link_e['href'].split("?")[0] if link_e['href'].startswith('/') else link_e['href'].split("?")[0]
            if link in ofertas_postadas: continue
            
            nome = p.find('img')['alt'] if p.find('img') and p.find('img').get('alt') else "Produto Amazon"
            # Lógica simplificada de preço Amazon (pode variar, Amazon é complexa no HTML)
            preco_e = p.select_one('.a-price-whole')
            if not preco_e: continue
            
            p_novo = preco_e.text.replace(',', '').replace('.', '').strip()
            img = p.find('img')['src'] if p.find('img') else None

            novos.append({'nome': nome[:80], 'novo': p_novo, 'antigo': None, 'link': link, 'img': img, 'loja': 'Amazon'})

        if novos:
            item = random.choice(novos[:5])
            # Link de Afiliado Amazon
            link_afiliado = f"{item['link']}?tag={AMAZON_TAG}"
            await enviar_telegram(item, link_afiliado)
            ofertas_postadas.append(item['link'])
        else:
            print("Amazon não retornou ofertas nesta rodada.")
    except Exception as e: print(f"Erro Amazon: {e}")

async def enviar_telegram(item, link_final):
    bot = Bot(token=TOKEN)
    preco_html = f"❌ De: <s>R$ {item['antigo']},00</s>\n✅ <b>Por: R$ {item['novo']},00</b>" if item['antigo'] else f"💰 <b>Preço: R$ {item['novo']},00</b>"
    
    texto = (
        f"🔥 <b>OFERTA {item['loja'].upper()}!</b> 🔥\n\n"
        f"📦 {item['nome']}\n\n"
        f"{preco_html}\n\n"
        f"⚡ <i>Garanta o seu na {item['loja']}!</i>"
    )
    
    teclado = InlineKeyboardMarkup([[InlineKeyboardButton(f"🛒 VER NA {item['loja'].upper()}", url=link_final)]])
    
    if item['img']:
        await bot.send_photo(chat_id=CHAVE_DO_CANAL, photo=item['img'], caption=texto, parse_mode='HTML', reply_markup=teclado)
    else:
        await bot.send_message(chat_id=CHAVE_DO_CANAL, text=texto, parse_mode='HTML', reply_markup=teclado)

# --- 4. CONTROLE DE RODÍZIO ---
def tarefa():
    global proxima_loja
    h_utc = time.gmtime().tm_hour
    h_br = (h_utc - 3) % 24
    
    if 8 <= h_br <= 22:
        if proxima_loja == "ML":
            asyncio.run(garimpar_ml())
            proxima_loja = "AMZ"
        else:
            asyncio.run(garimpar_amazon())
            proxima_loja = "ML"
    else:
        print(f"😴 Pausa madrugada ({h_br}h).")

schedule.every(15).minutes.do(tarefa) # Diminuí para 15 min para intercalar mais rápido
print("🚀 BOT DUAL-STORE (ML + AMAZON) ATIVADO!")
tarefa()

while True:
    schedule.run_pending()
    time.sleep(1)
