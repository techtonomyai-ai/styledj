"""Email service for StyleDJ — verification + password reset via Resend."""
import os
import resend

resend.api_key = os.getenv("RESEND_API_KEY", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", "noreply@techtonomy.ai")
APP_URL = os.getenv("FRONTEND_URL", "https://web-production-0acd2.up.railway.app")


def send_verification_email(to_email: str, token: str) -> bool:
    try:
        resend.Emails.send({
            "from": f"StyleDJ <{FROM_EMAIL}>",
            "to": [to_email],
            "subject": "⚡ Verify your StyleDJ account",
            "html": f"""
            <div style="font-family:sans-serif;max-width:480px;margin:0 auto;background:#0A0A0F;color:#E0E0FF;padding:40px;border-radius:16px;">
              <h1 style="background:linear-gradient(135deg,#7B2FBE,#00D4FF);-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-size:2rem;">⚡ StyleDJ</h1>
              <h2 style="color:#E0E0FF;">Verify your email</h2>
              <p style="color:#888;">Click the button below to verify your account and start generating tracks.</p>
              <a href="{APP_URL}/verify?token={token}" 
                 style="display:inline-block;margin:24px 0;padding:14px 28px;background:linear-gradient(135deg,#7B2FBE,#00D4FF);color:#fff;text-decoration:none;border-radius:8px;font-weight:700;">
                ✅ Verify Email
              </a>
              <p style="color:#555;font-size:0.85rem;">Link expires in 24 hours. If you didn't sign up, ignore this email.</p>
            </div>
            """
        })
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False


def send_password_reset_email(to_email: str, token: str) -> bool:
    try:
        resend.Emails.send({
            "from": f"StyleDJ <{FROM_EMAIL}>",
            "to": [to_email],
            "subject": "🔑 Reset your StyleDJ password",
            "html": f"""
            <div style="font-family:sans-serif;max-width:480px;margin:0 auto;background:#0A0A0F;color:#E0E0FF;padding:40px;border-radius:16px;">
              <h1 style="background:linear-gradient(135deg,#7B2FBE,#00D4FF);-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-size:2rem;">⚡ StyleDJ</h1>
              <h2 style="color:#E0E0FF;">Reset your password</h2>
              <p style="color:#888;">We received a request to reset your StyleDJ password.</p>
              <a href="{APP_URL}/reset-password?token={token}" 
                 style="display:inline-block;margin:24px 0;padding:14px 28px;background:linear-gradient(135deg,#7B2FBE,#00D4FF);color:#fff;text-decoration:none;border-radius:8px;font-weight:700;">
                🔑 Reset Password
              </a>
              <p style="color:#555;font-size:0.85rem;">Link expires in 1 hour. If you didn't request this, ignore this email.</p>
            </div>
            """
        })
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False
