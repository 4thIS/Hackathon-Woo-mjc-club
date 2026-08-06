"""T1 — 인증·계정. 명세: docs/api.md §2

실제 DB 를 쓴다. 테스트 계정은 학번 `999...` 대역이라 seed 데이터와 겹치지 않는다.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app import enums
from app.db import SessionLocal
from app.main import app
from app.models import Club, ClubMember, EmailToken, User


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def account():
    """매번 새 학번. 테스트가 서로 간섭하지 않는다."""
    sid = f"99{uuid.uuid4().int % 100_000_000:08d}"
    yield {
        "email": f"{sid}@mjc.ac.kr",
        "password": "test1234",
        "student_id": sid,
        "name": "테스터",
        "dept": "컴퓨터공학과",
        "birth": "2006-03-11",
        "gender": "남",
    }
    with SessionLocal() as db:
        db.query(ClubMember).filter(ClubMember.user_id == sid).delete()
        db.query(EmailToken).filter(EmailToken.user_id == sid).delete()
        db.query(User).filter(User.id == sid).delete()
        db.commit()


@pytest.fixture
def club():
    """테스트가 쓸 동아리를 직접 만든다.

    seed 데이터에 기대지 않는다 — CI 는 빈 DB 로 돌기 때문이다 (test_smoke.py 주석).
    """
    name = f"테스트동아리{uuid.uuid4().hex[:8]}"
    with SessionLocal() as db:
        row = Club(name=name, category=enums.CATEGORIES[0], founded_year=2020)
        db.add(row)
        db.commit()
        club_id = row.id

    yield club_id

    with SessionLocal() as db:
        db.query(ClubMember).filter(ClubMember.club_id == club_id).delete()
        db.query(Club).filter(Club.id == club_id).delete()
        db.commit()


def token_of(student_id: str) -> str:
    with SessionLocal() as db:
        row = db.scalar(select(EmailToken).where(EmailToken.user_id == student_id))
        return row.token


# ── 가입 검증 ──────────────────────────────────────────────


def test_signup_and_verify_then_login(client, account):
    r = client.post("/api/auth/signup", json=account)
    assert r.status_code == 201
    assert r.json()["student_id"] == account["student_id"]

    # 인증 전에도 로그인은 된다. 다만 email_verified 가 False 다 (기획서 §4.2)
    r = client.post("/api/auth/login", json={"email": account["email"], "password": "test1234"})
    assert r.status_code == 200
    assert r.json()["email_verified"] is False

    # 미인증은 '인증' 권한이 필요한 곳에서 막힌다
    r = client.post("/api/me/ai-key", json={"api_key": "x"})
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "EMAIL_NOT_VERIFIED"

    # 인증 링크는 JSON 이 아니라 302 다
    r = client.get(
        "/api/auth/verify", params={"token": token_of(account["student_id"])}, follow_redirects=False
    )
    assert r.status_code == 302
    assert "status=ok" in r.headers["location"]

    assert client.get("/api/me").json()["email_verified"] is True
    client.post("/api/auth/logout")


def test_verify_rejects_garbage_token(client):
    r = client.get("/api/auth/verify", params={"token": "없는토큰"}, follow_redirects=False)
    assert r.status_code == 302
    assert "status=invalid" in r.headers["location"]


@pytest.mark.parametrize(
    ("patch", "code"),
    [
        ({"email": "2026261234@gmail.com"}, "INVALID_EMAIL_DOMAIN"),
        ({"student_id": "12345"}, "INVALID_STUDENT_ID"),  # 10자리가 아님
        ({"password": "short"}, "WEAK_PASSWORD"),
        ({"gender": "기타"}, "INVALID_INPUT"),
    ],
)
def test_signup_input_rules(client, account, patch, code):
    r = client.post("/api/auth/signup", json={**account, **patch})
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == code


def test_email_local_part_need_not_match_student_id(client, account):
    """학교 메일 주소가 학번과 다른 계정이 있다 — 둘을 따로 받는다."""
    r = client.post("/api/auth/signup", json={**account, "email": "hongkildong@mjc.ac.kr"})
    assert r.status_code == 201
    assert r.json()["student_id"] == account["student_id"]

    login = client.post("/api/auth/login",
                        json={"email": "hongkildong@mjc.ac.kr", "password": account["password"]})
    assert login.status_code == 200
    assert login.json()["id"] == account["student_id"]


def test_same_student_id_on_other_domain_is_blocked(client, account):
    """학번이 PK다 — 도메인만 바꿔 두 번 가입할 수 없다 (기획서 §4.1)."""
    assert client.post("/api/auth/signup", json=account).status_code == 201

    other = {**account, "email": f"{account['student_id']}@on.mjc.ac.kr"}
    r = client.post("/api/auth/signup", json=other)
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "DUPLICATE_STUDENT_ID"


def test_login_rejects_wrong_password(client, account):
    client.post("/api/auth/signup", json=account)
    r = client.post("/api/auth/login", json={"email": account["email"], "password": "틀린비밀번호"})
    assert r.status_code == 401
    assert r.json()["detail"]["code"] == "INVALID_CREDENTIALS"


def test_resend_hides_whether_email_exists(client):
    """없는 주소여도 204 다 — 가입 여부를 알려주지 않는다 (api.md §2)."""
    r = client.post("/api/auth/verify/resend", json={"email": "99999999@mjc.ac.kr"})
    assert r.status_code == 204


# ── 내 정보 ────────────────────────────────────────────────


def test_update_me_allows_only_dept_status_password(client, account):
    client.post("/api/auth/signup", json=account)
    client.post("/api/auth/login", json={"email": account["email"], "password": "test1234"})

    r = client.patch("/api/me", json={"dept": "전자공학과", "academic_status": "휴학"})
    assert r.status_code == 200
    assert r.json()["dept"] == "전자공학과"
    assert r.json()["academic_status"] == "휴학"

    # 잠긴 필드는 보내도 무시된다 (기획서 §4.3)
    r = client.patch("/api/me", json={"name": "다른이름", "id": "00000000"})
    assert r.status_code == 200
    assert r.json()["name"] == "테스터"
    assert r.json()["id"] == account["student_id"]

    # 새 비밀번호로 실제로 로그인이 된다
    client.patch("/api/me", json={"password": "newpass1234"})
    client.post("/api/auth/logout")
    r = client.post("/api/auth/login", json={"email": account["email"], "password": "newpass1234"})
    assert r.status_code == 200
    client.post("/api/auth/logout")


def join(student_id: str, club_id: int, role: str) -> None:
    with SessionLocal() as db:
        db.add(ClubMember(user_id=student_id, club_id=club_id, role=role))
        db.commit()


def test_graduation_turns_memberships_into_ob(client, account, club):
    """졸업하면 모든 소속이 OB 가 된다 (기획서 §3.1)."""
    client.post("/api/auth/signup", json=account)
    client.post("/api/auth/login", json={"email": account["email"], "password": "test1234"})
    join(account["student_id"], club, enums.ROLE_MEMBER)

    mine = client.get("/api/me/clubs").json()
    assert [m["membership"] for m in mine] == ["활동중"]

    r = client.patch("/api/me", json={"academic_status": "졸업"})
    assert r.status_code == 200
    assert [m["membership"] for m in client.get("/api/me/clubs").json()] == ["OB"]

    client.post("/api/auth/logout")


def test_leader_cannot_graduate(client, account, club):
    """동아리장이 OB 가 되면 그 동아리가 마비된다 (기획서 §4.3)."""
    client.post("/api/auth/signup", json=account)
    client.post("/api/auth/login", json={"email": account["email"], "password": "test1234"})
    join(account["student_id"], club, enums.ROLE_LEADER)

    r = client.patch("/api/me", json={"academic_status": "졸업"})
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "LEADER_CANNOT_GRADUATE"

    # 막혔으니 학적도 그대로여야 한다
    assert client.get("/api/me").json()["academic_status"] == "재학"

    client.post("/api/auth/logout")


def test_my_requests_has_three_lists(client, account):
    client.post("/api/auth/signup", json=account)
    client.post("/api/auth/login", json={"email": account["email"], "password": "test1234"})

    r = client.get("/api/me/requests")
    assert r.status_code == 200
    assert set(r.json()) == {"join", "create", "leave"}
    client.post("/api/auth/logout")


def test_logout_clears_session(client, account):
    client.post("/api/auth/signup", json=account)
    client.post("/api/auth/login", json={"email": account["email"], "password": "test1234"})
    assert client.get("/api/me").status_code == 200

    client.post("/api/auth/logout")
    assert client.get("/api/me").status_code == 401


# ── 학년 (학번에서 유추하지 않는다) ─────────────────────────


def test_signup_stores_given_grade(client, account):
    """학번 앞자리로 계산하지 않는다 — 휴학·재수·편입이면 어긋나기 때문이다."""
    r = client.post("/api/auth/signup", json={**account, "grade": 2})
    assert r.status_code == 201

    client.post("/api/auth/login", json={"email": account["email"], "password": account["password"]})
    assert client.get("/api/me").json()["grade"] == 2
    client.post("/api/auth/logout")


def test_signup_rejects_bad_student_id(client, account):
    short = {**account, "student_id": "12345", "email": "12345@mjc.ac.kr"}
    r = client.post("/api/auth/signup", json=short)
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "INVALID_STUDENT_ID"


def test_grade_is_editable_and_clearable(client, account):
    client.post("/api/auth/signup", json={**account, "grade": 1})
    client.post("/api/auth/login", json={"email": account["email"], "password": account["password"]})

    assert client.patch("/api/me", json={"grade": 3}).json()["grade"] == 3
    # 명시적 null 은 "비우기". 아예 안 보내면 그대로 둔다
    assert client.patch("/api/me", json={"grade": None}).json()["grade"] is None
    assert client.patch("/api/me", json={"dept": "전자공학과"}).json()["grade"] is None

    r = client.patch("/api/me", json={"grade": 9})
    assert r.status_code == 400
    client.post("/api/auth/logout")
