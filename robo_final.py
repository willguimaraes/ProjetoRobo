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

# --- 1. CONFIGURAÇÃO DE LOG EM TEMPO REAL ---
sys.stdout.reconfigure(line_buffering=True)

# --- 2. SERVIDOR FANTASMA ---
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot Online!")
    def log_message(self, format, *args):
        return

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHandler)
    print(f"✅ [SISTEMA] Porta {port} aberta.", flush=True)
    server.serve_forever()

threading.Thread(target=run_server, daemon=True).start()

# --- 3. CONFIGURAÇÕES (Onde estava o erro!) ---
TOKEN = '8512528196:AAHCRuMbwSSgILe_WEv98D0c8TWgdatp8o8'
CHAVE_DO_CANAL = '@promodagota'
URL_OFERTAS = 'https://www.mercadolivre.com.br/ofertas#nav-header'

# ESTA LINHA É A QUE ESTAVA FALTANDO OU ESTAVA NO LUGAR ERRADO:
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
}

ofertas_postadas = set()

# 2. --- FUNÇÃO DE GARIMPO ---

async def garimpar_ofertas():
    global ofertas_postadas
    bot = Bot(token=TOKEN)
    
    print(f"\n[{time.strftime('%H:%M:%S')}] 🕵️‍♂️ Iniciando garimpo...")
    
    try:
        resposta = requests.get(URL_OFERTAS, headers=HEADERS, timeout=10)
        if resposta.status_code != 200:
            print(f"❌ Erro HTTP: {resposta.status_code}")
            return

        site = BeautifulSoup(resposta.text, 'html.parser')
        
        # --- NOVO SELETOR (Tenta 3 padrões diferentes do Mercado Livre) ---
        # 1. Tenta o padrão de lista de ofertas do dia
        produtos = site.find_all('li', class_='promotion-item')
        
        # 2. Se não achou, tenta o padrão de cards novos (Poly-card)
        if not produtos:
            produtos = site.find_all('div', class_='poly-card')
            
        # 3. Se ainda não achou, tenta o container genérico
        if not produtos:
            produtos = site.find_all('div', class_='promotion-item__container')

        print(f"🔎 Encontrei {len(produtos)} produtos na página.")

        for produto in produtos:
            # Busca o título (geralmente em um <a> ou <p>)
            nome_elem = produto.find('p', class_='promotion-item__title') or \
                        produto.find('h2') or \
                        produto.find('a', class_='poly-component__title')
            
            # Busca o preço
            preco_elem = produto.find('span', class_='andes-money-amount__fraction')
            
            # Busca o link
            link_elem = produto.find('a', href=True)

            if nome_elem and preco_elem and link_elem:
                nome = nome_elem.text.strip()
                preco = preco_elem.text.strip()
                link = link_elem['href']
                
                # Se for link relativo, completa com o domínio
                if link.startswith('/'):
                    link = "https://www.mercadolivre.com.br" + link
                
                oferta_id = f"{nome}-{preco}"
                
                if oferta_id not in ofertas_postadas:
                    texto = (
                        f"⚡ **OFERTA DO MOMENTO!** ⚡\n\n"
                        f"📦 {nome}\n"
                        f"💰 **R$ {preco},00**\n\n"
                        f"🔗 [CLIQUE AQUI PARA VER]({link})"
                    )
                    
                    print(f"📤 Postando: {nome[:30]}...")
                    await bot.send_message(chat_id=CHAVE_DO_CANAL, text=texto, parse_mode='Markdown')
                    ofertas_postadas.add(oferta_id)
                    time.sleep(2)
                    
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
