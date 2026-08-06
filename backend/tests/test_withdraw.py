"""회원 탈퇴. 명세: docs/api.md §2 `DELETE /api/me`

핵심은 **활동 기록이 남는 것**이다. 글은 동아리의 자산이지 개인 소유가 아니다.
"""

from datetime import date

import pytest
from sqlalchemy import select

from app import enums
from app.models import ClubMember, Like, Post, User


def make_post(db, club, author):
    p = Post(
        club_id=club.id,
        author_id=author.id,
        title="탈퇴 확인용 활동",
        body="본문",
        activity_date=date(2026, 5, 1),
        is_public=True,
    )
    db.add(p)
    db.commit()
    return p


def test_withdraw_requires_password(client, make_user, auth_cookie):
    user = make_user()
    r = client.request("DELETE", "/api/me", json={"password": "틀린비밀번호"},
                       cookies=auth_cookie(user))
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "INVALID_PASSWORD"


def test_withdraw_removes_account_and_memberships(client, make_user, make_club, join_club,
                                                  auth_cookie, db):
    user = make_user()
    club = make_club()
    join_club(user, club)

    r = client.request("DELETE", "/api/me", json={"password": "test1234"},
                       cookies=auth_cookie(user))
    assert r.status_code == 204

    # db.get 은 세션 캐시의 삭제된 객체를 되살리려다 ObjectDeletedError 를 낸다.
    # 캐시를 비우고 쿼리로 직접 확인한다.
    db.expunge_all()
    assert db.scalar(select(User).where(User.id == user.id)) is None
    assert db.scalar(
        select(ClubMember).where(ClubMember.user_id == user.id, ClubMember.club_id == club.id)
    ) is None
    # 세션이 끊겨 더는 조회되지 않는다
    assert client.get("/api/me", cookies=auth_cookie(user)).status_code == 401


def test_posts_survive_withdrawal(client, make_user, make_club, join_club, auth_cookie, db):
    """작성자가 나가도 동아리 아카이브에 구멍이 생기면 안 된다."""
    author = make_user()
    club = make_club()
    join_club(author, club, role=enums.ROLE_LEADER)
    post = make_post(db, club, author)

    # 동아리장은 탈퇴할 수 없으므로 먼저 넘긴다
    heir = make_user()
    join_club(heir, club)
    db.get(ClubMember, {"user_id": author.id, "club_id": club.id}).role = enums.ROLE_MEMBER
    db.get(ClubMember, {"user_id": heir.id, "club_id": club.id}).role = enums.ROLE_LEADER
    db.commit()

    r = client.request("DELETE", "/api/me", json={"password": "test1234"},
                       cookies=auth_cookie(author))
    assert r.status_code == 204

    db.expire_all()
    kept = db.get(Post, post.id)
    assert kept is not None, "탈퇴로 활동 글이 사라지면 안 된다"
    assert kept.author_id is None

    shown = client.get(f"/api/posts/{post.id}")
    assert shown.status_code == 200
    assert shown.json()["author"]["name"] == "탈퇴한 회원"


def test_leader_must_hand_over_first(client, make_user, make_club, join_club, auth_cookie):
    user = make_user()
    club = make_club()
    join_club(user, club, role=enums.ROLE_LEADER)

    r = client.request("DELETE", "/api/me", json={"password": "test1234"},
                       cookies=auth_cookie(user))
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "LEADER_CANNOT_LEAVE"
    assert club.name in r.json()["detail"]["message"]


def test_last_admin_cannot_withdraw(client, make_user, auth_cookie, db):
    admin = make_user(admin=True)
    others = db.query(User).filter(User.is_admin.is_(True), User.id != admin.id).all()
    for o in others:
        o.is_admin = False
    db.commit()
    try:
        r = client.request("DELETE", "/api/me", json={"password": "test1234"},
                           cookies=auth_cookie(admin))
        assert r.status_code == 409
        assert r.json()["detail"]["code"] == "LAST_ADMIN"
        assert db.get(User, admin.id) is not None
    finally:
        for o in others:
            o.is_admin = True
        db.commit()


def test_likes_are_removed(client, make_user, make_club, join_club, auth_cookie, db):
    author = make_user()
    liker = make_user()
    club = make_club()
    join_club(author, club, role=enums.ROLE_LEADER)
    post = make_post(db, club, author)
    db.add(Like(user_id=liker.id, post_id=post.id))
    db.commit()

    r = client.request("DELETE", "/api/me", json={"password": "test1234"},
                       cookies=auth_cookie(liker))
    assert r.status_code == 204
    assert db.scalar(select(Like).where(Like.user_id == liker.id)) is None


def test_student_id_can_be_reused(client, make_user, auth_cookie):
    """실제 재학생이 계정을 다시 만들 수 있어야 한다."""
    user = make_user()
    sid, email = user.id, user.email

    assert client.request("DELETE", "/api/me", json={"password": "test1234"},
                          cookies=auth_cookie(user)).status_code == 204

    r = client.post("/api/auth/signup", json={
        "email": email, "password": "test1234", "student_id": sid,
        "name": "재가입자", "dept": "컴퓨터정보과", "birth": "2005-01-01", "gender": "남",
    })
    assert r.status_code == 201


@pytest.mark.parametrize("cookies", [None])
def test_withdraw_requires_login(client, cookies):
    r = client.request("DELETE", "/api/me", json={"password": "x"})
    assert r.status_code == 401
