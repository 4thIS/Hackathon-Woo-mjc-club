"""메일 발송 설정 — 실제 SMTP 는 건드리지 않는다.

인증 링크가 환경에 따라 깨지지 않는지, Gmail 발신자 규칙을 지키는지,
그리고 SMTP 가 없을 때 서버가 죽지 않는지를 고정한다.
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app import enums
from app.config import settings
from app.db import SessionLocal
from app.models import EmailToken, User
from app.routers import auth as auth_router
from app.services import mailer


@pytest.fixture
def smtp_off(monkeypatch):
    monkeypatch.setattr(settings, "smtp_host", "", raising=False)
    return settings


# --- 인증 링크 ---------------------------------------------------------


def test_verification_link_uses_frontend_origin(monkeypatch):
    """포트 치환 없이 프론트 오리진을 그대로 쓴다.

    개발(vite)·도커(nginx) 모두 /api 를 백엔드로 프록시하므로 이게 양쪽 다 맞다.
    """
    monkeypatch.setattr(settings, "public_base_url", "", raising=False)
    monkeypatch.setattr(settings, "frontend_url", "http://localhost:8080", raising=False)
    assert mailer.verification_link("abc") == "http://localhost:8080/api/auth/verify?token=abc"

    monkeypatch.setattr(settings, "frontend_url", "http://localhost:5173", raising=False)
    assert mailer.verification_link("abc") == "http://localhost:5173/api/auth/verify?token=abc"


def test_public_base_url_overrides(monkeypatch):
    monkeypatch.setattr(settings, "frontend_url", "http://localhost:5173", raising=False)
    monkeypatch.setattr(settings, "public_base_url", "https://club.mjc.ac.kr/", raising=False)
    assert mailer.verification_link("t") == "https://club.mjc.ac.kr/api/auth/verify?token=t"


# --- 발신자 -----------------------------------------------------------


def test_sender_falls_back_to_smtp_user(monkeypatch):
    """Gmail 은 인증한 계정과 다른 From 을 허용하지 않는다."""
    monkeypatch.setattr(settings, "smtp_from", "", raising=False)
    monkeypatch.setattr(settings, "smtp_user", "me@gmail.com", raising=False)
    assert mailer.sender() == "me@gmail.com"

    monkeypatch.setattr(settings, "smtp_from", "no-reply@mjc.ac.kr", raising=False)
    assert mailer.sender() == "no-reply@mjc.ac.kr"


def test_from_header_has_display_name(monkeypatch):
    monkeypatch.setattr(settings, "smtp_from", "", raising=False)
    monkeypatch.setattr(settings, "smtp_user", "me@gmail.com", raising=False)
    monkeypatch.setattr(settings, "smtp_sender_name", "MJC Club Archive", raising=False)
    assert mailer._from_header() == "MJC Club Archive <me@gmail.com>"


# --- 폴백 -------------------------------------------------------------


def test_send_without_smtp_returns_false_and_does_not_raise(smtp_off, capsys):
    """SMTP 가 없어도 서버는 계속 돈다 (backend/CLAUDE.md)."""
    assert mailer.send("someone@mjc.ac.kr", "제목", "본문") is False
    assert "someone@mjc.ac.kr" in capsys.readouterr().out


def test_send_without_sender_returns_false(monkeypatch, capsys):
    monkeypatch.setattr(settings, "smtp_host", "smtp.example.com", raising=False)
    monkeypatch.setattr(settings, "smtp_from", "", raising=False)
    monkeypatch.setattr(settings, "smtp_user", "", raising=False)
    assert mailer.send("someone@mjc.ac.kr", "제목", "본문") is False
    assert "발신 주소 없음" in capsys.readouterr().out


# --- 재발송 쿨다운 -----------------------------------------------------


@pytest.fixture
def unverified_user():
    db = SessionLocal()
    uid = "8800000001"
    user = User(
        id=uid,
        email=f"{uid}@mjc.ac.kr",
        pw_hash="x",
        name="미인증",
        dept="테스트학과",
        birth=datetime(2006, 1, 1).date(),
        gender="남",
        academic_status=enums.ACADEMIC_ENROLLED,
        email_verified=False,
    )
    db.add(user)
    db.commit()
    yield user, db
    db.query(EmailToken).filter(EmailToken.user_id == uid).delete()
    db.query(User).filter(User.id == uid).delete()
    db.commit()
    db.close()


def test_resend_is_rate_limited(client, unverified_user, smtp_off):
    """실제 발송이 켜지면 재발송은 무제한 발송기가 된다. 응답은 204 를 유지한다."""
    user, db = unverified_user
    payload = {"email": user.email}

    assert client.post("/api/auth/verify/resend", json=payload).status_code == 204
    first = db.scalar(select(EmailToken).where(EmailToken.user_id == user.id))
    assert first is not None

    # 곧바로 다시 요청 — 204 지만 토큰은 새로 발급되지 않는다
    assert client.post("/api/auth/verify/resend", json=payload).status_code == 204
    db.expire_all()
    again = db.scalar(select(EmailToken).where(EmailToken.user_id == user.id))
    assert again.token == first.token


def test_resend_allowed_after_cooldown(client, unverified_user, smtp_off):
    user, db = unverified_user
    payload = {"email": user.email}
    client.post("/api/auth/verify/resend", json=payload)

    # 발급 시각을 쿨다운 밖으로 밀어 놓는다 (expires_at 에서 역산하므로 그걸 당긴다)
    token = db.scalar(select(EmailToken).where(EmailToken.user_id == user.id))
    old = token.token
    token.expires_at = datetime.now(UTC) + auth_router.TOKEN_TTL - timedelta(minutes=5)
    db.commit()

    assert client.post("/api/auth/verify/resend", json=payload).status_code == 204
    db.expire_all()
    fresh = db.scalar(select(EmailToken).where(EmailToken.user_id == user.id))
    assert fresh.token != old
