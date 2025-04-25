"""
core/email.py

Handles sending emails for:
- Email verification (initial)
- Welcome email after account activation
- Password reset requests
- New email address verification
- Email change notifications (optional)
"""

import logging
from datetime import datetime
from typing import Any
from fastapi import HTTPException
from fastapi_mail import FastMail, MessageSchema, MessageType
from pydantic import EmailStr

from app.core.email_config import conf
from app.core.config import settings

logger = logging.getLogger(__name__)


async def _send_email(
    to_email: EmailStr, subject: str, template_name: str, template_body: dict[str, Any]
) -> None:
    """Internal helper function to send emails using FastAPI-Mail."""
    if not all(
        [
            settings.MAIL_USERNAME,
            settings.MAIL_PASSWORD,
            settings.MAIL_FROM,
            settings.MAIL_SERVER,
        ]
    ):
        logger.error("Mail server settings are not fully configured. Cannot send email.")
        raise HTTPException(status_code=500, detail="Email service not configured")

    # Add common template variables
    template_body.setdefault("year", datetime.now().year)
    template_body.setdefault("company_name", settings.MAIL_FROM_NAME or "Laborly")

    message = MessageSchema(
        subject=subject,
        recipients=[to_email],
        template_body=template_body,
        subtype=MessageType.html,
    )

    fm = FastMail(conf)
    try:
        await fm.send_message(message, template_name=template_name)
        logger.info(
            f"Email '{subject}' sent successfully to {to_email} using template {template_name}"
        )
    except Exception as e:
        logger.error(f"Failed to send email '{subject}' to {to_email}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send email: {e}")


async def send_email_verification(to_email: EmailStr, token: str) -> None:
    """
    Sends an email verification link to the user's email address (initial registration).
    """
    # Construct verification URL using the correct endpoint from routes.py
    verify_url = f"{settings.BACKEND_URL}/auth/verify-initial-email?token={token}"
    subject = f"Verify Your Email - {settings.MAIL_FROM_NAME or 'Laborly'}"
    template_data = {
        "verification_link": verify_url,
        "verification_code": token,
        "account_verification_ttl_min": settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES or 30,
    }
    await _send_email(
        to_email=to_email,
        subject=subject,
        template_name="verification.html",
        template_body=template_data,
    )


async def send_welcome_email(to_email: EmailStr, first_name: str) -> None:
    """
    Sends a welcome email after successful account verification.
    """
    subject = f"Welcome to {settings.MAIL_FROM_NAME or 'Laborly'} 🎉"
    template_data = {
        "first_name": first_name,
        # Temp
        "login_url": f"{settings.BACKEND_URL}",
    }
    await _send_email(
        to_email=to_email,
        subject=subject,
        template_name="welcome.html",
        template_body=template_data,
    )


async def send_password_reset_email(to_email: EmailStr, token: str) -> None:
    """
    Sends a password reset link to the user's email address.
    """
    # Temp
    reset_url = f"{settings.BACKEND_URL}/reset-password?token={token}"
    subject = f"Reset Your Password - {settings.MAIL_FROM_NAME or 'Laborly'}"
    template_data = {
        "reset_link": reset_url,
        "password_reset_ttl_min": settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES or 60,
    }
    await _send_email(
        to_email=to_email,
        subject=subject,
        template_name="password_reset.html",
        template_body=template_data,
    )


async def send_new_email_verification(new_email: EmailStr, token: str) -> None:
    """
    Sends a verification link to the *new* email address during an update process.
    """
    # Temp
    verify_url = f"{settings.BACKEND_URL}/auth/verify-new-email?token={token}"
    subject = f"Confirm Your New Email Address - {settings.MAIL_FROM_NAME or 'Laborly'}"
    template_data = {
        "verification_link": verify_url,
        "new_email": new_email,
        "new_email_verification_ttl_min": (
            settings.NEW_EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES or 1440
        ),
    }
    await _send_email(
        to_email=new_email,
        subject=subject,
        template_name="new_email_verification.html",
        template_body=template_data,
    )


async def send_email_change_notification(old_email: EmailStr, new_email: EmailStr) -> None:
    """
    (Optional) Sends a notification to the user's *old* email address
    informing them that an email change was requested or completed.
    """
    subject = f"Email Address Change Notification - {settings.MAIL_FROM_NAME or 'Laborly'}"
    template_data = {
        "old_email": old_email,
        "new_email": new_email,
        "support_email": settings.SUPPORT_EMAIL or "support@example.com",
    }
    await _send_email(
        to_email=old_email,
        subject=subject,
        template_name="email_change_notification.html",
        template_body=template_data,
    )


async def send_password_reset_confirmation(to_email: EmailStr) -> None:
    """
    Sends a confirmation email after a password has been successfully reset.
    """
    subject = f"Your Password Has Been Reset - {settings.MAIL_FROM_NAME or 'Laborly'}"
    template_data = {
        # Temp
        "login_url": f"{settings.BACKEND_URL}",
        "support_email": settings.SUPPORT_EMAIL or "support@example.com",
    }
    await _send_email(
        to_email=to_email,
        subject=subject,
        template_name="password_reset_confirmation.html",
        template_body=template_data,
    )


async def send_new_email_confirmed(to_email: EmailStr) -> None:
    """
    Sends a confirmation email to the new email address after it has been verified.
    """
    subject = f"Your Email Address Has Been Updated - {settings.MAIL_FROM_NAME or 'Laborly'}"
    template_data = {
        "new_email": to_email,
        # Temp
        "profile_url": f"{settings.BACKEND_URL}",
    }
    await _send_email(
        to_email=to_email,
        subject=subject,
        template_name="new_email_confirmed.html",
        template_body=template_data,
    )
