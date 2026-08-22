import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import streamlit as st

def send_otp_email(to_email: str, otp_code: str) -> bool:
    """
    Sends an OTP email using standard smtplib.
    Requires st.secrets["smtp"] configuration.
    """
    try:
        if "smtp" not in st.secrets:
            print("Error: SMTP secrets not configured in .streamlit/secrets.toml")
            return False
            
        smtp_conf = st.secrets["smtp"]
        smtp_server = smtp_conf.get("server", "smtp.gmail.com")
        smtp_port = smtp_conf.get("port", 465)
        sender_email = smtp_conf.get("username")
        sender_password = smtp_conf.get("password")
        
        if not sender_email or not sender_password:
            print("Error: SMTP credentials missing")
            return False

        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = to_email
        msg["Subject"] = "Your Password Recovery OTP"

        body = f"""
        Hello,

        You have requested to reset your password.
        Your One-Time Password (OTP) is: {otp_code}

        This code will expire in 10 minutes. 
        If you did not request a password reset, please ignore this email.

        Regards,
        In-House Expense Tracker
        """
        msg.attach(MIMEText(body, "plain"))

        # For port 465, typically we use SMTP_SSL
        if smtp_port == 465:
            with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
                server.login(sender_email, sender_password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(sender_email, sender_password)
                server.send_message(msg)
                
        return True
    except Exception as e:
        print(f"Failed to send email OTP: {e}")
        return False
