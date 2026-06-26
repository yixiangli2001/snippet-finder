"""Outbound email for account-lifecycle messages (verify, reset).

Sends through Resend's HTTP API when RESEND_API_KEY is set. Otherwise it
prints the message to the console — lets the verify/reset flows be built,
tested, and demoed locally without signing up for an email provider.
"""

import os

import httpx
from dotenv import load_dotenv

load_dotenv()

RESEND_API_KEY = os.getenv("RESEND_API_KEY")
FROM_EMAIL = os.getenv("FROM_EMAIL", "Snippet Finder <onboarding@resend.dev>")


def send_email(to: str, subject: str, html: str) -> None:
    if not RESEND_API_KEY:
        print(f"\n--- DEV EMAIL ---\nTo: {to}\nSubject: {subject}\n{html}\n-----------------\n")
        return

    response = httpx.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {RESEND_API_KEY}"},
        json={"from": FROM_EMAIL, "to": [to], "subject": subject, "html": html},
        timeout=10,
    )
    response.raise_for_status()


def send_verification_email(to: str, link: str) -> None:
    send_email(
        to,
        "Verify your Snippet Finder email",
        f"<p>Click the link below to verify your account:</p>"
        f'<p><a href="{link}">{link}</a></p>'
        f"<p>This link expires in 24 hours.</p>",
    )


def send_reset_email(to: str, link: str) -> None:
    send_email(
        to,
        "Reset your Snippet Finder password",
        f"<p>Click the link below to reset your password:</p>"
        f'<p><a href="{link}">{link}</a></p>'
        f"<p>This link expires in 1 hour. If you did not request this, you can ignore this email.</p>",
    )
