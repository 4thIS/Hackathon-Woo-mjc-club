"""T4 — 탈퇴 요청. 명세: docs/api.md §4"""

from datetime import timedelta

from app import enums
from app.models import ClubMember, LeaveRequest, utcnow


def test_member_can_request_leave(client, make_user, make_club, join_club, auth_cookie):
    user = make_user()
    club = make_club()
    join_club(user, club)

    r = client.post(f"/api/clubs/{club.id}/leave-requests", cookies=auth_cookie(user))
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "심사중"
    assert "auto_approve_at" in body


def test_leader_cannot_request_leave_directly(client, make_user, make_club, join_club, auth_cookie):
    leader = make_user()
    club = make_club()
    join_club(leader, club, role=enums.ROLE_LEADER)

    r = client.post(f"/api/clubs/{club.id}/leave-requests", cookies=auth_cookie(leader))
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "LEADER_MUST_TRANSFER"


def test_leader_can_approve_leave_request(client, make_user, make_club, join_club, auth_cookie, db):
    leader = make_user()
    user = make_user()
    club = make_club()
    join_club(leader, club, role=enums.ROLE_LEADER)
    join_club(user, club)

    r1 = client.post(f"/api/clubs/{club.id}/leave-requests", cookies=auth_cookie(user))
    req_id = r1.json()["id"]

    r2 = client.post(f"/api/leave-requests/{req_id}/approve", cookies=auth_cookie(leader))
    assert r2.status_code == 200
    assert r2.json()["status"] == "승인"

    member = db.get(ClubMember, {"user_id": user.id, "club_id": club.id})
    assert member is None


def test_list_leave_requests_auto_approves_expired(client, make_user, make_club, join_club, auth_cookie, db):
    leader = make_user()
    user = make_user()
    club = make_club()
    join_club(leader, club, role=enums.ROLE_LEADER)
    join_club(user, club)

    old = LeaveRequest(user_id=user.id, club_id=club.id, status=enums.REQ_PENDING)
    db.add(old)
    db.commit()
    old.created_at = utcnow() - timedelta(days=8)
    db.commit()

    r = client.get(f"/api/clubs/{club.id}/leave-requests", cookies=auth_cookie(leader))
    assert r.status_code == 200
    # 자동 승인된 건은 처리가 끝났으므로 목록에서 빠진다 (목록은 '할 일'만 담는다)
    assert all(i["id"] != old.id for i in r.json())
    db.refresh(old)
    assert old.status == enums.REQ_APPROVED

    member = db.get(ClubMember, {"user_id": user.id, "club_id": club.id})
    assert member is None
