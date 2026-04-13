import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

# Load env variables
dotenv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'config', '.env'))
load_dotenv(dotenv_path)

GMAIL_SENDER = os.getenv("GMAIL_SENDER")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
GMAIL_RECEIVER = os.getenv("GMAIL_RECEIVER", GMAIL_SENDER)


def send_alert(need_data: dict):
    # 🛑 Safety check
    if not GMAIL_SENDER or not GMAIL_APP_PASSWORD:
        print("⚠ GMAIL_SENDER or GMAIL_APP_PASSWORD not set. Skipping email alert.")
        return False

    try:
        msg = EmailMessage()

        severity = str(need_data.get('severity', 'high')).upper()

        msg['Subject'] = f"🚨 URGENT ALERT: {severity} Severity Need"
        msg['From'] = GMAIL_SENDER
        msg['To'] = GMAIL_RECEIVER

        content = f"""
🚨 SETU ALERT SYSTEM 🚨

A HIGH PRIORITY NEED HAS BEEN DETECTED

----------------------------------------
Severity: {need_data.get('severity')}
Category: {need_data.get('category')}
Description: {need_data.get('description')}

Disaster Type: {need_data.get('disaster_type')}
Help Needed: {need_data.get('help_needed')}

Location:
Lat: {need_data.get('lat')}
Lng: {need_data.get('lng')}

AI Flag: {need_data.get('flag')}
----------------------------------------

⚡ Immediate action required.
"""

        msg.set_content(content)

        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(GMAIL_SENDER, GMAIL_APP_PASSWORD)
            server.send_message(msg)

        print("📧 Alert email sent successfully!")
        return True

    except Exception as e:
        print(f"❌ Email Error: {e}")
        return False