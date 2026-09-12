import smtplib
import base64
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import streamlit as st


def _get_hero_b64() -> str:
    """Return base64-encoded hero image for email header, or empty string if not found."""
    hero_path = os.path.join(os.path.dirname(__file__), "assets", "brand_hero.jpg")
    if os.path.exists(hero_path):
        with open(hero_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    return ""


def send_otp_email(to_email: str, otp_code: str) -> bool:
    """
    Sends a branded HTML OTP email using standard smtplib.
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

        msg = MIMEMultipart("alternative")
        msg["From"] = f"FinCompass <{sender_email}>"
        msg["To"] = to_email
        msg["Subject"] = "🧭 FinCompass — Your Password Recovery OTP"

        # ── Plain text fallback ─────────────────────────────────────────────
        plain_body = f"""Hello,

You have requested to reset your FinCompass password.
Your One-Time Password (OTP) is: {otp_code}

This code will expire in 10 minutes.
If you did not request a password reset, please ignore this email.

Regards,
The FinCompass Team
"""

        # ── Rich HTML version ───────────────────────────────────────────────
        hero_b64 = _get_hero_b64()
        hero_html = (
            f'<img src="data:image/jpeg;base64,{hero_b64}" '
            f'style="width:100%;max-height:220px;object-fit:cover;border-radius:12px 12px 0 0;" alt="FinCompass" />'
            if hero_b64 else
            '<div style="background:linear-gradient(135deg,#0f172a,#1e293b);height:80px;'
            'border-radius:12px 12px 0 0;display:flex;align-items:center;justify-content:center;'
            'font-size:1.8rem;font-weight:900;color:#38bdf8;">🧭 FinCompass</div>'
        )

        html_body = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#0f172a;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0f172a;padding:32px 16px;">
    <tr><td align="center">
      <table width="560" cellpadding="0" cellspacing="0"
             style="background:#1e293b;border-radius:16px;overflow:hidden;
                    border:1px solid #334155;box-shadow:0 20px 60px rgba(0,0,0,0.5);">
        <tr><td>{hero_html}</td></tr>
        <tr>
          <td style="padding:20px 32px 8px;text-align:center;">
            <div style="font-size:1.8rem;font-weight:900;color:#38bdf8;">🧭 FinCompass</div>
            <div style="color:#64748b;font-size:0.85rem;margin-top:2px;">Smart Financial Hub</div>
          </td>
        </tr>
        <tr><td style="padding:0 32px;"><hr style="border:none;border-top:1px solid #334155;margin:12px 0;"></td></tr>
        <tr>
          <td style="padding:16px 32px 24px;">
            <p style="color:#94a3b8;font-size:0.95rem;margin:0 0 20px;">
              Hi there! You requested a password reset for your FinCompass account.
              Use the OTP below to proceed. It expires in <strong style="color:#fbbf24;">10 minutes</strong>.
            </p>
            <div style="background:linear-gradient(135deg,#0f172a,#1e3a5f);
                        border:2px solid #38bdf8;border-radius:12px;
                        padding:24px;text-align:center;margin-bottom:24px;">
              <div style="color:#94a3b8;font-size:0.8rem;text-transform:uppercase;
                          letter-spacing:2px;margin-bottom:8px;">Your One-Time Password</div>
              <div style="font-size:2.8rem;font-weight:900;letter-spacing:10px;
                          color:#38bdf8;font-family:monospace;">{otp_code}</div>
            </div>
            <p style="color:#64748b;font-size:0.82rem;margin:0;">
              If you did not request this, you can safely ignore this email.
              Your password will not change unless you use the OTP above.
            </p>
          </td>
        </tr>
        <tr>
          <td style="background:#0f172a;padding:16px 32px;text-align:center;
                     border-top:1px solid #1e293b;border-radius:0 0 16px 16px;">
            <div style="color:#475569;font-size:0.75rem;">
              &copy; 2026 FinCompass &nbsp;&middot;&nbsp; Smart Financial Hub &nbsp;&middot;&nbsp;
              <span style="color:#38bdf8;">AI-Powered &nbsp;&middot;&nbsp; 360&deg; Wealth View</span>
            </div>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""

        msg.attach(MIMEText(plain_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

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
