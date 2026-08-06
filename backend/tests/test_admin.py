"""T4 — 동아리 개설·관리자. 명세: docs/api.md §5"""

from datetime import date

from app import enums
from app.models import Club, ClubApplication, ClubMember

from .conftest import new_club_name


def test_apply_club_creates_pending_application(client, make_user, auth_cookie):
    user = make_user()
    r = client.post(
        "/api/club-applications",
        json={
            "name": "보드게임연구회",
            "category": "취미·교양",
            "founded_year": 2026,
            "purpose": "매주 보드게임을 합니다.",
            "advisor": "김지훈",
        },
        cookies=auth_cookie(user),
    )
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "심사중"
    assert isinstance(body["id"], int)


def test_apply_club_forbidden_for_graduated(client, make_user, auth_cookie):
    user = make_user(academic_status=enums.ACADEMIC_GRADUATED)
    r = client.post(
        "/api/club-applications",
        json={"name": "X", "category": "취미·교양", "founded_year": 2026, "purpose": "", "advisor": ""},
        cookies=auth_cookie(user),
    )
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "OB_NOT_ALLOWED"


def test_cancel_application_by_owner_only(client, make_user, auth_cookie, db):
    user = make_user()
    other = make_user()
    app_ = ClubApplication(applicant_id=user.id, name="X", category="취미·교양", founded_year=2026)
    db.add(app_)
    db.commit()

    r1 = client.delete(f"/api/club-applications/{app_.id}", cookies=auth_cookie(other))
    assert r1.status_code == 403

    r2 = client.delete(f"/api/club-applications/{app_.id}", cookies=auth_cookie(user))
    assert r2.status_code == 200


def test_admin_lists_applications_with_applicant_brief(client, make_user, auth_cookie, db):
    admin = make_user(admin=True)
    applicant = make_user(name="박찬우")
    app_ = ClubApplication(
        applicant_id=applicant.id, name="보드게임연구회", category="취미·교양", founded_year=2026
    )
    db.add(app_)
    db.commit()

    r = client.get("/api/admin/club-applications", cookies=auth_cookie(admin))
    assert r.status_code == 200
    items = r.json()
    match = next(i for i in items if i["id"] == app_.id)
    assert match["applicant"]["name"] == "박찬우"
    assert match["status"] == "심사중"


def test_admin_lists_applications_requires_admin(client, make_user, auth_cookie):
    user = make_user()
    r = client.get("/api/admin/club-applications", cookies=auth_cookie(user))
    assert r.status_code == 403


def test_approve_application_creates_club_with_applicant_as_leader(client, make_user, auth_cookie, db):
    admin = make_user(admin=True)
    applicant = make_user()
    # 승인되면 진짜 동아리가 만들어진다. 이름에 표식이 없으면 conftest 의 정리를 빠져나가
    # 다음 실행에서 clubs_name_key 로 충돌한다.
    name = new_club_name()
    app_ = ClubApplication(
        applicant_id=applicant.id,
        name=name,
        category="취미·교양",
        founded_year=2026,
        purpose="목적",
        advisor="김지훈",
    )
    db.add(app_)
    db.commit()

    r = client.post(f"/api/admin/club-applications/{app_.id}/approve", cookies=auth_cookie(admin))
    assert r.status_code == 200
    club_id = r.json()["club_id"]

    club = db.get(Club, club_id)
    assert club is not None
    assert club.name == name

    membership = db.get(ClubMember, {"user_id": applicant.id, "club_id": club_id})
    assert membership.role == "동아리장"
    assert membership.gen == 1


def test_reject_application_requires_reason(client, make_user, auth_cookie, db):
    admin = make_user(admin=True)
    applicant = make_user()
    app_ = ClubApplication(applicant_id=applicant.id, name="X", category="취미·교양", founded_year=2026)
    db.add(app_)
    db.commit()

    r1 = client.post(f"/api/admin/club-applications/{app_.id}/reject", json={}, cookies=auth_cookie(admin))
    assert r1.status_code == 400

    r2 = client.post(
        f"/api/admin/club-applications/{app_.id}/reject",
        json={"reason": "유사 동아리가 이미 있습니다"},
        cookies=auth_cookie(admin),
    )
    assert r2.status_code == 200
    assert r2.json()["status"] == "거절"


def test_admin_can_archive_club(client, make_user, make_club, auth_cookie, db):
    admin = make_user(admin=True)
    club = make_club()
    r = client.patch(f"/api/admin/clubs/{club.id}", json={"status": "보관"}, cookies=auth_cookie(admin))
    assert r.status_code == 200
    db.refresh(club)
    assert club.status == "보관"


def test_admin_can_force_transfer_leader(client, make_user, make_club, join_club, auth_cookie, db):
    admin = make_user(admin=True)
    leader = make_user()
    member = make_user()
    club = make_club()
    join_club(leader, club, role=enums.ROLE_LEADER)
    join_club(member, club)

    r = client.patch(
        f"/api/admin/clubs/{club.id}", json={"leader_id": member.id}, cookies=auth_cookie(admin)
    )
    assert r.status_code == 200

    new_leader = db.get(ClubMember, {"user_id": member.id, "club_id": club.id})
    old_leader = db.get(ClubMember, {"user_id": leader.id, "club_id": club.id})
    assert new_leader.role == "동아리장"
    assert old_leader.role == "부원"


# ── 동아리 삭제 ────────────────────────────────────────────


def test_delete_club_removes_everything_but_the_application_history(
    client, make_user, make_club, join_club, auth_cookie
):
    """되돌릴 수 없는 동작이라 무엇이 지워지고 무엇이 남는지 고정한다."""
    from app.db import SessionLocal
    from app.models import Club, ClubMember, JoinForm, Post

    admin = make_user(admin=True)
    leader = make_user(verified=True)
    club = make_club()
    join_club(leader, club, role="동아리장")

    with SessionLocal() as db:
        db.add(Post(club_id=club.id, author_id=leader.id, title="글", body="본문",
                    photos=[], activity_date=date.today(), tags=[], is_public=True))
        db.add(JoinForm(club_id=club.id, fields=[], required=False))
        db.commit()

    r = client.delete(f"/api/admin/clubs/{club.id}", cookies=auth_cookie(admin))
    assert r.status_code == 204

    with SessionLocal() as db:
        assert db.get(Club, club.id) is None
        assert db.query(ClubMember).filter(ClubMember.club_id == club.id).count() == 0
        assert db.query(Post).filter(Post.club_id == club.id).count() == 0
        assert db.get(JoinForm, club.id) is None


def test_delete_club_requires_admin(client, make_user, make_club, auth_cookie):
    user = make_user(verified=True)
    club = make_club()
    assert client.delete(f"/api/admin/clubs/{club.id}", cookies=auth_cookie(user)).status_code == 403


def test_delete_missing_club_is_404(client, make_user, auth_cookie):
    admin = make_user(admin=True)
    r = client.delete("/api/admin/clubs/999999", cookies=auth_cookie(admin))
    assert r.status_code == 404
