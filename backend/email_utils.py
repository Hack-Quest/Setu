import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_otp_email(to_email: str, otp: str) -> bool:
    """Send an OTP email using Gmail SMTP."""
    sender_email = os.getenv("GMAIL_SENDER")
    app_password = os.getenv("GMAIL_APP_PASSWORD")

    if not sender_email or not app_password:
        print("⚠️ Email credentials not configured. Skipping email send.")
        return False

    subject = "Your Setu Login OTP"
    body = f"""
    <html>
      <body>
        <h2>Welcome to Setu</h2>
        <p>Your One-Time Password (OTP) for login is:</p>
        <h1 style="color: #4CAF50; letter-spacing: 2px;">{otp}</h1>
        <p>This OTP will expire in 10 minutes. Do not share it with anyone.</p>
        <p>If you did not request this, please ignore this email.</p>
        <br>
        <p>Stay Safe,</p>
        <p>The Setu Team</p>
      </body>
    </html>
    """

    msg = MIMEMultipart()
    msg['From'] = f"Setu Platform <{sender_email}>"
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html'))

    try:
        # Connect to Gmail SMTP server
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, app_password)
        server.send_message(msg)
        server.quit()
        print(f"📧 OTP email sent to {to_email}")
        return True
    except Exception as e:
        print(f"❌ Failed to send OTP email: {e}")
        return False
