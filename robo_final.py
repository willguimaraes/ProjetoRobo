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

# --- 1. CONFIGURAÇÃO DE SERVIDOR (MANTER ATIVO NO RENDER) ---
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

# --- 2. CONFIGURAÇÕES DO BOT E AFILIADO ---
TOKEN = '8512528196:AAHCRuMbwSSgILe_WEv98D0c8TWgdatp8o8'
CHAVE_DO_CANAL = '@promodagota'
URL_OFERTAS = 'https://www.mercadolivre.com.br/ofertas#nav-header'
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'}

# Seus IDs de Afiliado extraídos do seu link
MATT_TOOL = "11823943"
MATT_WORD = "guwi2000508"

# Memória temporária do robô
ofertas_postadas = set()

# --- 3. FUNÇÃO DE GARIMPO (ESTRATÉGIA ANTI-REPETIÇÃO) ---
async def garimpar_ofertas():
    global ofertas_postadas
    bot = Bot(token=TOKEN)
    
    print(f"\n[{time.strftime('%H:%M:%S')}] 🕵️‍♂️ Procurando novidades...")
    
    try:
        resposta = requests.get(URL_OFERTAS, headers=HEADERS, timeout=15)
        site = BeautifulSoup(resposta.text, 'html.parser')
        
        # Seleciona a lista de produtos da página
        produtos_brutos = site.find_all('li', class_='promotion-item') or \
                         site.find_all('div', class_='poly-card')

        if not produtos_brutos:
            print("⚠️ Página de ofertas vazia ou mudou de formato.")
            return

        # FILTRAGEM: Remove o que já foi postado nesta sessão
        novidades = []
        for p in produtos_brutos:
            nome_e = p.find('p') or p.find('h2') or p.find('a', class_='poly-component__title')
            preco_e = p.find('span', class_='andes-money-amount__fraction')
            
            if nome_e and preco_e:
                oferta_id = f"{nome_e.text.strip()}-{preco_e.text.strip()}"
                if oferta_id not in ofertas_postadas:
                    novidades.append(p)

        if not novidades:
            print("😴 Sem novidades reais agora. Aguardando próxima rodada...")
            return

        # SORTEIO: Escolhe 1 aleatório entre as 10 primeiras novidades
        # Isso evita postar sempre o mesmo produto do topo da lista
        produto_escolhido = random.choice(novidades[:10]) 

        # Extração de dados do escolhido
        nome_e = produto_escolhido.find('p') or produto_escolhido.find('h2') or produto_escolhido.find('a', class_='poly-component__title')
        preco_e = produto_escolhido.find('span', class_='andes-money-amount__fraction')
        link_e = produto_escolhido.find('a', href=True)
        img_e = produto_escolhido.find('img')

        nome = nome_e.text.strip()
        preco = preco_e.text.strip()
        link_original = link_e['href']
        if link_original.startswith('/'): 
            link_original = "https://www.mercadolivre.com.br" + link_original
        
        # Montagem do Link de Afiliado Rastreável
        divisor = "&" if "?" in link_original else "?"
        link_afiliado = f"{link_original}{divisor}matt_tool={MATT_TOOL}&matt_word={MATT_WORD}"
        
        img_url = img_e.get('data-src') or img_e.get('src') if img_e else None
        
        # Conteúdo do Post
        texto = (
            f"🔥 **OFERTA DO MOMENTO!** 🔥\n\n"
            f"📦 {nome}\n"
            f"💰 **R$ {preco},00**\n\n"
            f"⚡ *Garanta o seu antes que o estoque acabe!*"
        )
        
        # Botão estilizado
        teclado = InlineKeyboardMarkup([
            [InlineKeyboardButton("🛒 IR PARA A LOJA", url=link_afiliado)]
        ])
        
        print(f"📤 Postando: {nome[:30]}...")
        
        try:
            if img_url:
                await bot.send_photo(chat_id=CHAVE_DO_CANAL, photo=img_url, caption=texto, parse_mode='Markdown', reply_markup=teclado)
            else:
                await bot.send_message(chat_id=CHAVE_DO_CANAL, text=texto, parse_mode='Markdown', reply_markup=teclado)
            
            # Adiciona à memória para não repetir na próxima verificação
            ofertas_postadas.add(f"{nome}-{preco}")
            print("✅ Sucesso!")
        except Exception as e:
            print(f"❌ Erro no envio: {e}")
                
    except Exception as e:
        print(f"💥 Erro no garimpo: {e}")

# --- 4. CONTROLE DE AGENDAMENTO E HORÁRIO ---
def tarefa():
    hora = time.localtime().tm_hour
    # Posta entre 08h e 22h (Ajuste conforme o fuso do servidor)
    if 8 <= hora <= 22:
        asyncio.run(garimpar_ofertas())
    else:
        print(f"😴 Madrugada ({hora}h). Robô em repouso.")

# Intervalo de 20 minutos
schedule.every(20).minutes.do(tarefa)

print("🚀 ROBÔ DIAMANTE ATIVADO (1 prod / 20 min / Aleatório)")

# Inicia a primeira vez
tarefa()

while True:
    schedule.run_pending()
    time.sleep(1)
