"""T0 스모크. CI가 이 파일로 "앱이 뜨고 계약대로 응답하는지"를 지킨다.

기능 테스트는 각자 Task에서 추가한다. 프론트 테스트는 없다 (구현계획 §7).
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    # context manager 로 써야 lifespan(create_all)이 돈다. 빈 DB에서도 통과해야 한다.
    with TestClient(app) as c:
        yield c


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_clubs_list_shape(client):
    r = client.get("/api/clubs")
    assert r.status_code == 200
    assert set(r.json()) == {"items", "total"}


def test_stats_shape(client):
    r = client.get("/api/stats")
    assert r.status_code == 200
    assert set(r.json()) == {"clubs", "recruiting", "posts", "categories"}


def test_error_shape_is_the_contract(client):
    """docs/api.md §0.1 — 모든 에러는 {detail:{code,message}} 한 형태다."""
    r = client.get("/api/clubs/999999")
    assert r.status_code == 404
    detail = r.json()["detail"]
    assert detail["code"] == "NOT_FOUND"
    assert isinstance(detail["message"], str)


def test_me_requires_login(client):
    r = client.get("/api/me")
    assert r.status_code == 401
    assert r.json()["detail"]["code"] == "UNAUTHORIZED"


@pytest.mark.parametrize(
    ("call", "status", "code"),
    [
        (lambda c: c.get("/api/nonexistent"), 404, "NOT_FOUND"),
        (lambda c: c.delete("/api/health"), 405, "METHOD_NOT_ALLOWED"),
        # 본문이 유효한 UTF-8 이 아니면 FastAPI 가 detail 을 문자열로 올린다
        (
            lambda c: c.post(
                "/api/auth/login",
                content=b'{"email":"\xff\xfe"}',
                headers={"Content-Type": "application/json"},
            ),
            400,
            "INVALID_INPUT",
        ),
    ],
)
def test_framework_errors_keep_the_contract(client, call, status, code):
    """라우팅·파싱 실패도 {detail:{code,message}} 여야 한다 (api.md §0.1).

    Starlette 가 부모 클래스로 raise 하므로 핸들러를 부모에 걸지 않으면 여기서 샌다.
    프론트는 detail.code 로 분기하기 때문에 문자열이 오면 조용히 깨진다.
    """
    r = call(client)
    assert r.status_code == status
    detail = r.json()["detail"]
    assert detail["code"] == code
    assert isinstance(detail["message"], str)
