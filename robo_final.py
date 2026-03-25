import asyncio
import requests
from bs4 import BeautifulSoup
from telegram import Bot
import schedule
import time
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

# --- TRUQUE PARA O RENDER NÃO DESLIGAR O ROBÔ ---
def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    # Cria um servidor simples que apenas diz "OK"
    server = HTTPServer(('0.0.0.0', port), BaseHTTPRequestHandler)
    print(f"✅ Servidor fantasma rodando na porta {port}")
    server.serve_forever()

# Inicia o servidor em uma "linha" separada (thread) para não parar o robô
threading.Thread(target=run_dummy_server, daemon=True).start()
# -----------------------------------------------

# 1. --- CONFIGURAÇÕES ---
TOKEN = '8512528196:AAHCRuMbwSSgILe_WEv98D0c8TWgdatp8o8'
CHAVE_DO_CANAL = '@promodagota'
# URL da página de ofertas do dia
URL_OFERTAS = 'https://www.mercadolivre.com.br/ofertas#nav-header'

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'}

# Memória para não repetir ofertas já postadas nas últimas horas
ofertas_postadas = set()

# 2. --- FUNÇÃO DE GARIMPO ---

async def garimpar_ofertas():
    global ofertas_postadas
    bot = Bot(token=TOKEN)
    
    print(f"\n[{time.strftime('%H:%M:%S')}] 🕵️‍♂️ Iniciando garimpo de ofertas...")
    
    try:
        resposta = requests.get(URL_OFERTAS, headers=HEADERS)
        if resposta.status_code != 200:
            print("❌ Erro ao acessar a página de ofertas.")
            return

        site = BeautifulSoup(resposta.text, 'html.parser')
        
        # O ML organiza as ofertas em blocos. Vamos pegar os cartões de produtos:
        produtos = site.find_all('div', class_='promotion-item__container', limit=5) # Limitamos aos 5 primeiros
        
        for produto in produtos:
            nome_elem = produto.find('p', class_='promotion-item__title')
            preco_elem = produto.find('span', class_='andes-money-amount__fraction')
            link_elem = produto.find('a', class_='promotion-item__link-container')
            
            if nome_elem and preco_elem and link_elem:
                nome = nome_elem.text.strip()
                preco = preco_elem.text.strip()
                link = link_elem['href']
                
                # Gerar um ID único para a oferta (pra não postar o mesmo item toda hora)
                oferta_id = f"{nome}-{preco}"
                
                if oferta_id not in ofertas_postadas:
                    texto = (
                        f"⚡ **OFERTA DO MOMENTO!** ⚡\n\n"
                        f"📦 {nome}\n"
                        f"💰 **R$ {preco},00**\n\n"
                        f"🔗 [CLIQUE AQUI PARA VER]({link})"
                    )
                    
                    print(f"✅ Postando: {nome[:30]}...")
                    await bot.send_message(chat_id=CHAVE_DO_CANAL, text=texto, parse_mode='Markdown')
                    
                    # Salva na memória
                    ofertas_postadas.add(oferta_id)
                    time.sleep(3) # Pausa para o Telegram não travar
                else:
                    print(f"😴 {nome[:30]}... já foi postado.")
                    
    except Exception as e:
        print(f"Erro no garimpo: {e}")

# 3. --- AGENDADOR ---

def tarefa():
    asyncio.run(garimpar_ofertas())

# Verifica novas ofertas a cada 1 hora (para não virar spam)
schedule.every(1).hours.do(tarefa)

print("🚀 ROBÔ GARIMPEIRO ATIVADO! Buscando as 5 melhores ofertas...")
tarefa()

while True:
    schedule.run_pending()
    time.sleep(1)
