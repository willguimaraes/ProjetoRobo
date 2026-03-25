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

# --- 1. SERVIDOR PARA MANTER ATIVO (UPTIME ROBOT) ---
sys.stdout.reconfigure(line_buffering=True)

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot @promodagota - Sistema Seguro e Ativo!")
    def log_message(self, format, *args): return

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHandler)
    server.serve_forever()

threading.Thread(target=run_server, daemon=True).start()

# --- 2. CONFIGURAÇÕES PROTEGIDAS (VARIÁVEIS DE AMBIENTE) ---
TOKEN = os.environ.get('TELEGRAM_TOKEN')
MATT_TOOL = os.environ.get('MATT_TOOL')
MATT_WORD = os.environ.get('MATT_WORD')

CHAVE_DO_CANAL = '@promodagota'
URL_OFERTAS = 'https://www.mercadolivre.com.br/ofertas#nav-header'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
}

# Memória temporária para evitar repetição de links
ofertas_postadas = []

# --- 3. FUNÇÃO DE GARIMPO ---
async def garimpar_ofertas():
    global ofertas_postadas
    
    # Validação de segurança: se as chaves não existirem no Render, o bot avisa no log
    if not TOKEN or not MATT_TOOL or not MATT_WORD:
        print("❌ ERRO CRÍTICO: Variáveis de ambiente (TOKEN ou IDs) não configuradas no Render!")
        return

    bot = Bot(token=TOKEN)
    
    # Ajuste de Horário de Brasília (-3h em relação ao servidor UTC)
    hora_utc = time.gmtime().tm_hour
    hora_brasil = (hora_utc - 3) % 24
    print(f"\n[{hora_brasil:02d}:00 BRT] 🕵️‍♂️ Iniciando busca por novas ofertas...")
    
    try:
        resposta = requests.get(URL_OFERTAS, headers=HEADERS, timeout=15)
        site = BeautifulSoup(resposta.text, 'html.parser')
        
        # Seletores de produtos (M.Livre costuma usar essas classes)
        produtos_brutos = site.find_all(['li', 'div'], class_=['promotion-item', 'poly-card', 'promotion-item__container'])

        novidades = []
        for p in produtos_brutos:
            link_e = p.find('a', href=True)
            if not link_e: continue
            
            link_limpo = link_e['href'].split("#")[0]
            
            # Pula se o link já estiver na memória recente
            if link_limpo in ofertas_postadas: continue

            nome_e = p.find(['p', 'h2', 'h3']) or p.select_one('.poly-component__title')
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
            print("😴 Nenhuma novidade encontrada. Limpando histórico antigo para renovar...")
            if len(ofertas_postadas) > 40: 
                ofertas_postadas = ofertas_postadas[-15:]
            return

        # Sorteia um produto entre os primeiros resultados para dar dinâmica ao canal
        escolhido = random.choice(novidades[:15])
        
        link_final = escolhido['link']
        if link_final.startswith('/'): 
            link_final = "https://www.mercadolivre.com.br" + link_final
        
        # Montagem do link usando as chaves secretas do Render
        divisor = "&" if "?" in link_final else "?"
        link_afiliado = f"{link_final}{divisor}matt_tool={MATT_TOOL}&matt_word={MATT_WORD}"
        
        img_url = escolhido['img_e'].get('data-src') or escolhido['img_e'].get('src') if escolhido['img_e'] else None
        
        texto = (
            f"🔥 **OFERTA DO MOMENTO!** 🔥\n\n"
            f"📦 {escolhido['nome']}\n"
            f"💰 **R$ {escolhido['preco']},00**\n\n"
            f"⚡ *Garanta o seu antes que o preço suba!*"
        )
        
        teclado = InlineKeyboardMarkup([[InlineKeyboardButton("🛒 IR PARA A LOJA", url=link_afiliado)]])
        
        print(f"📤 Postando novidade no Telegram: {escolhido['nome'][:30]}...")
        
        try:
            if img_url:
                await bot.send_photo(chat_id=CHAVE_DO_CANAL, photo=img_url, caption=texto, parse_mode='Markdown', reply_markup=teclado)
            else:
                await bot.send_message(chat_id=CHAVE_DO_CANAL, text=texto, parse_mode='Markdown', reply_markup=teclado)
            
            # Registra o link postado para não repetir
            ofertas_postadas.append(escolhido['link'])
            print("✅ Sucesso!")
        except Exception as e:
            print(f"❌ Erro ao enviar mensagem: {e}")
                
    except Exception as e:
        print(f"💥 Erro geral no garimpo: {e}")

# --- 4. AGENDAMENTO E REGRAS DE HORÁRIO ---
def tarefa():
    # Sincronização com o horário do Brasil
    hora_utc = time.gmtime().tm_hour
    hora_brasil = (hora_utc - 3) % 24
    
    # Só trabalha das 08h às 22h (Horário de Brasília)
    if 8 <= hora_brasil <= 22:
        asyncio.run(garimpar_ofertas())
    else:
        print(f"😴 Madrugada no Brasil ({hora_brasil:02d}h). Robô descansando.")

# Execução a cada 20 minutos
schedule.every(20).minutes.do(tarefa)

print("🚀 ROBÔ @PROMODAGOTA PROTEGIDO E EM OPERAÇÃO!")
print("Configure as variáveis TELEGRAM_TOKEN, MATT_TOOL e MATT_WORD no Render.")

# Teste inicial imediato
tarefa()

while True:
    schedule.run_pending()
    time.sleep(1)
