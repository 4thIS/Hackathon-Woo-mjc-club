"""T3 — GET /api/clubs/{id} 의 my.join_request_status. 명세: docs/api.md §3 (TODO(T3) 반영)"""

from app import enums


def test_join_request_status_pending(client, make_user, make_club, auth_cookie):
    user = make_user()
    club = make_club()
    client.post(f"/api/clubs/{club.id}/join-requests", json={"answers": {}}, cookies=auth_cookie(user))

    r = client.get(f"/api/clubs/{club.id}", cookies=auth_cookie(user))
    assert r.json()["my"]["join_request_status"] == "심사중"


def test_join_request_status_rejected(client, make_user, make_club, join_club, auth_cookie):
    leader = make_user()
    user = make_user()
    club = make_club()
    join_club(leader, club, role=enums.ROLE_LEADER)

    r1 = client.post(f"/api/clubs/{club.id}/join-requests", json={"answers": {}}, cookies=auth_cookie(user))
    req_id = r1.json()["id"]
    client.post(f"/api/join-requests/{req_id}/reject", json={}, cookies=auth_cookie(leader))

    r = client.get(f"/api/clubs/{club.id}", cookies=auth_cookie(user))
    assert r.json()["my"]["join_request_status"] == "거절"


def test_join_request_status_none_when_no_request(client, make_user, make_club, auth_cookie):
    user = make_user()
    club = make_club()
    r = client.get(f"/api/clubs/{club.id}", cookies=auth_cookie(user))
    assert r.json()["my"]["join_request_status"] is None
