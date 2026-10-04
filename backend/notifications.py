# notifications.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import os
from database import get_connection

load_dotenv()

SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
SENDER_EMAIL = os.getenv('SENDER_EMAIL')
SENDER_PASSWORD = os.getenv('SENDER_PASSWORD')


def send_price_alert(user_email, product_name, target_price, current_price):
    """Send email notification when price drops to target. Returns True if sent, False on failure."""
    
    subject = f"Alert: {product_name} dropped to ${current_price}!"
    
    body = f"""
    Great news! {product_name} has dropped to your target price of ${target_price}.
    Check it out before it runs out!
    
    Best regards,
    Price Tracker Team
    """
    
    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = user_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        
        print(f"Email sent to {user_email}")
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False