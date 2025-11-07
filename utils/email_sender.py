"""
Módulo para envio de e-mails
"""
import os
import smtplib
from email.message import EmailMessage
import pandas as pd
from constants import (
    VENDEDOR_EMAIL_NORMALIZADO, 
    EMAIL_COPIA_COMISSOES,
    SMTP_CONFIG
)
from .pdf_generator import gerar_pdf_extrato


def enviar_email_comissao(df_vendedor: pd.DataFrame, tmp_pdf_path: str = None):
    """
    Gera PDF e envia o extrato de comissão para validação
    
    Args:
        df_vendedor: DataFrame com os dados do vendedor
        tmp_pdf_path: Caminho opcional para o PDF temporário
        
    Raises:
        ValueError: Se vendedor não tiver e-mail cadastrado
        Exception: Erros no envio do e-mail
    """
    try:
        # Identifica o vendedor
        vendedor = df_vendedor["Vendedor"].iloc[0].strip().upper()
        print(f"Procurando e-mail para vendedor: '{vendedor}'")
        
        email = VENDEDOR_EMAIL_NORMALIZADO.get(vendedor)
        print(f"E-mail encontrado: {email}")

        if not email:
            raise ValueError(f"O vendedor '{vendedor}' não possui e-mail configurado.")

        # Define o caminho do PDF temporário
        if tmp_pdf_path is None:
            tmp_pdf_path = f"extrato_validacao_{vendedor}.pdf"

        # Gera o PDF
        gerar_pdf_extrato(tmp_pdf_path, df_vendedor)

        # Composição do e-mail
        msg = EmailMessage()
        msg["Subject"] = f"Extrato de Comissão - {vendedor} (Validação)"
        msg["From"] = SMTP_CONFIG["user"]
        msg["To"] = email
        msg["Cc"] = EMAIL_COPIA_COMISSOES
        msg["Reply-To"] = EMAIL_COPIA_COMISSOES
        msg.set_content(
            f"Olá {vendedor},\n\n"
            "Segue o extrato de comissão para validação.\n"
            "Por favor, verifique e nos retorne caso haja divergências.\n\n"
            "Atenciosamente"
        )

        # Anexa o PDF
        with open(tmp_pdf_path, "rb") as f:
            msg.add_attachment(
                f.read(),
                maintype="application",
                subtype="pdf",
                filename=f"extrato_validacao_{vendedor}.pdf"
            )

        # Envia o e-mail
        srv = smtplib.SMTP(SMTP_CONFIG["host"], SMTP_CONFIG["port"], timeout=30)
        if SMTP_CONFIG["use_tls"]:
            srv.starttls()
        srv.login(SMTP_CONFIG["user"], SMTP_CONFIG["password"])
        srv.send_message(msg)
        srv.quit()

        print(f"E-mail enviado para: {email}")

    except Exception as e:
        print(f"Erro ao enviar e-mail: {str(e)}")
        raise

    finally:
        # Remove o arquivo temporário
        if tmp_pdf_path and os.path.exists(tmp_pdf_path):
            try:
                os.remove(tmp_pdf_path)
            except:
                pass