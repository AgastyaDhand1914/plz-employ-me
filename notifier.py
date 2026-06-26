import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import GMAIL_ADDRESS, GMAIL_APP_PASSWORD

def send_digest_email(subject: str, body: str, to_address: str = None) -> None:
    """sends a plain text digest email via gmail SMTP
    if recipeint not provided, send to yourself (default)"""
    
    recipient = to_address or GMAIL_ADDRESS

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = recipient

    #attach as plain text
    part = MIMEText(body, "plain")
    msg.attach(part)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_ADDRESS, recipient, msg.as_string())
        print(f"[notifier] Digest sent to {recipient}")