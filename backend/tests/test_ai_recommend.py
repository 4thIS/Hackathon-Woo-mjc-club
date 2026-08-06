"""성향 설문 → 동아리 추천 — 명세: docs/api.md §7

게이트웨이는 부르지 않는다. 서버가 응답을 어떻게 검증하는지만 본다.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import ai_recommend
from app.services.ai_draft import GatewayError


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


CLUBS = [
    {"id": 1, "name": "고리사진부", "category": "학술·전공", "recruit_status": "모집중",
     "purpose": "필름 사진", "posts": []},
    {"id": 2, "name": "축구부", "category": "체육", "recruit_status": "모집마감",
     "purpose": "주말 리그", "posts": []},
]
ALLOWED = {c["id"]: c for c in CLUBS}


def test_answers_become_readable_traits():
    lines = ai_recommend.answers_to_lines("AB")
    assert lines == [ai_recommend.AXES[0][0], ai_recommend.AXES[1][1]]
    # 응답이 짧으면 그만큼만 읽는다 (남는 축을 지어내지 않는다)
    assert len(ai_recommend.answers_to_lines("A")) == 1


def test_unknown_club_id_is_dropped():
    """목록에 없는 동아리를 지어내면 버린다 — 화면에 오르면 안 된다."""
    raw = '{"items": [{"club_id": 99, "reason": "지어낸 동아리"}, {"club_id": 1, "reason": "맞는 이유"}]}'
    picked = ai_recommend._parse(raw, ALLOWED)
    assert [p["club_id"] for p in picked] == [1]
    assert picked[0]["name"] == "고리사진부"


def test_duplicate_and_empty_reason_are_dropped():
    raw = (
        '{"items": [{"club_id": 1, "reason": "a"}, {"club_id": 1, "reason": "b"},'
        ' {"club_id": 2, "reason": ""}]}'
    )
    assert [p["club_id"] for p in ai_recommend._parse(raw, ALLOWED)] == [1]


def test_all_unknown_is_an_error():
    with pytest.raises(GatewayError):
        ai_recommend._parse('{"items": [{"club_id": 99, "reason": "x"}]}', ALLOWED)


def test_code_fence_is_tolerated():
    raw = '```json\n{"items": [{"club_id": 2, "reason": "축구를 좋아합니다"}]}\n```'
    assert ai_recommend._parse(raw, ALLOWED)[0]["club_id"] == 2


def test_requires_login(client):
    r = client.post("/api/ai/recommend", json={"answers": "ABABBA"})
    assert r.status_code == 401


def test_rejects_bad_answers(client, make_user, auth_cookie):
    user = make_user(verified=True)
    r = client.post("/api/ai/recommend", json={"answers": "AXAB"}, cookies=auth_cookie(user))
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "INVALID_INPUT"


def test_key_is_required(client, make_user, auth_cookie):
    """키가 없으면 게이트웨이를 부르기 전에 막는다."""
    user = make_user(verified=True)
    r = client.post("/api/ai/recommend", json={"answers": "ABABBA"}, cookies=auth_cookie(user))
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "AI_KEY_NOT_REGISTERED"
