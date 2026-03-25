import asyncio
import requests
from bs4 import BeautifulSoup
from telegram import Bot
import schedule
import time
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# ==========================================
# 1. TRUQUE DO SERVIDOR (PARA O RENDER NÃO MATAR O ROBÔ)
# ==========================================
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b"Robo Ativo!")

    def log_message(self, format, *args):
        return # Silencia os logs de acesso

def run_dummy_server():
    # O Render injeta a porta na variável de ambiente PORT (geralmente 10000)
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHandler)
    print(f"✅ Porta {port} aberta. Render feliz!")
    server.serve_forever()

# Inicia o servidor fantasma IMEDIATAMENTE
threading.Thread(target=run_dummy_server, daemon=True).start()

# ==========================================
# 2. CONFIGURAÇÕES
# ==========================================
TOKEN = '8512528196:AAHCRuMbwSSgILe_WEv98D0c8TWgdatp8o8'
CHAVE_DO_CANAL = '@promodagota'
URL_OFERTAS = 'https://www.mercadolivre.com.br/ofertas#nav-header'
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'}

ofertas_postadas = set()

# --- A PARTIR DAQUI MANTENHA O SEU CÓDIGO ORIGINAL (Função garimpar_ofertas, etc.) ---

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
        
      # Tentativa de pegar produtos de várias formas (Seletor mais moderno do ML)
        produtos = site.find_all('li', class_='promotion-item') or \
                   site.find_all('div', class_='promotion-item__container')
        
        print(f"🔎 Encontrei {len(produtos)} potenciais ofertas.")

        for produto in produtos:
            # Seletores mais flexíveis
            nome_elem = produto.find('p', class_='promotion-item__title')
            preco_elem = produto.find('span', class_='andes-money-amount__fraction')
            link_elem = produto.find('a') # Pega o primeiro link do bloco
                    
    except Exception as e:
        print(f"Erro no garimpo: {e}")

# 3. --- AGENDADOR ---

def tarefa():
    asyncio.run(garimpar_ofertas())

# Verifica novas ofertas a cada 1 hora (para não virar spam)
schedule.every(1).hours.do(tarefa)

print("🚀 ROBÔ está Acordado e Funcionando! Buscando as 5 melhores ofertas...")
tarefa()

while True:
    schedule.run_pending()
    time.sleep(1)
