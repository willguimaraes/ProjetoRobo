import sys
import os
import threading
import asyncio
import requests
from bs4 import BeautifulSoup
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
import schedule
import time
from http.server import HTTPServer, BaseHTTPRequestHandler

# --- 1. CONFIGURAÇÃO DE SERVIDOR ---
sys.stdout.reconfigure(line_buffering=True)

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot @promodagota - Afiliado Ativo!")
    def log_message(self, format, *args): return

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHandler)
    server.serve_forever()

threading.Thread(target=run_server, daemon=True).start()

# --- 2. CONFIGURAÇÕES (TOKEN E CANAL) ---
TOKEN = '8512528196:AAHCRuMbwSSgILe_WEv98D0c8TWgdatp8o8'
CHAVE_DO_CANAL = '@promodagota'
URL_OFERTAS = 'https://www.mercadolivre.com.br/ofertas#nav-header'
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'}

# --- SEUS DADOS DE AFILIADO ---
MATT_TOOL = "11823943"
MATT_WORD = "guwi2000508"

ofertas_postadas = set()

# --- 3. FUNÇÃO DE GARIMPO E POSTAGEM ---
async def garimpar_ofertas():
    global ofertas_postadas
    bot = Bot(token=TOKEN)
    
    try:
        resposta = requests.get(URL_OFERTAS, headers=HEADERS, timeout=15)
        site = BeautifulSoup(resposta.text, 'html.parser')
        produtos = site.find_all('li', class_='promotion-item') or site.find_all('div', class_='poly-card')

        postados = 0
        for produto in produtos:
            if postados >= 1: break # Posta 1 por vez a cada 20 min

            nome_e = produto.find('p') or produto.find('h2') or produto.find('a', class_='poly-component__title')
            preco_e = produto.find('span', class_='andes-money-amount__fraction')
            link_e = produto.find('a', href=True)
            img_e = produto.find('img')

            if nome_e and preco_e and link_e:
                nome = nome_e.text.strip()
                preco = preco_e.text.strip()
                link_original = link_e['href']
                if link_original.startswith('/'): link_original = "https://www.mercadolivre.com.br" + link_original
                
                # --- MONTAGEM DO LINK DE AFILIADO ---
                divisor = "&" if "?" in link_original else "?"
                link_afiliado = f"{link_original}{divisor}matt_tool={MATT_TOOL}&matt_word={MATT_WORD}"
                
                img_url = img_e.get('data-src') or img_e.get('src') if img_e else None
                oferta_id = f"{nome}-{preco}"
                
                if oferta_id not in ofertas_postadas:
                    texto = (
                        f"🔥 **OFERTA DO MOMENTO!** 🔥\n\n"
                        f"📦 {nome}\n"
                        f"💰 **R$ {preco},00**\n\n"
                        f"⚡ *Aproveite antes que o estoque acabe!*"
                    )
                    
                    # Botão com seu link de afiliado rastreado
                    teclado = InlineKeyboardMarkup([
                        [InlineKeyboardButton("🛒 IR PARA A LOJA (COM DESCONTO)", url=link_afiliado)]
                    ])
                    
                    print(f"📤 Postando oferta com afiliado: {nome[:30]}...")
                    
                    try:
                        if img_url:
                            await bot.send_photo(chat_id=CHAVE_DO_CANAL, photo=img_url, caption=texto, parse_mode='Markdown', reply_markup=teclado)
                        else:
                            await bot.send_message(chat_id=CHAVE_DO_CANAL, text=texto, parse_mode='Markdown', reply_markup=teclado)
                        
                        ofertas_postadas.add(oferta_id)
                        postados += 1
                    except Exception as e:
                        print(f"❌ Erro envio: {e}")
                
    except Exception as e:
        print(f"💥 Erro garimpo: {e}")

# --- 4. CONTROLE DE HORÁRIO ---
def tarefa():
    hora = time.localtime().tm_hour
    # Posta entre 08h e 22h (Horário do Servidor)
    if 8 <= hora <= 22:
        asyncio.run(garimpar_ofertas())
    else:
        print(f"😴 Madrugada ({hora}h). Em espera.")

# Repete a cada 20 minutos
schedule.every(20).minutes.do(tarefa)

print("🚀 ROBÔ COM AFILIADO ATIVADO! BOAS VENDAS!")
tarefa()

while True:
    schedule.run_pending()
    time.sleep(1)
