"""동아리장의 부원 상태 관리. 명세: docs/api.md §4

기획서 §3.1 의 두 축을 지킨다 — 학적은 사람 전역 값이라 동아리장이 못 바꾸고,
동아리 안에서의 상태(membership)만 다룬다.
"""

from app import enums
from app.models import ClubMember, LeaveRequest


def test_leader_can_move_member_to_ob(client, make_user, make_club, join_club, auth_cookie):
    leader = make_user()
    member = make_user()
    club = make_club()
    join_club(leader, club, role=enums.ROLE_LEADER)
    join_club(member, club)

    r = client.patch(f"/api/clubs/{club.id}/members/{member.id}",
                     json={"membership": "OB"}, cookies=auth_cookie(leader))
    assert r.status_code == 200
    assert r.json()["membership"] == "OB"


def test_gen_and_membership_are_independent(client, make_user, make_club, join_club, auth_cookie):
    """보낸 것만 바뀐다 — 기수만 고칠 때 멤버십이 날아가면 안 된다."""
    leader = make_user()
    member = make_user()
    club = make_club()
    join_club(leader, club, role=enums.ROLE_LEADER)
    join_club(member, club, membership=enums.MEMBERSHIP_OB, gen=3)

    r = client.patch(f"/api/clubs/{club.id}/members/{member.id}",
                     json={"gen": 7}, cookies=auth_cookie(leader))
    assert r.status_code == 200
    assert (r.json()["gen"], r.json()["membership"]) == (7, "OB")


def test_leader_cannot_become_ob(client, make_user, make_club, join_club, auth_cookie):
    """동아리장이 OB 가 되면 그 동아리가 마비된다 (기획서 §4.3 과 같은 불변식)."""
    leader = make_user()
    club = make_club()
    join_club(leader, club, role=enums.ROLE_LEADER)

    r = client.patch(f"/api/clubs/{club.id}/members/{leader.id}",
                     json={"membership": "OB"}, cookies=auth_cookie(leader))
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "LEADER_MUST_STAY_ACTIVE"


def test_invalid_membership_rejected(client, make_user, make_club, join_club, auth_cookie):
    leader = make_user()
    member = make_user()
    club = make_club()
    join_club(leader, club, role=enums.ROLE_LEADER)
    join_club(member, club)

    r = client.patch(f"/api/clubs/{club.id}/members/{member.id}",
                     json={"membership": "졸업"}, cookies=auth_cookie(leader))
    assert r.status_code == 400


def test_manage_list_exposes_academic_status(client, make_user, make_club, join_club, auth_cookie):
    """읽기 전용으로 보여준다 — 동아리장이 OB 전환을 판단하는 근거다."""
    leader = make_user()
    member = make_user(academic_status=enums.ACADEMIC_GRADUATED)
    club = make_club()
    join_club(leader, club, role=enums.ROLE_LEADER)
    join_club(member, club)

    rows = client.get(f"/api/clubs/{club.id}/members/manage",
                      cookies=auth_cookie(leader)).json()
    row = next(x for x in rows if x["user"]["id"] == member.id)
    assert row["academic_status"] == enums.ACADEMIC_GRADUATED


def test_leader_can_remove_member(client, make_user, make_club, join_club, auth_cookie, db):
    leader = make_user()
    member = make_user()
    club = make_club()
    join_club(leader, club, role=enums.ROLE_LEADER)
    join_club(member, club)

    r = client.request("DELETE", f"/api/clubs/{club.id}/members/{member.id}",
                       cookies=auth_cookie(leader))
    assert r.status_code == 204

    db.expunge_all()
    assert db.get(ClubMember, {"user_id": member.id, "club_id": club.id}) is None


def test_removing_member_closes_pending_leave_request(client, make_user, make_club, join_club,
                                                      auth_cookie, db):
    """심사중 요청이 남으면 탈퇴 요청 목록에 유령 항목이 된다."""
    leader = make_user()
    member = make_user()
    club = make_club()
    join_club(leader, club, role=enums.ROLE_LEADER)
    join_club(member, club)
    db.add(LeaveRequest(user_id=member.id, club_id=club.id, status=enums.REQ_PENDING))
    db.commit()

    client.request("DELETE", f"/api/clubs/{club.id}/members/{member.id}",
                   cookies=auth_cookie(leader))

    db.expire_all()
    left = db.query(LeaveRequest).filter(
        LeaveRequest.user_id == member.id, LeaveRequest.club_id == club.id
    ).all()
    assert all(x.status != enums.REQ_PENDING for x in left)


def test_cannot_remove_leader(client, make_user, make_club, join_club, auth_cookie):
    leader = make_user()
    club = make_club()
    join_club(leader, club, role=enums.ROLE_LEADER)

    r = client.request("DELETE", f"/api/clubs/{club.id}/members/{leader.id}",
                       cookies=auth_cookie(leader))
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "CANNOT_REMOVE_LEADER"


def test_member_cannot_manage_others(client, make_user, make_club, join_club, auth_cookie):
    leader = make_user()
    member = make_user()
    other = make_user()
    club = make_club()
    join_club(leader, club, role=enums.ROLE_LEADER)
    join_club(member, club)
    join_club(other, club)

    assert client.patch(f"/api/clubs/{club.id}/members/{other.id}",
                        json={"gen": 2}, cookies=auth_cookie(member)).status_code == 403
    assert client.request("DELETE", f"/api/clubs/{club.id}/members/{other.id}",
                          cookies=auth_cookie(member)).status_code == 403
