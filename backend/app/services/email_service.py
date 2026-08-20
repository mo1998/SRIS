"""
Email service for sending invitations and notifications.
Supports Resend (production) and Mailpit (development) providers.
"""

import logging
import time
from datetime import datetime
from html import escape
from typing import Dict, Optional, Protocol

import httpx

from app.config import settings
from app.metrics import record_email_result

logger = logging.getLogger("sris.email")


PLACEHOLDER_EMAIL_VALUES = {
    "",
    "noreply@yourdomain.com",
    "noreply@sris.com",
}

# Transient HTTP statuses worth retrying with backoff
RETRYABLE_STATUSES = {429, 500, 502, 503, 504}
SEND_RETRIES = 3
SEND_BACKOFF_SECONDS = 1.0
SEND_TIMEOUT_SECONDS = 15.0


class EmailProviderError(RuntimeError):
    """Raised when a configured email provider cannot send mail."""


class EmailProvider(Protocol):
    name: str

    def send(self, to_email: str, to_name: str, subject: str, html_content: str) -> None:
        ...


def _post_with_retry(url: str, headers: Dict[str, str], json_payload: dict) -> None:
    """POST a payload with bounded retries and exponential backoff on transient failures."""
    for attempt in range(SEND_RETRIES):
        try:
            resp = httpx.post(url, headers=headers, json=json_payload, timeout=SEND_TIMEOUT_SECONDS)
            resp.raise_for_status()
            return
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in RETRYABLE_STATUSES and attempt < SEND_RETRIES - 1:
                time.sleep(SEND_BACKOFF_SECONDS * (2 ** attempt))
                continue
            raise
        except httpx.TransportError:
            if attempt < SEND_RETRIES - 1:
                time.sleep(SEND_BACKOFF_SECONDS * (2 ** attempt))
                continue
            raise


class ResendEmailProvider:
    """Send email through the Resend HTTP API."""

    name = "resend"
    API_URL = "https://api.resend.com/emails"

    def send(self, to_email: str, to_name: str, subject: str, html_content: str) -> None:
        if not settings.RESEND_API_KEY:
            raise EmailProviderError("RESEND_API_KEY is not configured")
        payload = {
            "from": f"{settings.MAIL_FROM_NAME} <{settings.MAIL_FROM}>",
            "to": [to_email],
            "subject": subject,
            "html": html_content,
        }
        _post_with_retry(
            self.API_URL,
            {"Authorization": f"Bearer {settings.RESEND_API_KEY}"},
            payload,
        )


class MailpitEmailProvider:
    """Send email through the Mailpit HTTP API (development/testing)."""

    name = "mailpit"

    def send(self, to_email: str, to_name: str, subject: str, html_content: str) -> None:
        if not settings.MAILPIT_API_URL:
            raise EmailProviderError("MAILPIT_API_URL is not configured")
        payload = {
            "From": {"Email": settings.MAIL_FROM, "Name": settings.MAIL_FROM_NAME},
            "To": [{"Email": to_email, "Name": to_name}],
            "Subject": subject,
            "HTML": html_content,
        }
        _post_with_retry(settings.MAILPIT_API_URL, {}, payload)


class DisabledEmailProvider:
    """No-op provider used when email sending is explicitly disabled."""

    name = "disabled"

    def send(self, to_email: str, to_name: str, subject: str, html_content: str) -> None:
        logger.warning("Email provider is disabled — skipping send to %s", to_email)


def get_email_provider() -> EmailProvider:
    """Return the configured email provider instance."""
    provider = settings.EMAIL_PROVIDER.lower()
    if provider == "resend":
        return ResendEmailProvider()
    if provider == "mailpit":
        return MailpitEmailProvider()
    if provider == "disabled":
        return DisabledEmailProvider()
    raise EmailProviderError(f"Unknown EMAIL_PROVIDER: {settings.EMAIL_PROVIDER}")


def get_email_health() -> Dict[str, object]:
    missing_settings = []
    provider = get_email_provider()

    if provider.name == "resend" and not settings.RESEND_API_KEY:
        missing_settings.append("RESEND_API_KEY")
    if provider.name == "mailpit" and not settings.MAILPIT_API_URL:
        missing_settings.append("MAILPIT_API_URL")
    if provider.name != "disabled" and settings.MAIL_FROM in PLACEHOLDER_EMAIL_VALUES:
        missing_settings.append("MAIL_FROM")

    configured = provider.name != "disabled" and len(missing_settings) == 0
    status = (
        "disabled"
        if provider.name == "disabled"
        else ("configured" if configured else "configuration_incomplete")
    )
    mail_server, mail_port = _provider_endpoint(provider)
    return {
        "configured": configured,
        "status": status,
        "provider": provider.name,
        "mail_from": settings.MAIL_FROM,
        "mail_from_name": settings.MAIL_FROM_NAME,
        "mail_server": mail_server,
        "mail_port": mail_port,
        "missing_settings": missing_settings,
        "checked_at": datetime.utcnow(),
    }


def _provider_endpoint(provider: EmailProvider) -> tuple[str, int]:
    """Human-readable SMTP-style server/port for the active provider."""
    if provider.name == "resend":
        return "api.resend.com", 443
    if provider.name == "mailpit" and settings.MAILPIT_API_URL:
        from urllib.parse import urlparse

        parsed = urlparse(settings.MAILPIT_API_URL)
        return parsed.hostname or "", parsed.port or 80
    return "", 0


def render_invitation_email(
    candidate_name: str,
    interview_title: str,
    interview_link: str,
    expires_at: datetime,
    custom_message: Optional[str] = None,
) -> tuple[str, str]:
    """Render the invitation email subject and HTML body."""
    safe_candidate_name = escape(candidate_name)
    safe_interview_title = escape(interview_title)
    safe_interview_link = escape(interview_link)
    formatted_expiry = escape(expires_at.strftime('%B %d, %Y at %I:%M %p'))
    safe_custom_message = escape(custom_message).replace('\n', '<br>') if custom_message else None
    custom_message_html = f"""
            <div style="background-color: #eef6ff; padding: 16px; border-left: 4px solid #3498db; margin: 20px 0;">
                <p style="margin: 0; color: #2c3e50;">{safe_custom_message}</p>
            </div>
    """ if safe_custom_message else ""

    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f4f4f4;">
        <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            <h1 style="color: #2c3e50; margin-bottom: 20px;">Interview Invitation</h1>
            <p>Dear {safe_candidate_name},</p>
            <p>You have been invited to participate in a remote interview for the position related to: <strong>{safe_interview_title}</strong></p>
            {custom_message_html}

            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0;">
                <h3 style="color: #2c3e50; margin-top: 0;">Interview Details</h3>
                <p><strong>Interview:</strong> {safe_interview_title}</p>
                <p><strong>Valid Until:</strong> {formatted_expiry}</p>
            </div>

            <p style="margin: 20px 0;">Click the button below to start your interview:</p>

            <div style="text-align: center; margin: 30px 0;">
                <a href="{safe_interview_link}"
                   style="background-color: #3498db; color: white; padding: 15px 40px; text-decoration: none; border-radius: 5px; font-size: 16px; font-weight: bold;">
                    Start Interview
                </a>
            </div>

            <p style="color: #7f8c8d; font-size: 14px;">Or copy and paste this link into your browser:</p>
            <p style="color: #3498db; word-break: break-all; font-size: 12px;">{safe_interview_link}</p>

            <hr style="border: none; border-top: 1px solid #ecf0f1; margin: 30px 0;">
            <p style="color: #7f8c8d; font-size: 12px;">
                This interview is conducted by an AI system. Please ensure you have:
            </p>
            <ul style="color: #7f8c8d; font-size: 12px;">
                <li>A stable internet connection</li>
                <li>A working microphone and camera</li>
                <li>A quiet environment with good lighting</li>
                <li>Your face clearly visible</li>
            </ul>

            <p style="color: #7f8c8d; font-size: 12px; margin-top: 20px;">
                If you have any questions, please contact the employer directly.
            </p>
        </div>
    </body>
    </html>
    """

    return f"Interview Invitation - {interview_title}", html_content


def _send_email(
    to_email: str,
    to_name: str,
    subject: str,
    html_content: str,
) -> None:
    provider = get_email_provider()
    try:
        provider.send(to_email, to_name, subject, html_content)
        if provider.name != "disabled":
            record_email_result(provider.name, ok=True)
    except Exception:
        if provider.name != "disabled":
            record_email_result(provider.name, ok=False)
        raise


async def send_invitation_email(
    to_email: str,
    candidate_name: str,
    interview_title: str,
    interview_link: str,
    expires_at: datetime,
    custom_message: Optional[str] = None,
):
    """Send interview invitation email via the configured provider."""
    health = get_email_health()
    if not health["configured"]:
        logger.warning("Email provider not configured — skipping send to %s", to_email)
        return

    subject, html_content = render_invitation_email(
        candidate_name=candidate_name,
        interview_title=interview_title,
        interview_link=interview_link,
        expires_at=expires_at,
        custom_message=custom_message,
    )

    try:
        _send_email(to_email, candidate_name, subject, html_content)
        logger.info("Invitation email sent to %s via configured provider", to_email)
    except Exception as e:
        logger.error("Error sending invitation to %s: %s", to_email, e)


def render_reminder_email(
    candidate_name: str,
    interview_title: str,
    interview_link: str,
    expires_at: datetime,
    reminder_number: int,
) -> tuple[str, str]:
    """Render a reminder email for an invitation not yet accepted."""
    safe_candidate_name = escape(candidate_name)
    safe_interview_title = escape(interview_title)
    safe_interview_link = escape(interview_link)
    formatted_expiry = escape(expires_at.strftime('%B %d, %Y at %I:%M %p'))
    expiry_note = (
        f"This is your final reminder — the invitation expires {formatted_expiry}."
        if reminder_number >= 2
        else f"The invitation is still valid until {formatted_expiry}."
    )

    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f4f4f4;">
        <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            <h1 style="color: #2c3e50; margin-bottom: 20px;">Friendly Reminder</h1>
            <p>Dear {safe_candidate_name},</p>
            <p>We noticed you haven't started your remote interview for <strong>{safe_interview_title}</strong> yet.</p>
            <p style="color: #e67e22;">{expiry_note}</p>

            <p style="margin: 20px 0;">Click the button below to start your interview:</p>

            <div style="text-align: center; margin: 30px 0;">
                <a href="{safe_interview_link}"
                   style="background-color: #3498db; color: white; padding: 15px 40px; text-decoration: none; border-radius: 5px; font-size: 16px; font-weight: bold;">
                    Start Interview
                </a>
            </div>

            <p style="color: #7f8c8d; font-size: 14px;">Or copy and paste this link into your browser:</p>
            <p style="color: #3498db; word-break: break-all; font-size: 12px;">{safe_interview_link}</p>

            <hr style="border: none; border-top: 1px solid #ecf0f1; margin: 30px 0;">
            <p style="color: #7f8c8d; font-size: 12px;">
                If you already completed your interview, please ignore this message.
            </p>
        </div>
    </body>
    </html>
    """

    return f"Reminder: Your Interview Invitation - {interview_title}", html_content


async def send_reminder_email(
    to_email: str,
    candidate_name: str,
    interview_title: str,
    interview_link: str,
    expires_at: datetime,
    reminder_number: int,
):
    """Send an invitation reminder email via the configured provider."""
    health = get_email_health()
    if not health["configured"]:
        logger.warning("Email provider not configured — skipping reminder to %s", to_email)
        return

    subject, html_content = render_reminder_email(
        candidate_name=candidate_name,
        interview_title=interview_title,
        interview_link=interview_link,
        expires_at=expires_at,
        reminder_number=reminder_number,
    )

    try:
        _send_email(to_email, candidate_name, subject, html_content)
        logger.info("Reminder email sent to %s via configured provider", to_email)
    except Exception as e:
        logger.error("Error sending reminder to %s: %s", to_email, e)


def send_reminder_email_sync(
    to_email: str,
    candidate_name: str,
    interview_title: str,
    interview_link: str,
    expires_at: datetime,
    reminder_number: int,
) -> bool:
    """Synchronous reminder send for background maintenance jobs."""
    health = get_email_health()
    if not health["configured"]:
        logger.warning("Email provider not configured — skipping reminder to %s", to_email)
        return False

    subject, html_content = render_reminder_email(
        candidate_name=candidate_name,
        interview_title=interview_title,
        interview_link=interview_link,
        expires_at=expires_at,
        reminder_number=reminder_number,
    )

    try:
        _send_email(to_email, candidate_name, subject, html_content)
        logger.info("Reminder email sent to %s via configured provider", to_email)
        return True
    except Exception as e:
        logger.error("Error sending reminder to %s: %s", to_email, e)
        return False


async def send_completion_email(
    to_email: str,
    candidate_name: str,
    interview_title: str,
    score: float,
    passed: bool,
    results_link: str = "",
):
    """Send interview completion email with results via the configured provider."""
    health = get_email_health()
    if not health["configured"]:
        logger.warning("Email provider not configured — skipping completion email to %s", to_email)
        return

    result_text = "passed" if passed else "did not pass"
    safe_candidate_name = escape(candidate_name)
    safe_interview_title = escape(interview_title)
    safe_results_link = escape(results_link)
    results_html = (
        f'<p><a href="{safe_results_link}" style="display: inline-block; padding: 10px 20px; '
        f'background-color: #3498db; color: white; text-decoration: none; border-radius: 5px;">View Detailed Results</a></p>'
        if results_link else ""
    )
    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f4f4f4;">
        <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            <h1 style="color: #2c3e50;">Interview Completed!</h1>
            <p>Dear {safe_candidate_name},</p>
            <p>Thank you for completing your interview for <strong>{safe_interview_title}</strong></p>

            <div style="background-color: {'#d4edda' if passed else '#f8d7da'}; padding: 20px; border-radius: 5px; margin: 20px 0;">
                <h3 style="color: {'#155724' if passed else '#721c24'}; margin-top: 0;">Results</h3>
                <p style="font-size: 18px;"><strong>Score:</strong> {score:.1f}%</p>
                <p style="font-size: 18px;"><strong>Status:</strong> You {result_text} the interview</p>
            </div>

            {results_html}

            <p>A detailed report has been shared with the employer. They will review your performance and contact you if you move forward in the process.</p>

            <p style="margin-top: 30px;">Best of luck!</p>
        </div>
    </body>
    </html>
    """

    try:
        _send_email(to_email, candidate_name, subject=f"Interview Results - {interview_title}", html_content=html_content)
        logger.info("Completion email sent to %s via configured provider", to_email)
    except Exception as e:
        logger.error("Error sending completion to %s: %s", to_email, e)


def render_password_reset_email(
    reset_link: str,
    expires_minutes: int,
) -> tuple[str, str]:
    """Render the password reset confirmation email subject and HTML body."""
    safe_reset_link = escape(reset_link)
    formatted_expiry = escape(f"{expires_minutes} minutes")

    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f4f4f4;">
        <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            <h1 style="color: #2c3e50; margin-bottom: 20px;">Password Reset</h1>
            <p>We received a request to reset your password.</p>
            <p>Click the button below to choose a new password. This link is valid for <strong>{formatted_expiry}</strong>.</p>

            <div style="text-align: center; margin: 30px 0;">
                <a href="{safe_reset_link}"
                   style="background-color: #3498db; color: white; padding: 15px 40px; text-decoration: none; border-radius: 5px; font-size: 16px; font-weight: bold;">
                    Reset Password
                </a>
            </div>

            <p style="color: #7f8c8d; font-size: 14px;">Or copy and paste this link into your browser:</p>
            <p style="color: #3498db; word-break: break-all; font-size: 12px;">{safe_reset_link}</p>

            <hr style="border: none; border-top: 1px solid #ecf0f1; margin: 30px 0;">
            <p style="color: #7f8c8d; font-size: 12px;">
                If you did not request a password reset, you can safely ignore this email.
            </p>
        </div>
    </body>
    </html>
    """

    return "Reset Your SRIS Password", html_content


async def send_password_reset_email(to_email: str, reset_link: str):
    """Send a password reset email via the configured provider."""
    health = get_email_health()
    if not health["configured"]:
        logger.warning("Email provider not configured — skipping password reset to %s", to_email)
        return

    subject, html_content = render_password_reset_email(
        reset_link=reset_link,
        expires_minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES,
    )

    try:
        _send_email(to_email, to_email, subject, html_content)
        logger.info("Password reset email sent to %s via configured provider", to_email)
    except Exception as e:
        logger.error("Error sending password reset to %s: %s", to_email, e)
