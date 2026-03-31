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

# --- 1. CONFIGURAÇÕES (PEGANDO DO RENDER) ---
TOKEN = os.environ.get('TELEGRAM_TOKEN')
MATT_TOOL = os.environ.get('MATT_TOOL')
MATT_WORD = os.environ.get('MATT_WORD')
CHAVE_DO_CANAL = '@promodagota'

# --- 2. CATEGORIAS (9 NICHOS) ---
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

ofertas_postadas = []
indice_cat = 0
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'}

# --- 3. MOTOR DE BUSCA E POSTAGEM ---

async def executar_ciclo():
    global indice_cat, ofertas_postadas
    
    # Horário de Brasília (Render usa UTC, então subtraímos 3 horas)
    h_br = (time.gmtime().tm_hour - 3) % 24
    if not (8 <= h_br <= 23):
        print(f"😴 Madrugada ({h_br}h). Bot aguardando amanhecer.")
        return

    cat = CATEGORIAS_ML[indice_cat]
    print(f"🔎 Buscando em: {cat['nome']}")
    
    try:
        res = requests.get(cat['url'], headers=HEADERS, timeout=25)
        site = BeautifulSoup(res.text, 'html.parser')
        produtos = site.find_all(['li', 'div'], class_=['promotion-item', 'poly-card', 'promotion-item__container'])
        
        for p in produtos:
            link_e = p.find('a', href=True)
            if not link_e: continue
            link_base = link_e['href'].split("#")[0]
            
            if link_base in ofertas_postadas: continue
            
            nome_e = p.find(['p', 'h2', 'h3']) or p.select_one('.poly-component__title')
            preco_e = p.select_one('.andes-money-amount--current') or p.select_one('.poly-price__current')
            
            if nome_e and preco_e:
                nome = nome_e.text.strip()
                preco = preco_e.find('span', class_='andes-money-amount__fraction').text.strip()
                antigo_e = p.select_one('.andes-money-amount--previous')
                p_antigo = antigo_e.find('span', class_='andes-money-amount__fraction').text.strip() if antigo_e else None
                img = p.find('img').get('data-src') or p.find('img').get('src') if p.find('img') else None
                
                link_af = f"{link_base}{'&' if '?' in link_base else '?'}matt_tool={MATT_TOOL}&matt_word={MATT_WORD}"
                
                # --- POSTAGEM TELEGRAM ---
                bot = Bot(token=TOKEN)
                p_html = f"❌ De: <s>R$ {p_antigo},00</s>\n✅ <b>Por: R$ {preco},00</b>" if p_antigo else f"💰 <b>Preço: R$ {preco},00</b>"
                texto = f"🔥 <b>ACHADO NO MERCADO LIVRE!</b> 🔥\n\n📦 {nome}\n\n{p_html}\n\n⚡ <i>Corre para garantir!</i>"
                kb = InlineKeyboardMarkup([[InlineKeyboardButton("🛒 COMPRAR AGORA", url=link_af)]])
                
                if img: await bot.send_photo(chat_id=CHAVE_DO_CANAL, photo=img, caption=texto, parse_mode='HTML', reply_markup=kb)
                else: await bot.send_message(chat_id=CHAVE_DO_CANAL, text=texto, parse_mode='HTML', reply_markup=kb)
                
                print(f"✅ [TG] Postado: {nome[:30]}...")
                ofertas_postadas.append(link_base)
                indice_cat = (indice_cat + 1) % len(CATEGORIAS_ML)
                
                # Limpa memória
                if len(ofertas_postadas) > 200: ofertas_postadas.pop(0)
                break
    except Exception as e:
        print(f"❌ Erro na busca: {e}")

# --- 4. SERVIDOR PARA MANTER VIVO NO RENDER ---

class SimpleS(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot @promodagota Online")
    def log_message(self, format, *args): return

def run_server():
    port = int(os.environ.get("PORT", 10000))
    HTTPServer(('0.0.0.0', port), SimpleS).serve_forever()

threading.Thread(target=run_server, daemon=True).start()

# --- 5. AGENDADOR ---

def rodar():
    asyncio.run(executar_ciclo())

# Defina aqui o tempo: 10 ou 20 minutos
schedule.every(20).minutes.do(rodar)

print("🚀 BOT TURBO TELEGRAM INICIADO!")
rodar() # Força a primeira postagem na hora que liga

while True:
    schedule.run_pending()
    time.sleep(1)
