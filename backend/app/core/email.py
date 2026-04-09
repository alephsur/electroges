"""Email sending utility. Uses SMTP when enabled, logs to console otherwise."""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings

logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, html_body: str) -> None:
    """Send an email. Falls back to log output when SMTP is disabled."""
    if not settings.SMTP_ENABLED:
        logger.info(
            "SMTP disabled — email not sent.\n  To: %s\n  Subject: %s\n  Body:\n%s",
            to,
            subject,
            html_body,
        )
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM_EMAIL
    msg["To"] = to
    msg.attach(MIMEText(html_body, "html"))

    try:
        if settings.SMTP_USE_TLS:
            server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT)

        if settings.SMTP_USER:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)

        server.sendmail(settings.SMTP_FROM_EMAIL, to, msg.as_string())
        server.quit()
        logger.info("Email sent to %s — %s", to, subject)
    except Exception:
        logger.exception("Failed to send email to %s", to)
        raise


def send_invitation_email(to_email: str, full_name: str, tenant_name: str, activation_url: str) -> None:
    subject = f"Invitación a ElectroGes — {tenant_name}"
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #1e40af;">Bienvenido a ElectroGes</h2>
        <p>Hola <strong>{full_name}</strong>,</p>
        <p>Has sido invitado como administrador de <strong>{tenant_name}</strong> en ElectroGes.</p>
        <p>Haz clic en el botón para activar tu cuenta y crear tu contraseña:</p>
        <p style="margin: 24px 0;">
            <a href="{activation_url}"
               style="background-color: #1e40af; color: white; padding: 12px 24px;
                      text-decoration: none; border-radius: 6px; display: inline-block;">
                Activar cuenta
            </a>
        </p>
        <p style="color: #6b7280; font-size: 14px;">
            Este enlace es válido durante 48 horas.<br>
            Si no esperabas esta invitación, puedes ignorar este email.
        </p>
        <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 24px 0;">
        <p style="color: #9ca3af; font-size: 12px;">ElectroGes — Sistema de gestión para instalaciones eléctricas</p>
    </body>
    </html>
    """
    send_email(to_email, subject, html_body)
