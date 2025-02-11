import os
from dotenv import load_dotenv
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from groq import Groq
import asyncio
import aiohttp

# Carrega as variáveis de ambiente
load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')

if not TELEGRAM_TOKEN:
    raise ValueError("Token do Telegram não encontrado. Configure TELEGRAM_TOKEN no arquivo .env")
if not GROQ_API_KEY:
    raise ValueError("Chave API do Groq não encontrada. Configure GROQ_API_KEY no arquivo .env")

groq_client = Groq(api_key=GROQ_API_KEY)

def configurar_driver():
    """Configura o Chrome em modo headless"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Roda em background
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--disable-popup-blocking")
    return webdriver.Chrome(options=chrome_options)

def buscar_noticias_cointelegraph(driver):
    """Busca notícias no Cointelegraph"""
    noticias = []
    try:
        driver.get("https://cointelegraph.com.br/")
        wait = WebDriverWait(driver, 10)
        
        # Espera os artigos carregarem
        artigos = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "article.post-card__item")))
        
        for artigo in artigos[:3]:  # Pegando as 3 primeiras notícias
            try:
                titulo = artigo.find_element(By.CSS_SELECTOR, ".post-card__title").text
                link = artigo.find_element(By.TAG_NAME, "a").get_attribute("href")
                noticias.append({
                    'titulo': titulo,
                    'link': link,
                    'fonte': 'Cointelegraph'
                })
            except Exception as e:
                print(f"Erro ao extrair artigo Cointelegraph: {e}")
                
    except Exception as e:
        print(f"Erro no Cointelegraph: {e}")
    return noticias

def buscar_noticias_criptofacil(driver):
    """Busca notícias no Criptofácil"""
    noticias = []
    try:
        driver.get("https://www.criptofacil.com/ultimas-noticias/")
        wait = WebDriverWait(driver, 10)
        
        artigos = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "article.jeg_post")))
        
        for artigo in artigos[:3]:
            try:
                titulo = artigo.find_element(By.CSS_SELECTOR, ".jeg_post_title").text
                link = artigo.find_element(By.CSS_SELECTOR, ".jeg_post_title a").get_attribute("href")
                noticias.append({
                    'titulo': titulo,
                    'link': link,
                    'fonte': 'Criptofácil'
                })
            except Exception as e:
                print(f"Erro ao extrair artigo Criptofácil: {e}")
                
    except Exception as e:
        print(f"Erro no Criptofácil: {e}")
    return noticias

async def buscar_crypto():
    """Busca informações das principais criptomoedas"""
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        'ids': 'bitcoin,ethereum,binancecoin,ripple,cardano,solana',
        'vs_currencies': 'usd,brl',
        'include_24hr_change': 'true',
        'include_market_cap': 'true'
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, params=params) as response:
                dados = await response.json()
                mensagem = "📊 *MERCADO CRIPTO* 📊\n\n"
                
                for moeda, info in dados.items():
                    nome = moeda.capitalize()
                    preco_usd = info['usd']
                    preco_brl = info['brl']
                    variacao = info['usd_24h_change']
                    market_cap = info['usd_market_cap']
                    
                    emoji = "🟢" if variacao > 0 else "🔴"
                    
                    mensagem += f"*{nome}* {emoji}\n"
                    mensagem += f"USD: ${preco_usd:,.2f}\n"
                    mensagem += f"BRL: R${preco_brl:,.2f}\n"
                    mensagem += f"24h: {variacao:.2f}%\n"
                    mensagem += f"Market Cap: ${market_cap:,.0f}\n\n"
                
                return mensagem
        
        except Exception as e:
            print(f"Erro ao buscar dados cripto: {e}")
            return "Erro ao buscar informações de criptomoedas."

def buscar_todas_noticias():
    """Busca notícias de todas as fontes usando Selenium"""
    driver = configurar_driver()
    todas_noticias = []
    
    try:
        # Busca notícias de cada fonte
        todas_noticias.extend(buscar_noticias_cointelegraph(driver))
        todas_noticias.extend(buscar_noticias_criptofacil(driver))
        
    except Exception as e:
        print(f"Erro ao buscar notícias: {e}")
    
    finally:
        driver.quit()
    
    return todas_noticias

def start(update, context):
    """Comando /start"""
    mensagem = """
Olá! 👋 Eu sou um bot especializado em criptomoedas.

Comandos disponíveis:
📰 "quero as noticias" - Receba as últimas notícias do mundo cripto
💰 "crypto" - Veja as cotações das principais criptomoedas

Experimente agora mesmo!
    """
    update.message.reply_text(mensagem)

def processar_mensagem(update, context):
    """Processa mensagens recebidas"""
    mensagem = update.message.text.lower()
    
    if mensagem == "quero as noticias":
        update.message.reply_text("Buscando as últimas notícias do mundo cripto... Aguarde um momento.")
        
        noticias = buscar_todas_noticias()
        if not noticias:
            update.message.reply_text("Desculpe, não consegui buscar as notícias no momento. Tente novamente mais tarde.")
            return
            
        resposta = "📰 *ÚLTIMAS NOTÍCIAS CRIPTO* 📰\n\n"
        
        for noticia in noticias:
            resposta += f"*{noticia['fonte']}*\n"
            resposta += f"📌 {noticia['titulo']}\n"
            resposta += f"🔗 {noticia['link']}\n\n"
            
        # Dividindo a resposta em partes se for muito longa
        max_length = 4096
        for i in range(0, len(resposta), max_length):
            update.message.reply_text(
                resposta[i:i+max_length],
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
            
    elif mensagem == "crypto":
        update.message.reply_text("Buscando informações do mercado cripto... Aguarde um momento.")
        resposta = asyncio.run(buscar_crypto())
        update.message.reply_text(resposta, parse_mode='Markdown')

def main():
    """Função principal"""
    try:
        updater = Updater(TELEGRAM_TOKEN, use_context=True)
        dp = updater.dispatcher

        # Registrando handlers
        dp.add_handler(CommandHandler("start", start))
        dp.add_handler(MessageHandler(Filters.text & ~Filters.command, processar_mensagem))

        # Iniciando o bot
        print("Iniciando o bot...")
        updater.start_polling()
        print("Bot iniciado com sucesso!")
        updater.idle()
        
    except Exception as e:
        print(f"Erro ao iniciar o bot: {e}")
        raise

if __name__ == '__main__':
    main()