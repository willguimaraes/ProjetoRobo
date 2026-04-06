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
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler

# --- 1. CONFIGURAÇÕES ---
TOKEN = os.environ.get('TELEGRAM_TOKEN')
MATT_TOOL = os.environ.get('MATT_TOOL')
MATT_WORD = os.environ.get('MATT_WORD')
CHAVE_DO_CANAL = '@promodagota'

CATEGORIAS_ML = [
    {"nome": "TECNOLOGIA", "url": "https://www.mercadolivre.com.br/ofertas#c_id=MLB1051&category=MLB1051"},
    {"nome": "CASA & ELETROS", "url": "https://www.mercadolivre.com.br/ofertas#c_id=MLB1574&category=MLB1574"},
    {"nome": "GAMES", "url": "https://www.mercadolivre.com.br/ofertas#c_id=MLB1144&category=MLB1144"},
    {"nome": "MODA", "url": "https://www.mercadolivre.com.br/ofertas#c_id=MLB1430&category=MLB1430"},
    {"nome": "BELEZA", "url": "https://www.mercadolivre.com.br/ofertas#c_id=MLB1246&category=MLB1246"},
    {"nome": "SUPERMERCADO", "url": "https://www.mercadolivre.com.br/ofertas#c_id=MLB1403&category=MLB1403"},
    {"nome": "AUTOMOTIVO", "url": "https://www.mercadolivre.com.br/ofertas#c_id=MLB1743&category=MLB1743"},
    {"nome": "BRINQUEDOS", "url": "https://www.mercadolivre.com.br/ofertas#c_id=MLB1132&category=MLB1132"},
    {"nome": "PET SHOP", "url": "https://www.mercadolivre.com.br/ofertas#c_id=MLB1071&category=MLB1071"}
]

historico_quarentena = {}
indice_cat = 0
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'}

# --- 2. FUNÇÕES DE APOIO ---

def pode_postar(link):
    global historico_quarentena
    agora = datetime.now()
    if link in historico_quarentena:
        horario_postado = historico_quarentena[link]
        if agora < horario_postado + timedelta(hours=6):
            return False
    return True

async def enviar_telegram(item, link_final):
    bot = Bot(token=TOKEN)
    p_html = f"❌ De: <s>R$ {item['antigo']},00</s>\n✅ <b>Por: R$ {item['novo']},00</b>" if item['antigo'] else f"💰 <b>Preço: R$ {item['novo']},00</b>"
    texto = (f"🔥 <b>ACHADO NO MERCADO LIVRE!</b> 🔥\n\n📦 {item['nome']}\n\n{p_html}\n\n⚡ <i>Corre para garantir!</i>")
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🛒 COMPRAR AGORA", url=link_final)]])
    try:
        if item['img']:
            await bot.send_photo(chat_id=CHAVE_DO_CANAL, photo=item['img'], caption=texto, parse_mode='HTML', reply_markup=kb)
        else:
            await bot.send_message(chat_id=CHAVE_DO_CANAL, text=texto, parse_mode='HTML', reply_markup=kb)
        print(f"✅ [TG] Postado!")
    except Exception as e:
        print(f"❌ Erro Telegram: {e}")

# --- 3. MOTOR DE BUSCA ---

async def executar_ciclo():
    global indice_cat, historico_quarentena
    
    # LINHA CORRIGIDA AQUI:
    h_br = (time.gmtime().tm_hour - 3) % 24
    
    if not (8 <= h_br <= 23):
        print(f"😴 Madrugada ({h_br}h).")
        return

    cat = CATEGORIAS_ML[indice_cat]
    print(f"🔎 Categoria: {cat['nome']}")
    
    try:
        res = requests.get(cat['url'], headers=HEADERS, timeout=25)
        site = BeautifulSoup(res.text, 'html.parser')
        produtos = site.find_all(['li', 'div'], class_=['promotion-item', 'poly-card', 'promotion-item__container'])[:30]
        
        for p in produtos:
            link_e = p.find('a', href=True)
            if not link_e: continue
            link_base = link_e['href'].split("#")[0]
            
            if not pode_postar(link_base): continue 
            
            nome_e = p.find(['p', 'h2', 'h3']) or p.select_one('.poly-component__title')
            preco_e = p.select_one('.andes-money-amount--current') or p.select_one('.poly-price__current')
            
            if nome_e and preco_e:
                nome = nome_e.text.strip()
                preco = preco_e.find('span', class_='andes-money-amount__fraction').text.strip()
                antigo_e = p.select_one('.andes-money-amount--previous')
                p_antigo = antigo_e.find('span', class_='andes-money-amount__fraction').text.strip() if antigo_e else None
                img = p.find('img').get('data-src') or p.find('img').get('src') if p.find('img') else None
                link_af = f"{link_base}{'&' if '?' in link_base else '?'}matt_tool={MATT_TOOL}&matt_word={MATT_WORD}"
                
                await enviar_telegram({'nome': nome, 'novo': preco, 'antigo': p_antigo, 'img': img}, link_af)
                
                historico_quarentena[link_base] = datetime.now()
                indice_cat = (indice_cat + 1) % len(CATEGORIAS_ML)
                
                agora = datetime.now()
                historico_quarentena = {l: d for l, d in historico_quarentena.items() if agora < d + timedelta(hours=24)}
                break
    except Exception as e:
        print(f"❌ Erro no ciclo: {e}")

# --- 4. SERVIDOR HTTP (ANTI-501) ---

class SimpleS(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot @promodagota Online")
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()
    def log_message(self, format, *args): return

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleS)
    server.serve_forever()

threading.Thread(target=run_server, daemon=True).start()

# --- 5. AGENDADOR ---

def rodar():
    asyncio.run(executar_ciclo())

schedule.every(20).minutes.do(rodar)

print("🚀 BOT TURBO INICIADO!")
rodar()

while True:
    schedule.run_pending()
    time.sleep(1)
