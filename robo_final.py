import sys
import os
import threading
import asyncio
import requests
from bs4 import BeautifulSoup
from telegram import Bot
import schedule
import time
from http.server import HTTPServer, BaseHTTPRequestHandler

# --- 1. CONFIGURAÇÃO DE LOG E SERVIDOR ---
sys.stdout.reconfigure(line_buffering=True)

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot Online e Operante!")
    def log_message(self, format, *args): return

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHandler)
    print(f"✅ [SISTEMA] Servidor ativo na porta {port}", flush=True)
    server.serve_forever()

threading.Thread(target=run_server, daemon=True).start()

# --- 2. CONFIGURAÇÕES DO BOT ---
TOKEN = '8512528196:AAHCRuMbwSSgILe_WEv98D0c8TWgdatp8o8'
CHAVE_DO_CANAL = '@promodagota'
URL_OFERTAS = 'https://www.mercadolivre.com.br/ofertas#nav-header'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
}

ofertas_postadas = set()

# --- 3. FUNÇÃO PRINCIPAL DE GARIMPO ---
async def garimpar_ofertas():
    global ofertas_postadas
    bot = Bot(token=TOKEN)
    
    print(f"\n[{time.strftime('%H:%M:%S')}] 🕵️‍♂️ Iniciando busca...")
    
    try:
        resposta = requests.get(URL_OFERTAS, headers=HEADERS, timeout=15)
        site = BeautifulSoup(resposta.text, 'html.parser')
        
        # Seletores de produtos
        produtos = site.find_all('li', class_='promotion-item') or \
                   site.find_all('div', class_='poly-card')

        print(f"🔎 Encontrei {len(produtos)} produtos. Filtrando...")

        contagem = 0
        for produto in produtos:
            if contagem >= 3: 
                break 

            nome_elem = produto.find('p') or produto.find('h2') or produto.find('a', class_='poly-component__title')
            preco_elem = produto.find('span', class_='andes-money-amount__fraction')
            link_elem = produto.find('a', href=True)
            img_elem = produto.find('img')

            if nome_elem and preco_elem and link_elem:
                nome = nome_elem.text.strip()
                preco = preco_elem.text.strip()
                link = link_elem['href']
                if link.startswith('/'): 
                    link = "https://www.mercadolivre.com.br" + link
                
                img_url = None
                if img_elem:
                    img_url = img_elem.get('data-src') or img_elem.get('src')

                oferta_id = f"{nome}-{preco}"
                
                # Para o primeiro teste, você pode usar 'if True:' se quiser forçar
                if oferta_id not in ofertas_postadas:
                    texto = (
                        f"⚡ **OFERTA DO MOMENTO!** ⚡\n\n"
                        f"📦 {nome}\n"
                        f"💰 **R$ {preco},00**\n\n"
                        f"🔗 [CLIQUE AQUI PARA VER]({link})"
                    )
                    
                    print(f"📤 Postando: {nome[:30]}...")
                    
                    try:
                        if img_url:
                            await bot.send_photo(chat_id=CHAVE_DO_CANAL, photo=img_url, caption=texto, parse_mode='Markdown')
                        else:
                            await bot.send_message(chat_id=CHAVE_DO_CANAL, text=texto, parse_mode='Markdown')
                        
                        ofertas_postadas.add(oferta_id)
                        contagem += 1
                        await asyncio.sleep(5)
                    except Exception as e:
                        print(f"⚠️ Erro no envio: {e}")
                else:
                    print(f"😴 {nome[:20]}... já postado.")

    except Exception as e:
        print(f"💥 ERRO NO GARIMPO: {e}")

# --- 4. AGENDAMENTO E EXECUÇÃO ---
def tarefa():
    asyncio.run(garimpar_ofertas())

# Inicia a cada 1 hora
schedule.every(1).hours.do(tarefa)

print("🚀 >>> ROBÔ OFICIAL ATIVADO! <<<")
# Executa a primeira vez ao ligar
tarefa()

while True:
    schedule.run_pending()
    time.sleep(1)
