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

# --- 1. SERVIDOR ---
sys.stdout.reconfigure(line_buffering=True)

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot @promodagota - Rodando!")
    def log_message(self, format, *args): return

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHandler)
    server.serve_forever()

threading.Thread(target=run_server, daemon=True).start()

# --- 2. CONFIGURAÇÕES ---
TOKEN = '8512528196:AAHCRuMbwSSgILe_WEv98D0c8TWgdatp8o8'
CHAVE_DO_CANAL = '@promodagota'
URL_OFERTAS = 'https://www.mercadolivre.com.br/ofertas#nav-header'
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'}

MATT_TOOL = "11823943"
MATT_WORD = "guwi2000508"

# LISTA GLOBAL PARA NÃO PERDER A MEMÓRIA NESTA SESSÃO
ofertas_postadas = []

async def garimpar_ofertas():
    global ofertas_postadas
    bot = Bot(token=TOKEN)
    
    print(f"\n[{time.strftime('%H:%M:%S')}] 🕵️‍♂️ Iniciando busca profunda...")
    
    try:
        resposta = requests.get(URL_OFERTAS, headers=HEADERS, timeout=15)
        site = BeautifulSoup(resposta.text, 'html.parser')
        
        # Pega todos os cards de produtos possíveis
        produtos_brutos = site.find_all(['li', 'div'], class_=['promotion-item', 'poly-card', 'promotion-item__container'])

        novidades = []
        for p in produtos_brutos:
            # Pega o link primeiro, que é o ID único
            link_e = p.find('a', href=True)
            if not link_e: continue
            
            link_limpo = link_e['href'].split("#")[0] # Remove lixo do link
            
            # Se o link já foi postado, pula!
            if link_limpo in ofertas_postadas:
                continue

            # Tenta achar o nome
            nome_e = p.find(['p', 'h2', 'h3']) or p.select_one('.poly-component__title')
            # Tenta achar o preço (vários seletores para não falhar)
            preco_e = p.find('span', class_='andes-money-amount__fraction') or \
                      p.select_one('.poly-price__current .andes-money-amount__fraction')

            if nome_e and preco_e:
                novidades.append({
                    'nome': nome_e.text.strip(),
                    'preco': preco_e.text.strip(),
                    'link': link_limpo,
                    'img_e': p.find('img')
                })

        if not novidades:
            print("😴 Tudo o que vi agora já foi postado. Limpando memória para renovar...")
            # Se ele postou tudo o que tinha na página, limpamos 5 para ele ter o que postar
            if len(ofertas_postadas) > 20: ofertas_postadas = ofertas_postadas[-5:]
            return

        # Escolhe um aleatório das novidades
        escolhido = random.choice(novidades[:15])

        # Prepara o post
        link_final = escolhido['link']
        if link_final.startswith('/'): link_final = "https://www.mercadolivre.com.br" + link_final
        
        # Injeta seu Afiliado
        divisor = "&" if "?" in link_final else "?"
        link_afiliado = f"{link_final}{divisor}matt_tool={MATT_TOOL}&matt_word={MATT_WORD}"
        
        img_url = escolhido['img_e'].get('data-src') or escolhido['img_e'].get('src') if escolhido['img_e'] else None
        
        texto = (
            f"🔥 **OFERTA DO MOMENTO!** 🔥\n\n"
            f"📦 {escolhido['nome']}\n"
            f"💰 **R$ {escolhido['preco']},00**\n\n"
            f"⚡ *Corre porque acaba rápido!*"
        )
        
        teclado = InlineKeyboardMarkup([[InlineKeyboardButton("🛒 IR PARA A LOJA", url=link_afiliado)]])
        
        print(f"📤 Postando NOVIDADE: {escolhido['nome'][:30]}...")
        
        if img_url:
            await bot.send_photo(chat_id=CHAVE_DO_CANAL, photo=img_url, caption=texto, parse_mode='Markdown', reply_markup=teclado)
        else:
            await bot.send_message(chat_id=CHAVE_DO_CANAL, text=texto, parse_mode='Markdown', reply_markup=teclado)
        
        # Adiciona o LINK na memória (o link nunca mente!)
        ofertas_postadas.append(escolhido['link'])

    except Exception as e:
        print(f"💥 Erro: {e}")

def tarefa():
    hora = time.localtime().tm_hour
    if 8 <= hora <= 22:
        asyncio.run(garimpar_ofertas())

schedule.every(20).minutes.do(tarefa)

print("🚀 ROBÔ ANTI-REPETIÇÃO ATIVADO!")
tarefa()

while True:
    schedule.run_pending()
    time.sleep(1)
