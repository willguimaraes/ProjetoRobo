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
        self.wfile.write(b"Bot @promodagota - Mega Diversificado Ativo")
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

# --- 3. A SUPER LISTA DE CATEGORIAS (MÁXIMA DIVERSIDADE) ---
CATEGORIAS_ML = [
    {"nome": "TECNOLOGIA & CELULARES", "url": "https://www.mercadolivre.com.br/ofertas#c_id=MLB1051&category=MLB1051"},
    {"nome": "CASA & ELETROS", "url": "https://www.mercadolivre.com.br/ofertas#c_id=MLB1574&category=MLB1574"},
    {"nome": "GAMES & CONSOLES", "url": "https://www.mercadolivre.com.br/ofertas#c_id=MLB1144&category=MLB1144"},
    {"nome": "MODA & TÊNIS", "url": "https://www.mercadolivre.com.br/ofertas#c_id=MLB1430&category=MLB1430"},
    {"nome": "BELEZA & PERFUMARIA", "url": "https://www.mercadolivre.com.br/ofertas#c_id=MLB1246&category=MLB1246"},
    {"nome": "SUPERMERCADO & LIMPEZA", "url": "https://www.mercadolivre.com.br/ofertas#c_id=MLB1403&category=MLB1403"},
    {"nome": "AUTOMOTIVO & PNEUS", "url": "https://www.mercadolivre.com.br/ofertas#c_id=MLB1743&category=MLB1743"},
    {"nome": "BRINQUEDOS & BEBÊS", "url": "https://www.mercadolivre.com.br/ofertas#c_id=MLB1132&category=MLB1132"},
    {"nome": "MUNDO PET", "url": "https://www.mercadolivre.com.br/ofertas#c_id=MLB1071&category=MLB1071"}
]

ofertas_postadas = []
indice_cat = 0
alternador_loja = "ML" # ML ou AMZ

# --- 4. MOTOR DE BUSCA ---

async def buscar_ml_especifico():
    global ofertas_postadas, indice_cat
    cat = CATEGORIAS_ML[indice_cat]
    print(f"🔎 [ML] Explorando: {cat['nome']}")
    
    try:
        res = requests.get(cat['url'], headers=HEADERS, timeout=25)
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
            item = random.choice(candidatos[:35]) # Sorteio entre os 35 melhores
            link_af = f"{item['link']}{'&' if '?' in item['link'] else '?'}matt_tool={MATT_TOOL}&matt_word={MATT_WORD}"
            await enviar_telegram(item, link_af)
            ofertas_postadas.append(item['link'])
            indice_cat = (indice_cat + 1) % len(CATEGORIAS_ML)
            return True
    except Exception as e: print(f"❌ Erro ML {cat['nome']}: {e}")
    return False

async def buscar_amazon():
    print("🔎 [AMZ] Buscando achados...")
    try:
        # Plano B imediato: se a Amazon não responder em 15s, vai pro ML
        res = requests.get('https://www.amazon.com.br/gp/goldbox', headers=HEADERS, timeout=15)
        site = BeautifulSoup(res.text, 'html.parser')
        produtos = site.select('div[data-testid="grid-desktop-card"]')
        
        if not produtos: return await buscar_ml_especifico()
        
        # Se achou algo na Amazon, tenta postar... caso contrário:
        return await buscar_ml_especifico()
    except:
        return await buscar_ml_especifico()

async def enviar_telegram(item, link):
    bot = Bot(token=TOKEN)
    pre = f"❌ De: <s>R$ {item['antigo']},00</s>\n✅ <b>Por: R$ {item['novo']},00</b>" if item['antigo'] else f"💰 <b>Preço: R$ {item['novo']},00</b>"
    texto = f"🔥 <b>ACHADO NO {item['loja'].upper()}!</b> 🔥\n\n📦 {item['nome']}\n\n{pre}\n\n⚡ <i>Corre pra garantir!</i>"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(f"🛒 COMPRAR NA {item['loja'].upper()}", url=link)]])
    try:
        if item['img']: await bot.send_photo(chat_id=CHAVE_DO_CANAL, photo=item['img'], caption=texto, parse_mode='HTML', reply_markup=kb)
        else: await bot.send_message(chat_id=CHAVE_DO_CANAL, text=texto, parse_mode='HTML', reply_markup=kb)
        print(f"✅ POSTADO: {item['loja']} - {item['nome'][:30]}...")
    except Exception as e: print(f"Erro Telegram: {e}")

# --- 5. CICLO DE RODÍZIO ---

def ciclo_mestre():
    global alternador_loja
    h_br = (time.gmtime().tm_hour - 3) % 24
    if 8 <= h_br <= 23:
        if alternador_loja == "AMZ":
            asyncio.run(buscar_amazon())
            alternador_loja = "ML"
        else:
            asyncio.run(buscar_ml_especifico())
            alternador_loja = "AMZ"
    else: print("😴 Zzz... Horário de descanso.")

# Postagem a cada 10 minutos para não cansar o público, mas manter o canal ativo
schedule.every(10).minutes.do(ciclo_mestre)

print("🚀 BOT @PROMODAGOTA MEGA-DIVERSIFICADO INICIADO!")
ciclo_mestre()

while True:
    schedule.run_pending()
    time.sleep(1)
