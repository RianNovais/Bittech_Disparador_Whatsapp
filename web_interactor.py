from urllib.parse import quote
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os


def format_phone_number(phone):
    try:
        # Remove todos os caracteres que não são dígitos
        digits_only = ''.join(filter(str.isdigit, phone))

        # Extrai o código de área (assume-se que são os 2 primeiros dígitos)
        area_code = digits_only[:2]

        # Formata como +55 seguido pelo código de área e número
        formatted = f"+55{area_code}{digits_only[2:]}"

        return formatted
    except Exception as e:
        print(f'Erro: {e}')
        return None


def iniciar_sessao_whatsapp():
    """Inicia uma sessão do WhatsApp Web e aguarda autenticação via QR code"""
    print("Iniciando sessão do WhatsApp Web...")

    # Configurar o Firefox
    firefox_options = Options()
    firefox_options.add_argument("--disable-gpu")
    firefox_options.add_argument("--window-size=1920,1080")
    firefox_options.add_argument("--no-sandbox")
    firefox_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")

    # Iniciar o navegador
    driver = webdriver.Firefox(options=firefox_options)

    # Abrir o WhatsApp Web
    driver.get("https://web.whatsapp.com/")

    print("Por favor, escaneie o QR code para autenticar...")

    # Aguardar até que o painel lateral esteja visível (indicando que o usuário está logado)
    try:
        WebDriverWait(driver, 180).until(
            EC.presence_of_element_located((By.XPATH, "//div[@id='side']"))
        )
        print("Autenticação concluída com sucesso!")
        return driver
    except Exception as e:
        print(f"Erro na autenticação: {e}")
        driver.quit()
        return None


def enviar_mensagem(driver, telephone, mensagem, nome_destinatario):
    """Envia uma mensagem para um número específico usando uma sessão já autenticada"""
    try:
        # Formatar o número de telefone
        telephone_formatado = format_phone_number(telephone)
        if not telephone_formatado:
            print(f"Número inválido para {nome_destinatario}")
            return False

        # Abrir conversa com o número específico
        link_mensagem = f'https://web.whatsapp.com/send?phone={telephone_formatado}&text={quote(mensagem)}'

        driver.get(link_mensagem)

        print(f"Carregando conversa com {nome_destinatario}...")

        btn_enviar = WebDriverWait(driver, 60).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="main"]/footer/div[1]/div/span/div/div[2]/div[2]/button'))
        )
        time.sleep(1)
        btn_enviar.click()

        time.sleep(5)

        print(f"Mensagem enviada com sucesso para {nome_destinatario} ({telephone})")

        return True

    except Exception as e:
        print(f"Erro ao enviar mensagem para {nome_destinatario}: {e}")
        return False


def execute_numbers(contatos, progress_callback=None):
    """
    Função para enviar mensagens para uma lista de contatos, com callback de progresso

    Args:
        contatos: Lista de dicionários com 'nome' e 'telefone' para cada contato
        mensagem: Texto da mensagem a ser enviada
        progress_callback: Função de callback para atualizar o progresso na interface
            Assinatura: progress_callback(atual, total, status_text, success=True)

    Returns:
        dict: Estatísticas do envio {'total': n, 'enviadas': n, 'falhas': n}
    """
    # Iniciar a sessão do WhatsApp (usuário escaneia o QR code uma única vez)
    if progress_callback:
        progress_callback(0, len(contatos), "Iniciando sessão do WhatsApp... Escaneie o QRCode", True)

    driver = iniciar_sessao_whatsapp()

    if not driver:
        if progress_callback:
            progress_callback(0, len(contatos), "Não foi possível iniciar a sessão do WhatsApp.", False)
        return {"total": len(contatos), "enviadas": 0, "falhas": len(contatos)}

    # Contador para estatísticas
    enviadas = 0
    falhas = 0
    total = len(contatos)

    try:
        # Enviar mensagem para cada contato
        for i, contato in enumerate(contatos):
            nome = contato['nome']
            telefone = contato['telefone']
            mensagem = contato['mensagem']

            if progress_callback:
                progress_callback(i, total, f"Enviando para {nome}...", True)

            if enviar_mensagem(driver, telefone, mensagem, nome):
                enviadas += 1
                if progress_callback:
                    progress_callback(i + 1, total, f"Enviado com sucesso para {nome}", True)
            else:
                falhas += 1
                if progress_callback:
                    progress_callback(i + 1, total, f"Falha ao enviar para {nome}", False)

            # Pequena pausa para evitar sobrecarga
            time.sleep(2)

        # Resultado final
        status_final = f"Concluído! Enviadas: {enviadas}, Falhas: {falhas}"
        if progress_callback:
            progress_callback(total, total, status_final, True)

        return {
            "total": total,
            "enviadas": enviadas,
            "falhas": falhas
        }

    finally:
        # Fechar o navegador ao final
        print("\nFechando o navegador...")
        driver.quit()
