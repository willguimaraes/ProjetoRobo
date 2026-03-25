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

# --- 1. SERVIDOR DE MONITORAMENTO (SAÚDE DO BOT) ---
sys.stdout.reconfigure(line_buffering=True)

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot @promodagota - Operacional")
    def log_message(self, format, *args): return

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHandler)
    print(f"📡 Servidor de Vigilância na porta {port}")
    server.serve_forever()

threading.Thread(target=run_server, daemon=True).start()

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

# --- 3. MOTOR DE BUSCA ---

async def buscar_ml():
    global ofertas_postadas
    print("🔎 [ML] Iniciando varredura...")
    try:
        res = requests.get('https://www.mercadolivre.com.br/ofertas#nav-header', headers=HEADERS, timeout=20)
        site = BeautifulSoup(res.text, 'html.parser')
        produtos = site.find_all(['li', 'div'], class_=['promotion-item', 'poly-card', 'promotion-item__container'])
        
        candidatos = []
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
                candidatos.append({'nome': nome, 'novo': p_novo, 'antigo': p_antigo, 'link': link, 'img': img})

        if candidatos:
            item = random.choice(candidatos[:30]) # Sorteio amplo
            link_af = f"{item['link']}{'&' if '?' in item['link'] else '?'}matt_tool={MATT_TOOL}&matt_word={MATT_WORD}"
            await enviar_telegram(item['nome'], item['novo'], item['antigo'], link_af, item['img'], "Mercado Livre")
            ofertas_postadas.append(item['link'])
            return True
    except Exception as e: print(f"❌ Erro ML: {e}")
    return False

async def buscar_amazon():
    global ofertas_postadas
    print("🔎 [AMZ] Iniciando varredura...")
    try:
        res = requests.get('https://www.amazon.com.br/gp/goldbox', headers=HEADERS, timeout=20)
        site = BeautifulSoup(res.text, 'html.parser')
        produtos = site.select('div[data-testid="grid-desktop-card"]') or site.select('.s-result-item')
        
        candidatos = []
        for p in produtos:
            link_e = p.find('a', href=True)
            if not link_e: continue
            link = "https://www.amazon.com.br" + link_e['href'].split("?")[0] if link_e['href'].startswith('/') else link_e['href'].split("?")[0]
            if link in ofertas_postadas: continue
            
            nome = p.find('img')['alt'] if p.find('img') and p.find('img').get('alt') else "Oferta Amazon"
            preco_e = p.select_one('.a-price-whole')
            if not preco_e: continue
            
            p_novo = preco_e.text.replace(',', '').replace('.', '').strip()
            img = p.find('img')['src'] if p.find('img') else None

            if nome and p_novo:
                candidatos.append({'nome': nome[:80], 'novo': p_novo, 'link': link, 'img': img})

        if candidatos:
            item = random.choice(candidatos[:15])
            link_af = f"{item['link']}?tag={AMAZON_TAG}"
            await enviar_telegram(item['nome'], item['novo'], None, link_af, item['img'], "Amazon")
            ofertas_postadas.append(item['link'])
            return True
    except Exception as e: print(f"❌ Erro Amazon: {e}")
    return False

async def enviar_telegram(nome, novo, antigo, link, img, loja):
    bot = Bot(token=TOKEN)
    preco_html = f"❌ De: <s>R$ {antigo},00</s>\n✅ <b>Por: R$ {novo},00</b>" if antigo else f"💰 <b>Preço: R$ {novo},00</b>"
    texto = f"🔥 <b>OFERTA {loja.upper()}!</b> 🔥\n\n📦 {nome}\n\n{preco_html}\n\n⚡ <i>Aproveite na {loja}!</i>"
    teclado = InlineKeyboardMarkup([[InlineKeyboardButton(f"🛒 VER NA {loja.upper()}", url=link)]])
    await bot.send_photo(chat_id=CHAVE_DO_CANAL, photo=img, caption=texto, parse_mode='HTML', reply_markup=teclado) if img else await bot.send_message(chat_id=CHAVE_DO_CANAL, text=texto, parse_mode='HTML', reply_markup=teclado)
    print(f"✅ POSTADO COM SUCESSO: {loja}")

# --- 4. CICLO DE EXECUÇÃO ---

def loop_principal():
    global ponteiro_loja
    h_br = (time.gmtime().tm_hour - 3) % 24
    print(f"⏰ {h_br:02d}:00 - Verificando agendamento...")
    
    if 8 <= h_br <= 23:
        loja_atual = lojas[ponteiro_loja]
        if loja_atual == "ML": asyncio.run(buscar_ml())
        else: asyncio.run(buscar_amazon())
        ponteiro_loja = (ponteiro_loja + 1) % len(lojas)
    else:
        print("😴 Horário de repouso no Brasil.")

# Agendamento a cada 10 minutos
schedule.every(10).minutes.do(loop_principal)

print("🚀 O ROBÔ ACORDOU! (Postagem inicial em instantes...)")
loop_principal() # POSTA IMEDIATAMENTE AO LIGAR

while True:
    schedule.run_pending()
    # Log de sobrevivência a cada 60 segundos
    if time.localtime().tm_sec == 0:
        print("🕒 Sistema ativo... aguardando próximo ciclo.")
    time.sleep(1)
