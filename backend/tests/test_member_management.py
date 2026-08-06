"""T4 — 부원 관리·동아리 정보수정·위임. 명세: docs/api.md §4"""

from app import enums
from app.models import ClubMember


def test_manage_members_lists_role_membership_gen(client, make_user, make_club, join_club, auth_cookie):
    leader = make_user()
    member = make_user()
    club = make_club()
    join_club(leader, club, role=enums.ROLE_LEADER, gen=1)
    join_club(member, club, gen=5)

    r = client.get(f"/api/clubs/{club.id}/members/manage", cookies=auth_cookie(leader))
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 2
    entry = next(i for i in items if i["user"]["id"] == member.id)
    assert entry["role"] == "부원"
    assert entry["membership"] == "활동중"
    assert entry["gen"] == 5


def test_manage_members_requires_leader(client, make_user, make_club, join_club, auth_cookie):
    member = make_user()
    club = make_club()
    join_club(member, club)
    r = client.get(f"/api/clubs/{club.id}/members/manage", cookies=auth_cookie(member))
    assert r.status_code == 403


def test_leader_can_update_member_gen(client, make_user, make_club, join_club, auth_cookie, db):
    leader = make_user()
    member = make_user()
    club = make_club()
    join_club(leader, club, role=enums.ROLE_LEADER)
    join_club(member, club, gen=5)

    r = client.patch(
        f"/api/clubs/{club.id}/members/{member.id}", json={"gen": 6}, cookies=auth_cookie(leader)
    )
    assert r.status_code == 200

    m = db.get(ClubMember, {"user_id": member.id, "club_id": club.id})
    assert m.gen == 6


def test_update_club_info(client, make_user, make_club, join_club, auth_cookie, db):
    leader = make_user()
    club = make_club()
    join_club(leader, club, role=enums.ROLE_LEADER)

    r = client.patch(
        f"/api/clubs/{club.id}",
        json={"purpose": "새 목적", "recruit_status": "모집마감", "current_gen": 13},
        cookies=auth_cookie(leader),
    )
    assert r.status_code == 200
    assert r.json()["purpose"] == "새 목적"
    assert r.json()["recruit_status"] == "모집마감"
    assert r.json()["current_gen"] == 13


def test_transfer_leader_to_active_member(client, make_user, make_club, join_club, auth_cookie, db):
    leader = make_user()
    member = make_user()
    club = make_club()
    join_club(leader, club, role=enums.ROLE_LEADER)
    join_club(member, club)

    r = client.post(
        f"/api/clubs/{club.id}/transfer", json={"user_id": member.id}, cookies=auth_cookie(leader)
    )
    assert r.status_code == 200

    new_leader = db.get(ClubMember, {"user_id": member.id, "club_id": club.id})
    old_leader = db.get(ClubMember, {"user_id": leader.id, "club_id": club.id})
    assert new_leader.role == "동아리장"
    assert old_leader.role == "부원"


def test_transfer_leader_rejects_non_active_target(client, make_user, make_club, join_club, auth_cookie):
    leader = make_user()
    club = make_club()
    join_club(leader, club, role=enums.ROLE_LEADER)

    r = client.post(
        f"/api/clubs/{club.id}/transfer", json={"user_id": "00000000"}, cookies=auth_cookie(leader)
    )
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "TARGET_NOT_ACTIVE_MEMBER"
