"""메일 발송. **실패해도 서버가 죽지 않는다** (backend/CLAUDE.md 규칙).

SMTP 설정이 없거나 발송이 실패하면 콘솔에 내용을 출력한다. 시연 중 메일이
안 가는 것보다 인증 링크를 터미널에서 복사할 수 있는 편이 낫다.

Gmail 을 발신 서버로 쓸 때 주의:
- 앱 비밀번호가 필요하다(2단계 인증 켠 뒤 발급). 계정 비밀번호로는 로그인되지 않는다.
- **인증한 계정과 다른 From 은 허용되지 않는다.** `SMTP_FROM` 을 비워 두면
  `SMTP_USER` 를 발신자로 쓴다 (`sender()`).
"""

import logging
import smtplib
from email.message import EmailMessage
from email.utils import formataddr

from ..config import settings

log = logging.getLogger("mailer")

TIMEOUT = 20  # Gmail 은 첫 연결이 느릴 때가 있다


def sender() -> str:
    """실제 발신 주소. smtp_from 이 비면 인증 계정을 쓴다."""
    return settings.smtp_from or settings.smtp_user


def _from_header() -> str:
    addr = sender()
    name = settings.smtp_sender_name.strip()
    return formataddr((name, addr)) if name else addr


def send(to: str, subject: str, body: str) -> bool:
    """성공하면 True. 실패하면 콘솔 출력 후 False — 예외를 올리지 않는다."""
    if not settings.smtp_host:
        _console(to, subject, body, reason="SMTP 미설정")
        return False
    if not sender():
        _console(to, subject, body, reason="발신 주소 없음(SMTP_USER/SMTP_FROM)")
        return False

    msg = EmailMessage()
    msg["From"] = _from_header()
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=TIMEOUT) as s:
            s.starttls()
            if settings.smtp_user:
                s.login(settings.smtp_user, settings.smtp_password)
            s.send_message(msg)
        log.info("메일 발송 → %s / %s", to, subject)
        return True
    except Exception as e:  # noqa: BLE001 — 어떤 이유든 서버는 계속 돈다
        _console(to, subject, body, reason=f"발송 실패: {e}")
        return False


def _console(to: str, subject: str, body: str, reason: str) -> None:
    log.warning("메일 미발송(%s) → %s / %s", reason, to, subject)
    print(f"\n{'=' * 60}\n[MAIL:{reason}] to={to}\n{subject}\n{'-' * 60}\n{body}\n{'=' * 60}\n", flush=True)


def verification_link(token: str) -> str:
    """인증 링크.

    개발(vite)·도커(nginx) 모두 프론트 오리진에서 `/api` 를 백엔드로 프록시하므로
    프론트 주소를 그대로 쓰면 양쪽 다 맞는다. API 가 다른 호스트에 있으면
    `PUBLIC_BASE_URL` 로 덮어쓴다.
    """
    base = (settings.public_base_url or settings.frontend_url).rstrip("/")
    return f"{base}/api/auth/verify?token={token}"
