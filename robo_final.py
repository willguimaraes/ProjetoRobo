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
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler

# --- 1. CONFIGURAÇÕES (AS VARIÁVEIS DEVEM ESTAR NO RENDER) ---
TOKEN = os.environ.get('TELEGRAM_TOKEN')
MATT_TOOL = os.environ.get('MATT_TOOL')
MATT_WORD = os.environ.get('MATT_WORD')
CHAVE_DO_CANAL = '@promodagota'

# Categorias para o rodízio de ofertas
CATEGORIAS_ML = [
    {"nome": "TECNOLOGIA", "url": "https://www.mercadolivre.com.br/ofertas#c_id=MLB1051&category=MLB1051"},
    {"nome": "CASA & ELETROS", "url": "https://www.mercadolivre.com.br/ofertas#c_id=MLB1574&category=MLB1574"},
    {"nome": "GAMES", "url": "https://www.mercadolivre.com.br/ofertas#c_id=MLB1144&category=MLB1144"},
    {"nome": "MODA", "url": "https://www.mercadolivre.com.br/ofertas#c_id=MLB1430&category=MLB1430"},
    {"nome": "BELEZA", "url": "https://www.mercadolivre.com.br/ofertas#c_id=MLB1246&category=MLB1246"},
    {"nome": "SUPERMERCADO", "url": "https://www.mercadolivre.com.br/ofertas#c_id=MLB1403&category=MLB1403"},
    {"nome": "AUTOMOTIVO", "url": "https://www.mercadolivre.com.br/ofertas#c_id=MLB1743&category=MLB1743"},
    {"nome": "BRINQUEDOS", "url": "https://www.mercadolivre.com.br/ofertas#c_id=MLB1132&category=MLB1132"},
    {"nome": "PET SHOP", "url": "https://www.mercadolivre.com.br/ofertas#c_id=MLB1071&category=MLB1071"}
]

# Dicionário de controle: { "link": datetime_da_postagem }
historico_quarentena = {}
indice_cat = 0
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'}

# --- 2. FUNÇÕES DE APOIO ---

def pode_postar(link):
    """Verifica se o produto já foi postado nas últimas 6 horas"""
    global historico_quarentena
    agora = datetime.now()
    if link in historico_quarentena:
        horario_postado = historico_quarentena[link]
        if agora < horario_postado + timedelta(hours=6):
            return False
    return True

async def enviar_telegram(item, link_final):
    """Envia a oferta formatada para o canal"""
    bot = Bot(token=TOKEN)
    p_html = f"❌ De: <s>R$ {item['antigo']},00</s>\n✅ <b>Por: R$ {item['novo']},00</b>" if item['antigo'] else f"💰 <b>Preço: R$ {item['novo']},00</b>"
    
    texto = (f"🔥 <b>ACHADO NO MERCADO LIVRE!</b> 🔥\n\n"
             f"📦 {item['nome']}\n\n"
             f"{p_html}\n\n"
             f"⚡ <i>Corre para garantir o seu!</i>")
    
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🛒 COMPRAR AGORA", url=link_final)]])
    
    try:
        if item['img']:
            await bot.send_photo(chat_id=CHAVE_DO_CANAL, photo=item['img'], caption=texto, parse_mode='HTML', reply_markup=kb)
        else:
            await bot.send_message(chat_id=CHAVE_DO_CANAL, text=texto, parse_mode='HTML', reply_markup=kb)
        print(f"✅ [TG] Postado com sucesso!")
    except Exception as e:
        print(f"❌ Erro ao enviar Telegram: {e}")

# --- 3. MOTOR DE BUSCA (MERCADO LIVRE) ---

async def executar_ciclo():
    global indice_cat, historico_quarentena
    
    # Ajuste de Horário de Brasília (Render usa UTC)
    h_br =
