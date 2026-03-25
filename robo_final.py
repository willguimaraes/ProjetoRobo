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

# --- 1. SERVIDOR ROBUSTO (PARA O RENDER NÃO DORMIR) ---
sys.stdout.reconfigure(line_buffering=True)

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b"Bot Online e Trabalhando!") # Resposta para o UptimeRobot
    def log_message(self, format, *args): return # Limpa o log de acessos inúteis

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHandler)
    print(f"📡 Servidor de monitoramento rodando na porta {port}")
    server.serve_forever()

# Inicia o servidor em uma thread separada imediatamente
t = threading.Thread(target=run_server, daemon=True)
t.start()

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

# --- 3. FUNÇÕES DE BUSCA ---

async def buscar_ml():
    global ofertas_postadas
    print("🔎 Garimpando Mercado Livre...")
    url = 'https://www.mercadolivre.com.br/ofertas#nav-header'
    try:
        res = requests.get(url, headers=HEADERS, timeout=20)
        site = BeautifulSoup(res.text, 'html.parser')
        produtos = site.find_all(['li', 'div'], class_=['promotion-item', 'poly-card', 'promotion-item__container'])
        
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
                link_afiliado = f"{link}{'&' if '?' in link else '?'}matt_tool={MATT_TOOL}&matt_word={MATT_WORD}"
                await enviar_telegram(nome, p_novo, p_antigo, link_afiliado, img, "Mercado Livre")
                ofertas_postadas.append(link)
                return True
    except Exception as e: print(f"Erro ML: {e}")
    return False

async def buscar_amazon():
    global ofertas_postadas
    print("🔎 Garimpando Amazon...")
    url = 'https://www.amazon.com.br/gp/goldbox'
    try:
        res = requests.get(url, headers=HEADERS, timeout=20)
        site = BeautifulSoup(res.text, 'html.parser')
        produtos = site.select('div[data-testid="grid-desktop-card"]') or site.select('.s-result-item')
        
        for p in produtos:
            link_e = p.find('a', href=True)
            if not link_e: continue
            link = "https://www.amazon.com.br" + link_e['href'].split("?")[0] if link_e['href'].startswith('/') else link_e['href'].split("?")[0]
            if link in ofertas_postadas: continue
            
            nome = p.find('img')['alt'] if p.find('img') and p.find('img').get('alt') else "Produto em Oferta"
            preco_e = p.select_one('.a-price-whole')
            if not preco_e: continue
            
            p_novo = preco_e.text.replace(',', '').replace('.', '').strip()
            img = p.find('img')['src'] if p.find('img') else None

            link_afiliado = f"{link}?tag={AMAZON_TAG}"
            await enviar_telegram(nome[:80], p_novo, None, link_afiliado, img, "Amazon")
            ofertas_postadas.append(link)
            return True
    except Exception as e: print(f"Erro Amazon: {e}")
    return False

async def enviar_telegram(nome, novo, antigo, link, img, loja):
    bot = Bot(token=TOKEN)
    preco_html = f"❌ De: <s>R$ {antigo},00</s>\n✅ <b>Por: R$ {novo},00</b>" if antigo else f"💰 <b>Preço: R$ {novo},00</b>"
    texto = f"🔥 <b>OFERTA {loja.upper()}!</b> 🔥\n\n📦 {nome}\n\n{preco_html}\n\n⚡ <i>Garanta o seu na {loja}!</i>"
    teclado = InlineKeyboardMarkup([[InlineKeyboardButton(f"🛒 VER NA {loja.upper()}", url=link)]])
    
    if img: await bot.send_photo(chat_id=CHAVE_DO_CANAL, photo=img, caption=texto, parse_mode='HTML', reply_markup=teclado)
    else: await bot.send_message(chat_id=CHAVE_DO_CANAL, text=texto, parse_mode='HTML', reply_markup=teclado)
    print(f"✅ Postado: {loja}")

# --- 4. EXECUTOR PRINCIPAL ---

def loop_principal():
    global ponteiro_loja
    h_br = (time.gmtime().tm_hour - 3) % 24
    
    if 8 <= h_br <= 22:
        loja_atual = lojas[ponteiro_loja]
        if loja_atual == "ML":
            sucesso = asyncio.run(buscar_ml())
        else:
            sucesso = asyncio.run(buscar_amazon())
        
        # Alterna para a próxima loja independente de sucesso
        ponteiro_loja = (ponteiro_loja + 1) % len(lojas)
    else:
        print(f"😴 Madrugada ({h_br}h). Aguardando...")

# Agendamento
schedule.every(20).minutes.do(loop_principal)

print("🚀 BOT @PROMODAGOTA INICIADO!")
loop_principal() # Roda uma vez ao ligar

while True:
    schedule.run_pending()
    time.sleep(30) # Aumentei o sleep para não sobrecarregar o processador
