"""Async email sending utility using aiosmtplib."""

from __future__ import annotations

import logging
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib
from fastapi import HTTPException, status

from app.core.config import settings

logger = logging.getLogger(__name__)


async def send_email_with_attachment(
    to_email: str,
    subject: str,
    body_html: str,
    attachment_bytes: bytes,
    attachment_filename: str,
) -> None:
    """
    Sends an email with a PDF attachment via SMTP.
    Raises HTTPException(503) if SMTP is not configured.
    Raises HTTPException(502) if the send fails.
    """
    if not settings.SMTP_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El envío de email no está configurado en el servidor.",
        )

    msg = MIMEMultipart("mixed")
    msg["From"] = settings.SMTP_FROM_EMAIL or settings.SMTP_USER
    msg["To"] = to_email
    msg["Subject"] = subject

    msg.attach(MIMEText(body_html, "html", "utf-8"))

    pdf_part = MIMEApplication(attachment_bytes, _subtype="pdf")
    pdf_part.add_header(
        "Content-Disposition", "attachment", filename=attachment_filename
    )
    msg.attach(pdf_part)

    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER,
            password=settings.SMTP_PASSWORD,
            use_tls=not settings.SMTP_USE_TLS,
            start_tls=settings.SMTP_USE_TLS,
        )
        logger.info("email.sent to=%s subject=%s", to_email, subject)
    except Exception as exc:
        logger.error("email.send_failed to=%s error=%s", to_email, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error al enviar el email: {exc}",
        ) from exc
