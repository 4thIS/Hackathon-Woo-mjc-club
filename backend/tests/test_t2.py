"""T2 — 탐색 읽기 엔드포인트. 명세: docs/api.md §3

권한별 노출 차이가 이 Task의 핵심이라(비공개 글·실명) 그 경계를 테스트로 고정한다.
로그인은 T1(wj) 이 아직 구현 전이라 세션 쿠키 대신 의존성 오버라이드로 사용자를 주입한다.
"""

from datetime import date

import pytest
from fastapi.testclient import TestClient

from app import enums
from app.db import SessionLocal
from app.deps import current_user_optional
from app.main import app
from app.models import Club, ClubMember, Post, User

CLUB_A = "테스트동아리_T2_A"
CLUB_B = "테스트동아리_T2_B"
MEMBER_ID = "9900000001"
OUTSIDER_ID = "9900000002"


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def data(client):
    """이 테스트만의 데이터를 만들고 끝나면 지운다. seed 유무와 무관하게 돌아야 한다."""
    db = SessionLocal()
    member = User(
        id=MEMBER_ID, email=f"{MEMBER_ID}@mjc.ac.kr", pw_hash="x", name="부원", dept="컴퓨터공학과",
        birth=date(2006, 1, 1), gender="남", email_verified=True,
    )
    outsider = User(
        id=OUTSIDER_ID, email=f"{OUTSIDER_ID}@mjc.ac.kr", pw_hash="x", name="외부인", dept="간호학과",
        birth=date(2006, 1, 1), gender="여", email_verified=True,
    )
    a = Club(name=CLUB_A, category="취미·교양", founded_year=2020, current_gen=3)
    b = Club(name=CLUB_B, category="체육", founded_year=2020, current_gen=1)
    db.add_all([member, outsider, a, b])
    db.flush()

    db.add(ClubMember(user_id=MEMBER_ID, club_id=a.id, role=enums.ROLE_LEADER, gen=1))
    db.add(ClubMember(user_id=OUTSIDER_ID, club_id=a.id, membership=enums.MEMBERSHIP_OB, gen=None))

    posts = [
        Post(club_id=a.id, author_id=MEMBER_ID, title="A-오래된-공개", body="본문",
             activity_date=date(2024, 3, 1), is_public=True, photos=[], tags=[]),
        Post(club_id=a.id, author_id=MEMBER_ID, title="A-최신-공개", body="본문",
             activity_date=date(2025, 9, 1), is_public=True, photos=[], tags=[]),
        Post(club_id=a.id, author_id=MEMBER_ID, title="A-비공개", body="본문",
             activity_date=date(2025, 10, 1), is_public=False, photos=[], tags=[]),
        Post(club_id=b.id, author_id=MEMBER_ID, title="B-공개", body="본문",
             activity_date=date(2025, 11, 1), is_public=True, photos=[], tags=[]),
    ]
    db.add_all(posts)
    db.commit()

    ids = {"club_a": a.id, "club_b": b.id, "private": posts[2].id, "public": posts[1].id}
    db.close()

    yield ids

    db = SessionLocal()
    db.query(Post).filter(Post.club_id.in_([ids["club_a"], ids["club_b"]])).delete(synchronize_session=False)
    db.query(ClubMember).filter(ClubMember.club_id.in_([ids["club_a"], ids["club_b"]])).delete(
        synchronize_session=False
    )
    db.query(Club).filter(Club.id.in_([ids["club_a"], ids["club_b"]])).delete(synchronize_session=False)
    db.query(User).filter(User.id.in_([MEMBER_ID, OUTSIDER_ID])).delete(synchronize_session=False)
    db.commit()
    db.close()


def as_user(user_id: str | None):
    """current_user_optional 을 갈아끼운다. None 이면 비로그인."""
    def _override():
        if user_id is None:
            return None
        db = SessionLocal()
        try:
            return db.get(User, user_id)
        finally:
            db.close()

    app.dependency_overrides[current_user_optional] = _override


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


# --- 타임라인 ----------------------------------------------------------


def test_timeline_hides_private_from_anonymous(client, data):
    as_user(None)
    r = client.get(f"/api/clubs/{data['club_a']}/posts", params={"limit": 20})
    assert r.status_code == 200
    body = r.json()
    titles = [p["title"] for p in body["items"]]
    assert titles == ["A-오래된-공개", "A-최신-공개"]  # 오래된 순
    assert body["total"] == 2  # total 도 공개 글 기준이어야 한다
    assert body["first_year"] == 2024


def test_timeline_shows_private_to_member(client, data):
    as_user(MEMBER_ID)
    r = client.get(f"/api/clubs/{data['club_a']}/posts", params={"limit": 20})
    body = r.json()
    assert body["total"] == 3
    assert "A-비공개" in [p["title"] for p in body["items"]]


def test_timeline_batches(client, data):
    as_user(None)
    first = client.get(f"/api/clubs/{data['club_a']}/posts", params={"offset": 0, "limit": 1}).json()
    assert len(first["items"]) == 1
    assert first["has_more"] is True

    second = client.get(f"/api/clubs/{data['club_a']}/posts", params={"offset": 1, "limit": 1}).json()
    assert second["items"][0]["title"] != first["items"][0]["title"]
    assert second["has_more"] is False


# --- 인원 --------------------------------------------------------------


def test_members_hide_names_from_anonymous(client, data):
    as_user(None)
    body = client.get(f"/api/clubs/{data['club_a']}/members").json()
    assert body["total"] == 2
    assert all(g["members"] == [] for g in body["groups"])  # 인원수만 (api.md §9-2)
    assert sum(g["count"] for g in body["groups"]) == 2


def test_members_show_names_to_logged_in(client, data):
    as_user(MEMBER_ID)
    body = client.get(f"/api/clubs/{data['club_a']}/members").json()
    labels = [g["label"] for g in body["groups"]]
    assert "OB" in labels
    assert labels[-1] == "OB"  # OB 는 항상 마지막
    named = [m for g in body["groups"] for m in g["members"]]
    assert {"부원", "외부인"} == {m["name"] for m in named}
    assert any(m["role"] == enums.ROLE_LEADER for m in named)


# --- 글 상세 -----------------------------------------------------------


def test_private_post_is_404_not_403(client, data):
    """존재 자체를 숨긴다 (api.md §9-5)."""
    as_user(None)
    r = client.get(f"/api/posts/{data['private']}")
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "NOT_FOUND"


def test_private_post_visible_to_member(client, data):
    as_user(MEMBER_ID)
    r = client.get(f"/api/posts/{data['private']}")
    assert r.status_code == 200
    assert r.json()["can_edit"] is True  # 동아리장


def test_public_post_readable_by_anonymous(client, data):
    as_user(None)
    body = client.get(f"/api/posts/{data['public']}").json()
    assert body["can_edit"] is False
    assert body["liked_by_me"] is False
    assert isinstance(body["photos"], list)


# --- 캐러셀 ------------------------------------------------------------


def test_highlights_one_per_club(client, data):
    as_user(None)
    items = client.get("/api/posts/highlights", params={"limit": 20}).json()
    club_ids = [p["club_id"] for p in items]
    assert len(club_ids) == len(set(club_ids))  # 동아리당 1건 (api.md §9-4)
    assert all(p["is_public"] for p in items)

    mine = [p for p in items if p["club_id"] == data["club_a"]]
    assert mine and mine[0]["title"] == "A-최신-공개"  # 동아리 안에서는 최신 1건
    # 사진 없는 카드의 분야 그라데이션에 필요하다 (api.md §0.4)
    assert mine[0]["category"] == "취미·교양"
