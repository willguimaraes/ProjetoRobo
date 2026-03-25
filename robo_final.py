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
        # 1. TENTA ACESSAR O SITE
        resposta = requests.get(URL_OFERTAS, headers=HEADERS, timeout=10)
        print(f"📡 Status da Resposta: {resposta.status_code}")

        if resposta.status_code != 200:
            print("❌ O Mercado Livre bloqueou o acesso do servidor.")
            return

        site = BeautifulSoup(resposta.text, 'html.parser')
        
        # 2. TENTA ENCONTRAR OS PRODUTOS (SELETORES ATUALIZADOS)
        # O ML muda essas classes direto. Vamos tentar as duas mais comuns:
        produtos = site.find_all('li', class_='promotion-item')
        if not produtos:
            produtos = site.find_all('div', class_='promotion-item__container')

        print(f"🔎 Encontrei {len(produtos)} produtos na página.")

        if len(produtos) == 0:
            print("⚠️ Atenção: O site carregou, mas não encontrei nenhum bloco de oferta com esses nomes de classe.")
            # Opcional: print(site.prettify()[:500]) # Isso mostra o começo do HTML no log
            return

        for produto in produtos:
            # Seletores ultra-flexíveis para evitar erros
            nome_elem = produto.find('p') 
            preco_elem = produto.find('span', class_='andes-money-amount__fraction')
            link_elem = produto.find('a')

            if nome_elem and preco_elem and link_elem:
                nome = nome_elem.text.strip()
                preco = preco_elem.text.strip()
                link = link_elem['href']
                
                oferta_id = f"{nome}-{preco}"
                
                if oferta_id not in ofertas_postadas:
                    print(f"📤 Tentando enviar: {nome[:20]}...")
                    await bot.send_message(chat_id=CHAVE_DO_CANAL, text=f"✅ Teste: {nome}\n💰 R$ {preco}", parse_mode='Markdown')
                    ofertas_postadas.add(oferta_id)
                    print("✅ Mensagem enviada com sucesso!")
                else:
                    print(f"😴 {nome[:20]}... já postado.")

    except Exception as e:
        print(f"💥 ERRO CRÍTICO: {e}")
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
