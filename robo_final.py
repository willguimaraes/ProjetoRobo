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
        self.wfile.write(b"Bot @promodagota - Efeito Riscado Ativo!")
    def log_message(self, format, *args): return

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHandler)
    server.serve_forever()

threading.Thread(target=run_server, daemon=True).start()

# --- 2. CONFIGURAÇÕES PROTEGIDAS ---
TOKEN = os.environ.get('TELEGRAM_TOKEN')
MATT_TOOL = os.environ.get('MATT_TOOL')
MATT_WORD = os.environ.get('MATT_WORD')
CHAVE_DO_CANAL = '@promodagota'
URL_OFERTAS = 'https://www.mercadolivre.com.br/ofertas#nav-header'
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'}

ofertas_postadas = []

# --- 3. FUNÇÃO DE GARIMPO (LÓGICA HTML) ---
async def garimpar_ofertas():
    global ofertas_postadas
    if not TOKEN: return
    bot = Bot(token=TOKEN)
    
    hora_utc = time.gmtime().tm_hour
    hora_brasil = (hora_utc - 3) % 24
    print(f"\n[{hora_brasil:02d}:00 BRT] 🕵️‍♂️ Garimpando descontos reais...")
    
    try:
        resposta = requests.get(URL_OFERTAS, headers=HEADERS, timeout=15)
        site = BeautifulSoup(resposta.text, 'html.parser')
        produtos_brutos = site.find_all(['li', 'div'], class_=['promotion-item', 'poly-card', 'promotion-item__container'])

        novidades = []
        for p in produtos_brutos:
            link_e = p.find('a', href=True)
            if not link_e: continue
            
            link_limpo = link_e['href'].split("#")[0]
            if link_limpo in ofertas_postadas: continue

            nome_e = p.find(['p', 'h2', 'h3']) or p.select_one('.poly-component__title')
            
            container_novo = p.select_one('.andes-money-amount--current') or p.select_one('.poly-price__current')
            container_antigo = p.select_one('.andes-money-amount--previous')
            
            p_novo = container_novo.find('span', class_='andes-money-amount__fraction').text.strip() if container_novo else None
            p_antigo = container_antigo.find('span', class_='andes-money-amount__fraction').text.strip() if container_antigo else None

            if nome_e and p_novo:
                novidades.append({
                    'nome': nome_e.text.strip(),
                    'preco_novo': p_novo,
                    'preco_antigo': p_antigo,
                    'link': link_limpo,
                    'img_e': p.find('img')
                })

        if not novidades:
            if len(ofertas_postadas) > 50: ofertas_postadas = ofertas_postadas[-15:]
            return

        escolhido = random.choice(novidades[:15])
        link_final = escolhido['link']
        if link_final.startswith('/'): link_final = "https://www.mercadolivre.com.br" + link_final
        
        link_afiliado = f"{link_final}{'&' if '?' in link_final else '?'}matt_tool={MATT_TOOL}&matt_word={MATT_WORD}"
        img_url = escolhido['img_e'].get('data-src') or escolhido['img_e'].get('src') if escolhido['img_e'] else None
        
        # --- MONTAGEM DO TEXTO EM HTML ---
        if escolhido['preco_antigo']:
            # <s> faz o efeito riscado no HTML do Telegram
            preco_texto = f"❌ De: <s>R$ {escolhido['preco_antigo']},00</s>\n✅ <b>Por: R$ {escolhido['preco_novo']},00</b>"
        else:
            preco_texto = f"💰 <b>Preço: R$ {escolhido['preco_novo']},00</b>"

        texto = (
            f"🔥 <b>OFERTA DO MOMENTO!</b> 🔥\n\n"
            f"📦 {escolhido['nome']}\n\n"
            f"{preco_texto}\n\n"
            f"⚡ <i>Aproveite antes que o preço suba!</i>"
        )
        
        teclado = InlineKeyboardMarkup([[InlineKeyboardButton("🛒 IR PARA A LOJA", url=link_afiliado)]])
        
        # IMPORTANTE: parse_mode='HTML' agora
        if img_url:
            await bot.send_photo(chat_id=CHAVE_DO_CANAL, photo=img_url, caption=texto, parse_mode='HTML', reply_markup=teclado)
        else:
            await bot.send_message(chat_id=CHAVE_DO_CANAL, text=texto, parse_mode='HTML', reply_markup=teclado)
        
        ofertas_postadas.append(escolhido['link'])

    except Exception as e:
        print(f"💥 Erro: {e}")

def tarefa():
    hora_utc = time.gmtime().tm_hour
    hora_brasil = (hora_utc - 3) % 24
    if 8 <= hora_brasil <= 22:
        asyncio.run(garimpar_ofertas())

schedule.every(20).minutes.do(tarefa)
print("🚀 ROBÔ COM RISCADO HTML ATIVADO!")
tarefa()
while True:
    schedule.run_pending()
    time.sleep(1)
