"""학과 목록 — 명세: docs/api.md §1

목록은 crawl_depts.py 가 만든 파일이 원본이다. 앱은 학교 홈페이지를 타지 않는다.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from app import depts
from app.db import SessionLocal
from app.main import app
from app.models import ClubMember, EmailToken, User


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def account():
    sid = f"98{uuid.uuid4().int % 100_000_000:08d}"
    yield {
        "email": f"{sid}@mjc.ac.kr",
        "password": "test1234",
        "student_id": sid,
        "name": "테스터",
        "dept": depts.dept_names()[0],
        "birth": "2006-03-11",
        "gender": "남",
    }
    with SessionLocal() as db:
        db.query(ClubMember).filter(ClubMember.user_id == sid).delete()
        db.query(EmailToken).filter(EmailToken.user_id == sid).delete()
        db.query(User).filter(User.id == sid).delete()
        db.commit()


def test_list_is_served_from_file(client):
    r = client.get("/api/depts")
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) >= 30                      # 크롤러의 하한과 같은 기준
    assert "컴퓨터공학과" in items
    assert all(isinstance(x, str) and x.strip() for x in items)
    # 학부·제도는 학과가 아니다 — 크롤러가 걸러 낸다
    assert not [x for x in items if x.endswith(("학부", "전공"))]


def test_signup_rejects_dept_outside_list(client, account):
    r = client.post("/api/auth/signup", json={**account, "dept": "없는학과"})
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "INVALID_DEPT"


def test_update_me_rejects_dept_outside_list(client, account):
    assert client.post("/api/auth/signup", json=account).status_code == 201
    client.post("/api/auth/login", json={"email": account["email"], "password": "test1234"})

    r = client.patch("/api/me", json={"dept": "없는학과"})
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "INVALID_DEPT"

    ok = client.patch("/api/me", json={"dept": depts.dept_names()[1]})
    assert ok.status_code == 200
    assert ok.json()["dept"] == depts.dept_names()[1]
    client.post("/api/auth/logout")


def test_validation_is_skipped_when_list_is_unavailable(monkeypatch):
    """파일을 못 읽으면 가입을 막는 대신 검증을 건너뛴다 — 목록이 비면 아무도 못 들어온다."""
    monkeypatch.setattr(depts, "dept_names", lambda: ())
    assert depts.is_valid("무엇이든") is True
