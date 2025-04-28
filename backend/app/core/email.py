"""
backend/app/core/email.py

Email Sending Utilities

Handles sending transactional emails for:
- Email verification
- Welcome email after account activation
- Password reset
- New email verification
- Email change notifications
"""

import logging
from datetime import datetime
from typing import Any

from fastapi import HTTPException
from fastapi_mail import FastMail, MessageSchema, MessageType
from pydantic import EmailStr

from app.core.config import settings
from app.core.email_config import conf

# ---------------------------------------------------
# Logger Configuration
# ---------------------------------------------------
logger = logging.getLogger(__name__)


# ---------------------------------------------------
# Internal Email Sender
# ---------------------------------------------------
async def _send_email(
    to_email: EmailStr,
    subject: str,
    template_name: str,
    template_body: dict[str, Any],
) -> None:
    """
    Internal helper function to send emails using FastAPI-Mail.
    """
    if not all(
        [
            settings.MAIL_USERNAME,
            settings.MAIL_PASSWORD,
            settings.MAIL_FROM,
            settings.MAIL_SERVER,
        ]
    ):
        logger.error("[EMAIL] Incomplete mail server settings. Cannot send email.")
        raise HTTPException(
            status_code=500,
            detail="Email service not configured",
        )

    # Add default template variables
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
        logger.info(f"[EMAIL] Sent '{subject}' to {to_email} (template={template_name})")
    except Exception as e:
        logger.error(f"[EMAIL] Failed to send '{subject}' to {to_email}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send email: {e}",
        )


# ---------------------------------------------------
# Public Email Sending Functions
# ---------------------------------------------------
async def send_email_verification(to_email: EmailStr, token: str) -> None:
    """
    Send an email verification link to a user's email during registration.
    """
    verify_url = f"{settings.BASE_URL}/auth/verify-email?token={token}"
    subject = f"Verify Your Email - {settings.MAIL_FROM_NAME or 'Laborly'}"
    template_data = {
        "verification_link": verify_url,
        "verification_code": token,
        "account_verification_ttl_min": settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES,
    }
    await _send_email(to_email, subject, "verification.html", template_data)


async def send_welcome_email(to_email: EmailStr, first_name: str) -> None:
    """
    Send a welcome email after successful account activation.
    """
    subject = f"Welcome to {settings.MAIL_FROM_NAME or 'Laborly'} 🎉"
    template_data = {
        "first_name": first_name,
        "login_url": f"{settings.BASE_URL}",
    }
    await _send_email(to_email, subject, "welcome.html", template_data)


async def send_password_reset_email(to_email: EmailStr, token: str) -> None:
    """
    Send a password reset link to the user's email address.
    """
    reset_url = f"{settings.BASE_URL}/reset-password?token={token}"
    subject = f"Reset Your Password - {settings.MAIL_FROM_NAME or 'Laborly'}"
    template_data = {
        "reset_link": reset_url,
        "password_reset_ttl_min": settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES,
    }
    await _send_email(to_email, subject, "password_reset.html", template_data)


async def send_new_email_verification(new_email: EmailStr, token: str) -> None:
    """
    Send a verification link to a new email address during email update process.
    """
    verify_url = f"{settings.BASE_URL}/auth/verify-new-email?token={token}"
    subject = f"Confirm Your New Email Address - {settings.MAIL_FROM_NAME or 'Laborly'}"
    template_data = {
        "verification_link": verify_url,
        "new_email": new_email,
        "new_email_verification_ttl_min": (settings.NEW_EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES,),
    }
    await _send_email(new_email, subject, "new_email_verification.html", template_data)


async def send_email_change_notification(old_email: EmailStr, new_email: EmailStr) -> None:
    """
    Send a notification to the user's old email after email change request.
    """
    subject = f"Email Address Change Notification - {settings.MAIL_FROM_NAME or 'Laborly'}"
    template_data = {
        "old_email": old_email,
        "new_email": new_email,
        "support_email": settings.SUPPORT_EMAIL or "support@example.com",
    }
    await _send_email(old_email, subject, "email_change_notification.html", template_data)


async def send_password_reset_confirmation(to_email: EmailStr) -> None:
    """
    Send a confirmation email after a successful password reset.
    """
    subject = f"Your Password Has Been Reset - {settings.MAIL_FROM_NAME or 'Laborly'}"
    template_data = {
        "login_url": f"{settings.BASE_URL}",
        "support_email": settings.SUPPORT_EMAIL or "support@example.com",
    }
    await _send_email(to_email, subject, "password_reset_confirmation.html", template_data)


async def send_new_email_confirmed(to_email: EmailStr) -> None:
    """
    Send a confirmation email to the user's new email after it has been verified.
    """
    subject = f"Your Email Address Has Been Updated - {settings.MAIL_FROM_NAME or 'Laborly'}"
    template_data = {
        "new_email": to_email,
        "profile_url": f"{settings.BASE_URL}",
    }
    await _send_email(to_email, subject, "new_email_confirmed.html", template_data)
