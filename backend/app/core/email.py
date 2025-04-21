"""
core/email.py

Handles sending emails for:
- Email verification
- Welcome email after account activation
"""

from datetime import datetime
from fastapi_mail import FastMail, MessageSchema, MessageType

from app.core.email_config import conf
from app.core.config import settings


async def send_email_verification(to_email: str, token: str) -> None:
    """
    Sends an email verification link to the user's email address.
    """
    fm = FastMail(conf)
    verify_url = f"{settings.BASE_URL}/auth/verify-email?token={token}"

    template_data = {
        "verification_link": verify_url,
        "verification_code": token,
        "account_verification_ttl_min": 5,
        "year": datetime.now().year,
    }

    message = MessageSchema(
        subject="Verify Your Email - Laborly",
        recipients=[to_email],
        template_body=template_data,
        subtype=MessageType.html,
    )

    await fm.send_message(message, template_name="verification.html")


async def send_welcome_email(to_email: str, first_name: str) -> None:
    """
    Sends a welcome email after successful account verification.
    """
    fm = FastMail(conf)

    template_data = {
        "first_name": first_name,
        "year": datetime.now().year,
    }

    message = MessageSchema(
        subject="Welcome to Laborly 🎉",
        recipients=[to_email],
        template_body=template_data,
        subtype=MessageType.html,
    )

    await fm.send_message(message, template_name="welcome.html")
