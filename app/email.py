"""Transactional email via Resend (https://resend.com).

Chosen over SendGrid for setup simplicity: one API key, one HTTP POST, no
sender-identity SDK boilerplate. A blank RESEND_API_KEY doesn't error — it
just logs the email to the console, so password reset is testable locally
without a Resend account.
"""

from __future__ import annotations

import httpx

from app.config import get_settings

RESEND_API_URL = "https://api.resend.com/emails"


async def send_password_reset_email(to: str, reset_url: str) -> None:
    settings = get_settings()
    subject = "Reset your Supasift password"
    html = (
        "<p>Someone requested a password reset for this Supasift account.</p>"
        f'<p><a href="{reset_url}">Reset your password</a></p>'
        "<p>This link expires in 1 hour and can only be used once. If you "
        "didn't request this, you can safely ignore this email.</p>"
    )

    if not settings.resend_api_key:
        print(f"[email] RESEND_API_KEY not set — would send to {to}: {reset_url}")
        return

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                RESEND_API_URL,
                headers={"Authorization": f"Bearer {settings.resend_api_key}"},
                json={
                    "from": settings.email_from,
                    "to": [to],
                    "subject": subject,
                    "html": html,
                },
            )
        if response.status_code >= 400:
            print(f"[email] Resend {response.status_code} sending to {to}: {response.text}")
    except httpx.HTTPError as exc:
        # Never let an email provider outage surface as a 500 to the client —
        # forgot-password always returns its generic response regardless.
        print(f"[email] failed to send to {to}: {exc}")
