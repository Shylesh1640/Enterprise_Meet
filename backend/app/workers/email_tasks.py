"""Enterprise Meet — Email tasks (Celery)."""

from __future__ import annotations

import logging
from typing import Optional

from celery import Task

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def _get_smtp_connection():
    """Create an SMTP connection using configured settings."""
    import smtplib
    from app.core.config import settings

    if settings.SMTP_SSL:
        conn = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT)
    else:
        conn = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
        if settings.SMTP_TLS:
            conn.starttls()

    if settings.SMTP_USER and settings.SMTP_PASSWORD:
        conn.login(settings.SMTP_USER, settings.SMTP_PASSWORD)

    return conn


def _send_email(to: str, subject: str, html_body: str) -> None:
    """Send an HTML email via SMTP."""
    import email.mime.multipart
    import email.mime.text
    from app.core.config import settings

    msg = email.mime.multipart.MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM}>"
    msg["To"] = to
    msg.attach(email.mime.text.MIMEText(html_body, "html"))

    with _get_smtp_connection() as conn:
        conn.sendmail(settings.SMTP_FROM, [to], msg.as_string())


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def send_verification_email(
    self: Task, user_id: str, email: str, first_name: str, token: str
) -> None:
    """Send email verification link to new user."""
    from app.core.config import settings

    verify_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"
    html = f"""
    <h2>Welcome to Enterprise Meet, {first_name}!</h2>
    <p>Please verify your email address by clicking the link below:</p>
    <a href="{verify_url}" style="
        background:#4F46E5;color:white;padding:12px 24px;border-radius:6px;
        text-decoration:none;display:inline-block;
    ">Verify Email</a>
    <p>This link expires in 24 hours.</p>
    <p>If you didn't register, please ignore this email.</p>
    """
    try:
        _send_email(email, "Verify your Enterprise Meet account", html)
        logger.info(f"Verification email sent to {email}")
    except Exception as exc:
        logger.error(f"Failed to send verification email to {email}: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def send_password_reset_email(
    self: Task, email: str, first_name: str, token: str
) -> None:
    """Send password reset link."""
    from app.core.config import settings

    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    html = f"""
    <h2>Reset your password, {first_name}</h2>
    <p>Click the link below to reset your password. This link expires in 1 hour.</p>
    <a href="{reset_url}" style="
        background:#EF4444;color:white;padding:12px 24px;border-radius:6px;
        text-decoration:none;display:inline-block;
    ">Reset Password</a>
    <p>If you didn't request this, please ignore this email.</p>
    """
    try:
        _send_email(email, "Reset your Enterprise Meet password", html)
        logger.info(f"Password reset email sent to {email}")
    except Exception as exc:
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def send_meeting_invitation_email(
    self: Task, email: str, meeting_title: str, meeting_code: str
) -> None:
    """Send meeting invitation to a non-user via email."""
    from app.core.config import settings

    join_url = f"{settings.FRONTEND_URL}/join/{meeting_code}"
    html = f"""
    <h2>You've been invited to a meeting!</h2>
    <p><strong>{meeting_title}</strong></p>
    <p>Meeting Code: <code>{meeting_code}</code></p>
    <a href="{join_url}" style="
        background:#10B981;color:white;padding:12px 24px;border-radius:6px;
        text-decoration:none;display:inline-block;
    ">Join Meeting</a>
    """
    try:
        _send_email(email, f"Invitation: {meeting_title}", html)
    except Exception as exc:
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def send_meeting_reminder_email(
    self: Task,
    email: str,
    first_name: str,
    meeting_title: str,
    meeting_code: str,
    starts_in_minutes: int,
) -> None:
    """Send meeting reminder email."""
    from app.core.config import settings

    join_url = f"{settings.FRONTEND_URL}/join/{meeting_code}"
    html = f"""
    <h2>Reminder: {meeting_title} starts in {starts_in_minutes} minutes</h2>
    <p>Hi {first_name},</p>
    <p>Your meeting is starting soon.</p>
    <a href="{join_url}" style="
        background:#4F46E5;color:white;padding:12px 24px;border-radius:6px;
        text-decoration:none;display:inline-block;
    ">Join Meeting</a>
    """
    try:
        _send_email(email, f"Reminder: {meeting_title} starts in {starts_in_minutes}min", html)
    except Exception as exc:
        raise self.retry(exc=exc)
