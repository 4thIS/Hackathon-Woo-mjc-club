"""메일 발송. **실패해도 서버가 죽지 않는다** (backend/CLAUDE.md 규칙).

SMTP 설정이 없거나 발송이 실패하면 콘솔에 내용을 출력한다. 시연 중 메일이
안 가는 것보다 인증 링크를 터미널에서 복사할 수 있는 편이 낫다.
"""

import logging
import smtplib
from email.message import EmailMessage

from ..config import settings

log = logging.getLogger("mailer")


def send(to: str, subject: str, body: str) -> bool:
    """성공하면 True. 실패하면 콘솔 출력 후 False — 예외를 올리지 않는다."""
    if not settings.smtp_host:
        _console(to, subject, body, reason="SMTP 미설정")
        return False

    msg = EmailMessage()
    msg["From"] = settings.smtp_from
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as s:
            s.starttls()
            if settings.smtp_user:
                s.login(settings.smtp_user, settings.smtp_password)
            s.send_message(msg)
        return True
    except Exception as e:  # noqa: BLE001 — 어떤 이유든 서버는 계속 돈다
        _console(to, subject, body, reason=f"발송 실패: {e}")
        return False


def _console(to: str, subject: str, body: str, reason: str) -> None:
    log.warning("메일 미발송(%s) → %s / %s", reason, to, subject)
    print(f"\n{'=' * 60}\n[MAIL:{reason}] to={to}\n{subject}\n{'-' * 60}\n{body}\n{'=' * 60}\n", flush=True)


def verification_link(token: str) -> str:
    return f"{settings.frontend_url.replace(':5173', ':8000')}/api/auth/verify?token={token}"
