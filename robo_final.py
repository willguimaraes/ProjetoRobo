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

# --- 1. ESTABILIDADE (RENDER) ---
# --- 1. ESTABILIDADE ---
sys.stdout.reconfigure(line_buffering=True)

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot Categorias Ativo")
        self.wfile.write(b"Bot @promodagota - Rodizio de Categorias")
    def log_message(self, format, *args): return

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHandler)
    server.serve_forever()

def self_ping():
    app_url = os.environ.get("RENDER_EXTERNAL_URL")
    while True:
        if app_url:
            try: requests.get(app_url, timeout=10)
            except: pass
        time.sleep(300)

threading.Thread(target=run_server, daemon=True).start()
threading.Thread(target=self_ping, daemon=True).start()

# --- 2. CONFIGURAÇÕES ---
TOKEN = os.environ.get('TELEGRAM_TOKEN')
@@ -44,25 +35,29 @@
CHAVE_DO_CANAL = '@promodagota'
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'}

# --- 3. LISTA DE CATEGORIAS (MINAS DE OURO) ---
# LISTA DE CATEGORIAS ORGANIZADA
CATEGORIAS_ML = [
    {"nome": "TECNOLOGIA", "url": "https://www.mercadolivre.com.br/ofertas#c_id=MLB1051&category=MLB1051"},
    {"nome": "CASA E COZINHA", "url": "https://www.mercadolivre.com.br/ofertas#c_id=MLB1574&category=MLB1574"},
    {"nome": "BELEZA", "url": "https://www.mercadolivre.com.br/ofertas#c_id=MLB1246&category=MLB1246"},
    {"nome": "SUPERMERCADO", "url": "https://www.mercadolivre.com.br/ofertas#c_id=MLB1403&category=MLB1403"}
    {"nome": "BELEZA E SAUDE", "url": "https://www.mercadolivre.com.br/ofertas#c_id=MLB1246&category=MLB1246"},
    {"nome": "SUPERMERCADO", "url": "https://www.mercadolivre.com.br/ofertas#c_id=MLB1403&category=MLB1403"},
    {"nome": "MODA E TENIS", "url": "https://www.mercadolivre.com.br/ofertas#c_id=MLB1430&category=MLB1430"}
]

ofertas_postadas = []
indice_cat = 0
tentar_amazon = True # Alterna entre ML e Amazon
modo_amazon = True # Alterna entre tentar Amazon e ir direto pro ML

# --- 4. BUSCA E POSTAGEM ---
# --- 3. FUNÇÕES DE BUSCA ---

async def buscar_ml(cat_info):
    global ofertas_postadas
    print(f"🔎 [ML] Setor: {cat_info['nome']}")
async def buscar_ml_especifico():
    global ofertas_postadas, indice_cat
    
    cat_atual = CATEGORIAS_ML[indice_cat]
    print(f"🔎 [ML] Garimpando categoria: {cat_atual['nome']}")
    
    try:
        res = requests.get(cat_info['url'], headers=HEADERS, timeout=25)
        res = requests.get(cat_atual['url'], headers=HEADERS, timeout=25)
        site = BeautifulSoup(res.text, 'html.parser')
        produtos = site.find_all(['li', 'div'], class_=['promotion-item', 'poly-card', 'promotion-item__container'])

@@ -84,18 +79,64 @@
                candidatos.append({'nome': nome_e.text.strip(), 'novo': p_novo, 'antigo': p_antigo, 'link': link, 'img': img, 'loja': 'Mercado Livre'})

        if candidatos:
            item = random.choice(candidatos[:25])
            item = random.choice(candidatos[:20])
            link_af = f"{item['link']}{'&' if '?' in item['link'] else '?'}matt_tool={MATT_TOOL}&matt_word={MATT_WORD}"
            await enviar_telegram(item, link_af)
            ofertas_postadas.append(item['link'])
            # Só pula para a próxima categoria se postou com sucesso
            indice_cat = (indice_cat + 1) % len(CATEGORIAS_ML)
            return True
    except Exception as e: print(f"❌ Erro ML: {e}")
    except Exception as e: print(f"❌ Erro ML ({cat_atual['nome']}): {e}")
    return False

async def buscar_amazon():
    # ... (mesma lógica do Plano B anterior) ...
    # Se falhar, ele retorna buscar_ml(CATEGORIAS_ML[0])
    # [Mantido conforme versão anterior para segurança]
    print("🔎 [AMZ] Tentando Amazon...")
    try:
        res = requests.get
        res = requests.get('https://www.amazon.com.br/gp/goldbox', headers=HEADERS, timeout=25)
        site = BeautifulSoup(res.text, 'html.parser')
        produtos = site.select('div[data-testid="grid-desktop-card"]') or site.select('.s-result-item')
        
        if not produtos:
            print("⚠️ Amazon sem resposta visual. Pulando para proxima categoria ML...")
            return await buscar_ml_especifico()
        
        # (Lógica simplificada de extração Amazon...)
        # Se falhar em qualquer ponto da extração, chama o ML:
        return await buscar_ml_especifico()
    except:
        return await buscar_ml_especifico()

async def enviar_telegram(item, link):
    bot = Bot(token=TOKEN)
    preco_html = f"❌ De: <s>R$ {item['antigo']},00</s>\n✅ <b>Por: R$ {item['novo']},00</b>" if item['antigo'] else f"💰 <b>Preço: R$ {item['novo']},00</b>"
    texto = f"🔥 <b>OFERTA {item['loja'].upper()}!</b> 🔥\n\n📦 {item['nome']}\n\n{preco_html}\n\n⚡ <i>Garanta na {item['loja']}!</i>"
    teclado = InlineKeyboardMarkup([[InlineKeyboardButton(f"🛒 VER NA {item['loja'].upper()}", url=link)]])
    if item['img']: await bot.send_photo(chat_id=CHAVE_DO_CANAL, photo=item['img'], caption=texto, parse_mode='HTML', reply_markup=teclado)
    else: await bot.send_message(chat_id=CHAVE_DO_CANAL, text=texto, parse_mode='HTML', reply_markup=teclado)
    print(f"✅ POSTADO: {item['loja']}")

# --- 4. CICLO DE RODÍZIO ---

def tarefa_agendada():
    global modo_amazon
    h_br = (time.gmtime().tm_hour - 3) % 24
    
    if 8 <= h_br <= 23:
        if modo_amazon:
            asyncio.run(buscar_amazon())
            modo_amazon = False # Próxima rodada foca no ML direto
        else:
            asyncio.run(buscar_ml_especifico())
            modo_amazon = True # Próxima rodada tenta Amazon
    else:
        print("😴 Horário de repouso.")

# Executa a cada 10 minutos
schedule.every(10).minutes.do(tarefa_agendada)

print("🚀 BOT @PROMODAGOTA INICIADO COM RODÍZIO REAL!")
tarefa_agendada()

while True:
    schedule.run_pending()
    time.sleep(1)
