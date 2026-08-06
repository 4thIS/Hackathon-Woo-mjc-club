"""T6 — AI 활동 글 초안. 명세: docs/api.md §7 · 기획서 §7

게이트웨이는 네트워크라 모킹한다. 실제 호출은 scratchpad 스모크로 따로 확인했다
(기획서 §7.0 결과표). 여기서 지키는 것은 **계약과 환각 방지 규칙**이다.
"""

import io
import uuid

import pytest
from fastapi.testclient import TestClient

from app import enums
from app.db import SessionLocal
from app.main import app
from app.models import Club, ClubMember, EmailToken, User
from app.security import encrypt_ai_key
from app.services import ai_draft, pdf_text


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def leader(client):
    """AI 키가 등록된 동아리장. 로그인 상태로 넘긴다."""
    sid = f"98{uuid.uuid4().int % 1_000_000:06d}"
    name = f"AI테스트동아리{uuid.uuid4().hex[:8]}"
    account = {
        "email": f"{sid}@mjc.ac.kr",
        "password": "test1234",
        "student_id": sid,
        "name": "초안테스터",
        "dept": "컴퓨터정보과",
        "birth": "2006-01-01",
        "gender": "남",
    }
    client.post("/api/auth/signup", json=account)

    with SessionLocal() as db:
        club = Club(name=name, category=enums.CATEGORIES[0], founded_year=2020)
        db.add(club)
        db.commit()
        club_id = club.id

        user = db.get(User, sid)
        user.email_verified = True  # 인증 메일 왕복은 T1 테스트가 이미 검증한다
        user.ai_key_enc = encrypt_ai_key("dummy-key-for-tests")
        user.ai_key_tail = "ests"
        db.add(ClubMember(user_id=sid, club_id=club_id, role=enums.ROLE_LEADER))
        db.commit()

    client.post("/api/auth/login", json={"email": account["email"], "password": "test1234"})
    yield {"student_id": sid, "club_id": club_id}
    client.post("/api/auth/logout")

    with SessionLocal() as db:
        db.query(ClubMember).filter(ClubMember.user_id == sid).delete()
        db.query(Club).filter(Club.id == club_id).delete()
        db.query(EmailToken).filter(EmailToken.user_id == sid).delete()
        db.query(User).filter(User.id == sid).delete()
        db.commit()


def fake_gateway(monkeypatch, title="성북동 출사", body="12명이 다녀왔습니다.", tags=None):
    """generate 를 그대로 두고 게이트웨이 응답만 갈아끼운다."""
    payload = {"title": title, "body": body, "tags": tags or ["출사"]}

    class Res:
        status_code = 200

        @staticmethod
        def json():
            import json as _json

            return {"choices": [{"message": {"content": _json.dumps(payload, ensure_ascii=False)}}]}

    captured = {}

    def _post(url, **kw):
        captured["url"] = url
        captured["json"] = kw.get("json")
        captured["headers"] = kw.get("headers")
        return Res()

    monkeypatch.setattr(ai_draft.httpx, "post", _post)
    return captured


# ── 환각 방지 규칙 (기획서 §7.2) ───────────────────────────


def test_photos_only_is_refused(client, leader):
    """사진만으로는 초안을 만들지 않는다. 버그가 아니라 설계다."""
    r = client.post(
        "/api/ai/draft",
        data={"club_id": leader["club_id"]},
        files=[("photos", ("a.jpg", b"\xff\xd8\xff fake jpeg", "image/jpeg"))],
    )
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "MEMO_REQUIRED"


def test_nothing_at_all_is_refused(client, leader):
    r = client.post("/api/ai/draft", data={"club_id": leader["club_id"]})
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "MEMO_REQUIRED"


def test_blank_memo_counts_as_missing(client, leader):
    r = client.post("/api/ai/draft", data={"club_id": leader["club_id"], "memo": "   "})
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "MEMO_REQUIRED"


def test_unreadable_pdf_asks_for_memo(client, leader):
    r = client.post(
        "/api/ai/draft",
        data={"club_id": leader["club_id"]},
        files=[("pdf", ("scan.pdf", b"not really a pdf", "application/pdf"))],
    )
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "PDF_UNREADABLE"


# ── 정상 경로 ──────────────────────────────────────────────


def test_memo_only_produces_draft(client, leader, monkeypatch):
    captured = fake_gateway(monkeypatch)
    r = client.post(
        "/api/ai/draft",
        data={"club_id": leader["club_id"], "memo": "10/12 성북동 출사, 12명 참여"},
    )
    assert r.status_code == 200
    d = r.json()
    assert d["title"] and d["body"]
    assert d["used"] == {"memo": True, "pdf": False, "photos": 0, "vision": False}

    # 끝 슬래시가 빠지면 게이트웨이가 리다이렉트한다
    assert captured["url"].endswith("/chat/completions/")
    # UA 없이 나가면 Cloudflare 가 403(1010)으로 막는다 (backend/CLAUDE.md)
    assert "Mozilla" in captured["headers"]["User-Agent"]


def test_photos_ride_along_when_memo_exists(client, leader, monkeypatch):
    captured = fake_gateway(monkeypatch)
    r = client.post(
        "/api/ai/draft",
        data={"club_id": leader["club_id"], "memo": "출사 다녀왔습니다"},
        files=[
            ("photos", ("a.jpg", b"\xff\xd8\xff aaa", "image/jpeg")),
            ("photos", ("b.jpg", b"\xff\xd8\xff bbb", "image/jpeg")),
        ],
    )
    assert r.status_code == 200
    assert r.json()["used"] == {"memo": True, "pdf": False, "photos": 2, "vision": True}

    content = captured["json"]["messages"][1]["content"]
    assert sum(1 for c in content if c["type"] == "image_url") == 2
    # 사실이 먼저, 사진이 뒤 — 순서가 곧 우선순위다
    assert content[0]["type"] == "text"
    assert "메모" in content[0]["text"]


@pytest.mark.parametrize(
    ("raw", "mime"),
    [
        (b"\x89PNG\r\n\x1a\n" + b"0" * 20, "image/png"),
        (b"\xff\xd8\xff" + b"0" * 20, "image/jpeg"),
        (b"GIF89a" + b"0" * 20, "image/gif"),
        (b"RIFF" + b"0000" + b"WEBP" + b"0" * 20, "image/webp"),
    ],
)
def test_media_type_comes_from_bytes_not_filename(raw, mime, monkeypatch):
    """선언한 media type 과 실제 바이트가 다르면 게이트웨이가 400 으로 거부한다.

    실제로 겪은 문제다 — image/jpeg 로 고정해두고 PNG 를 보내 400 을 받았다.
    """
    content = ai_draft._user_content("동아리", "체육", "메모", None, [raw])
    assert content[1]["image_url"]["url"].startswith(f"data:{mime};base64,")


def test_prompt_carries_the_no_hallucination_rules():
    """규칙이 프롬프트에서 빠지면 AI 가 '뜻깊은 시간' 을 지어낸다 (기획서 §7.2)."""
    p = ai_draft.SYSTEM_PROMPT
    assert "지어내지 않습니다" in p
    assert "구체화" in p
    assert "뜻깊은" in p  # 금지 예시가 실제로 들어 있는지


# ── 응답 파싱 ──────────────────────────────────────────────


@pytest.mark.parametrize(
    "raw",
    [
        '{"title":"제목","body":"본문","tags":["가","나"]}',
        '```json\n{"title":"제목","body":"본문","tags":["가","나"]}\n```',
        '설명이 앞에 붙는 경우 {"title":"제목","body":"본문","tags":["가","나"]} 뒤에도 붙음',
    ],
)
def test_parse_survives_wrapping(raw):
    d = ai_draft._parse(raw)
    assert d["title"] == "제목"
    assert d["body"] == "본문"
    assert d["tags"] == ["가", "나"]


@pytest.mark.parametrize("raw", ["JSON 이 아예 없음", '{"title":"","body":""}', "{깨진 json"])
def test_parse_rejects_garbage(raw):
    with pytest.raises(ai_draft.GatewayError):
        ai_draft._parse(raw)


def test_tags_are_capped_at_four():
    d = ai_draft._parse('{"title":"t","body":"b","tags":["1","2","3","4","5","6"]}')
    assert len(d["tags"]) == 4


# ── 게이트웨이 장애 ────────────────────────────────────────


def test_quota_exceeded_maps_to_429(client, leader, monkeypatch):
    class Res:
        status_code = 429
        text = "quota"

    monkeypatch.setattr(ai_draft.httpx, "post", lambda url, **kw: Res())
    r = client.post("/api/ai/draft", data={"club_id": leader["club_id"], "memo": "메모"})
    assert r.status_code == 429
    assert r.json()["detail"]["code"] == "AI_QUOTA_EXCEEDED"


def test_gateway_failure_maps_to_502(client, leader, monkeypatch):
    class Res:
        status_code = 500
        text = "boom"

    monkeypatch.setattr(ai_draft.httpx, "post", lambda url, **kw: Res())
    r = client.post("/api/ai/draft", data={"club_id": leader["club_id"], "memo": "메모"})
    assert r.status_code == 502
    assert r.json()["detail"]["code"] == "AI_GATEWAY_ERROR"


def test_missing_key_is_rejected_before_calling_gateway(client, leader, monkeypatch):
    def _boom(*a, **kw):
        raise AssertionError("키가 없으면 게이트웨이를 부르면 안 된다")

    monkeypatch.setattr(ai_draft.httpx, "post", _boom)
    with SessionLocal() as db:
        u = db.get(User, leader["student_id"])
        u.ai_key_enc = None
        db.commit()

    r = client.post("/api/ai/draft", data={"club_id": leader["club_id"], "memo": "메모"})
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "AI_KEY_NOT_REGISTERED"


# ── 시연 폴백 (구현계획 §6) ────────────────────────────────


def test_demo_fallback_needs_no_gateway_and_no_key(monkeypatch):
    monkeypatch.setattr(ai_draft.settings, "demo_fallback", 1)
    monkeypatch.setattr(
        ai_draft.httpx, "post", lambda *a, **kw: pytest.fail("폴백은 게이트웨이를 부르지 않는다")
    )
    d = ai_draft.generate("", "동아리", "체육", "메모", None, [b"x", b"y"])
    assert d["title"] and d["tags"]
    assert d["used"]["photos"] == 2


# ── PDF 추출 ───────────────────────────────────────────────


def test_pdf_extract_returns_none_for_garbage():
    assert pdf_text.extract(b"this is not a pdf") is None


def test_pdf_extract_reads_text():
    pytest.importorskip("reportlab", reason="PDF 생성기가 없으면 건너뛴다")
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(72, 720, "Field trip on October 12 with twelve members attending.")
    c.save()

    text = pdf_text.extract(buf.getvalue())
    assert text is not None
    assert "October 12" in text
