import smtplib
from email.mime.text import MIMEText

SMTP_HOST = 'smtp.gmail.com'
SMTP_PORT = 587
SMTP_USER = 'bremas0104@gmail.com'
SMTP_PASSWORD = 'htjyotjqzdcmkmea'  

async def enviar_email_reset(destinatario_email: str, token: str):
    corpo = f"Clique no link para resetar sua senha:\n\nhttp://127.0.0.1:8000/resetar-senha?token={token}"
    
    mensagem = MIMEText(corpo)
    mensagem['Subject'] = 'Reset de Senha - Sistema de Usuários'
    mensagem['From'] = SMTP_USER
    mensagem['To'] = destinatario_email

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_USER, destinatario_email, mensagem.as_string())
