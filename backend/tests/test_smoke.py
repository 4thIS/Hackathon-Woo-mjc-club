"""T0 스모크. CI가 이 파일로 "앱이 뜨고 계약대로 응답하는지"를 지킨다.

기능 테스트는 각자 Task에서 추가한다. 프론트 테스트는 없다 (구현계획 §7).
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_clubs_list_shape():
    r = client.get("/api/clubs")
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"items", "total"}


def test_stats_shape():
    r = client.get("/api/stats")
    assert r.status_code == 200
    assert set(r.json()) == {"clubs", "recruiting", "posts", "categories"}


def test_error_shape_is_the_contract():
    """docs/api.md §0.1 — 모든 에러는 {detail:{code,message}} 한 형태다."""
    r = client.get("/api/clubs/999999")
    assert r.status_code == 404
    detail = r.json()["detail"]
    assert detail["code"] == "NOT_FOUND"
    assert isinstance(detail["message"], str)


def test_me_requires_login():
    r = client.get("/api/me")
    assert r.status_code == 401
    assert r.json()["detail"]["code"] == "UNAUTHORIZED"
