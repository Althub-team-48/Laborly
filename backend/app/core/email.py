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
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pydantic import EmailStr
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import From, Mail, To

from app.core.config import settings

# Logger configuration
logger = logging.getLogger(__name__)

# Jinja2 template environment setup
jinja_env: Environment | None = None
try:
    template_dir = settings.mail_templates_path
    if not template_dir.is_dir():
        logger.error(f"Template directory not found: {template_dir}")
        raise FileNotFoundError(f"Email template directory not found: {template_dir}")

    jinja_env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape(["html", "xml"]),
    )
    logger.info(f"Jinja2 environment initialized with templates in: {template_dir}")
except Exception:
    logger.exception("Failed to initialize Jinja2 environment")
    jinja_env = None


def _render_template(template_name: str, context: dict[str, Any]) -> str:
    """
    Renders an email template using Jinja2 with provided context.
    Args:
        template_name (str): Name of the template file.
        context (dict[str, Any]): Variables to pass to the template.
    Returns:
        str: Rendered HTML content.
    """
    if not jinja_env:
        logger.error("Jinja2 environment not available")
        raise RuntimeError("Email template environment not initialized")

    try:
        template = jinja_env.get_template(template_name)
        full_context = {
            "year": datetime.now().year,
            "company_name": settings.MAIL_FROM_NAME or settings.APP_NAME,
            "app_name": settings.APP_NAME,
            "base_url": str(settings.BASE_URL).rstrip("/"),
            "support_email": str(settings.SUPPORT_EMAIL),
            **context,
        }
        rendered_content = template.render(full_context)
        logger.debug(f"Successfully rendered template: {template_name}")
        return rendered_content
    except Exception as e:
        logger.error(f"Failed to render template '{template_name}': {str(e)}")
        raise ValueError(f"Failed to render email template {template_name}") from e


async def _send_email(to_email: EmailStr, subject: str, html_content: str) -> None:
    """
    Sends an email using SendGrid API.
    Args:
        to_email (EmailStr): Recipient's email address.
        subject (str): Email subject line.
        html_content (str): HTML content of the email.
    """
    if not settings.EMAILS_ENABLED:
        logger.warning(
            f"Email sending disabled. Skipping send to {to_email} for subject '{subject}'"
        )
        return

    if not all([settings.SENDGRID_API_KEY, settings.MAIL_FROM]):
        logger.error("SendGrid API Key or MAIL_FROM setting is missing")
        raise HTTPException(status_code=500, detail="Email service configuration missing")

    from_email = From(
        email=str(settings.MAIL_FROM), name=settings.MAIL_FROM_NAME or settings.APP_NAME
    )
    to_emails = To(str(to_email))
    message = Mail(
        from_email=from_email,
        to_emails=to_emails,
        subject=subject,
        html_content=html_content,
    )

    try:
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        response = sg.client.mail.send.post(request_body=message.get())
        logger.info(
            f"Email sent to {to_email} for subject '{subject}' with status code {response.status_code}"
        )

        if response.status_code >= 300:
            logger.error(f"SendGrid API error: Status={response.status_code}, Body={response.body}")
            raise HTTPException(status_code=500, detail="Failed to send email via provider")
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {str(e)}")
        raise HTTPException(
            status_code=500, detail="An unexpected error occurred while sending the email"
        )


async def send_email_verification(
    to_email: EmailStr, token: str, first_name: str | None = None
) -> None:
    """
    Sends an email verification link to the user.
    Args:
        to_email (EmailStr): Recipient's email address.
        token (str): Verification token.
    """
    base_url_str = str(settings.BASE_URL).rstrip("/")
    subject = f"Verify Your Email - {settings.MAIL_FROM_NAME or settings.APP_NAME}"
    context = {
        "verification_link": f"{base_url_str}/auth/verify-email?token={token}",
        "verification_code": token,
        "account_verification_ttl_min": settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES,
        "first_name": first_name,
    }
    html_content = _render_template("verification.html", context)
    await _send_email(to_email, subject, html_content)
    logger.info(f"Email verification sent to {to_email}")


async def send_welcome_email(to_email: EmailStr, first_name: str) -> None:
    """
    Sends a welcome email to a newly activated user.
    Args:
        to_email (EmailStr): Recipient's email address.
        first_name (str): User's first name.
    """
    base_url_str = str(settings.BASE_URL).rstrip("/")
    subject = f"Welcome to {settings.MAIL_FROM_NAME or settings.APP_NAME}"
    context = {
        "first_name": first_name,
        "login_url": f"{base_url_str}/auth/login",
    }
    html_content = _render_template("welcome.html", context)
    await _send_email(to_email, subject, html_content)
    logger.info(f"Welcome email sent to {to_email}")


async def send_password_reset_email(
    to_email: EmailStr, token: str, first_name: str | None = None
) -> None:
    """
    Sends a password reset link to the user.
    Args:
        to_email (EmailStr): Recipient's email address.
        token (str): Password reset token.
    """
    base_url_str = str(settings.BASE_URL).rstrip("/")
    subject = f"Reset Your Password - {settings.MAIL_FROM_NAME or settings.APP_NAME}"
    context = {
        "reset_link": f"{base_url_str}/auth/reset-password?token={token}",
        "password_reset_ttl_min": settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES,
        "first_name": first_name,
    }
    html_content = _render_template("password_reset.html", context)
    await _send_email(to_email, subject, html_content)
    logger.info(f"Password reset email sent to {to_email}")


async def send_new_email_verification(new_email: EmailStr, token: str, first_name: str) -> None:
    """
    Sends a verification link for a new email address.
    Args:
        new_email (EmailStr): New email address to verify.
        token (str): Verification token.
    """
    base_url_str = str(settings.BASE_URL).rstrip("/")
    subject = f"Confirm Your New Email Address - {settings.MAIL_FROM_NAME or settings.APP_NAME}"
    context = {
        "verification_link": f"{base_url_str}/auth/verify-new-email?token={token}",
        "new_email": new_email,
        "new_email_verification_ttl_min": settings.NEW_EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES,
        "first_name": first_name,
    }
    html_content = _render_template("new_email_verification.html", context)
    await _send_email(new_email, subject, html_content)
    logger.info(f"New email verification sent to {new_email}")


async def send_email_change_notification(
    old_email: EmailStr, new_email: EmailStr, first_name: str
) -> None:
    """
    Notifies the old email address of an email change.
    Args:
        old_email (EmailStr): Previous email address.
        new_email (EmailStr): New email address.
    """
    subject = f"Email Address Change Notification - {settings.MAIL_FROM_NAME or settings.APP_NAME}"
    context = {
        "old_email": old_email,
        "new_email": new_email,
        "first_name": first_name,
    }
    html_content = _render_template("email_change_notification.html", context)
    await _send_email(old_email, subject, html_content)
    logger.info(f"Email change notification sent to {old_email}")


async def send_password_reset_confirmation(to_email: EmailStr, first_name: str) -> None:
    """
    Sends a confirmation email after a password reset.
    Args:
        to_email (EmailStr): Recipient's email address.
    """
    base_url_str = str(settings.BASE_URL).rstrip("/")
    subject = f"Your Password Has Been Reset - {settings.MAIL_FROM_NAME or settings.APP_NAME}"
    context = {
        "login_url": f"{base_url_str}/auth/login",
        "first_name": first_name,
    }
    html_content = _render_template("password_reset_confirmation.html", context)
    await _send_email(to_email, subject, html_content)
    logger.info(f"Password reset confirmation sent to {to_email}")


async def send_new_email_confirmed(to_email: EmailStr, first_name: str) -> None:
    """
    Sends a confirmation to the new email address after update.
    Args:
        to_email (EmailStr): New email address.
    """
    base_url_str = str(settings.BASE_URL).rstrip("/")
    subject = (
        f"Your Email Address Has Been Updated - {settings.MAIL_FROM_NAME or settings.APP_NAME}"
    )
    context = {
        "new_email": to_email,
        "profile_url": f"{base_url_str}/auth/profile",
        "first_name": first_name,
    }
    html_content = _render_template("new_email_confirmed.html", context)
    await _send_email(to_email, subject, html_content)
    logger.info(f"New email confirmation sent to {to_email}")


async def send_final_change_notification_to_old_email(
    old_email: EmailStr, new_email: EmailStr, first_name: str | None = None
) -> None:
    """
    Notifies the old email address that the email change is complete.
    Args:
        old_email (EmailStr): The previous email address.
        new_email (EmailStr): The new email address that is now active.
        first_name (str | None): User's first name for personalization.
    """
    subject = f"Email Address Changed - {settings.MAIL_FROM_NAME or settings.APP_NAME}"
    context = {
        "old_email": old_email,
        "new_email": new_email,
        "first_name": first_name,
    }
    html_content = _render_template("final_email_change_notice_to_old.html", context)
    await _send_email(old_email, subject, html_content)
    logger.info(f"Final email change notification sent to old address {old_email}")
