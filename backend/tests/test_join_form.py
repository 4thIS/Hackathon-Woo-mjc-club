"""T3 — 가입폼. 명세: docs/api.md §4"""


def test_join_form_defaults_when_missing(client, make_club):
    club = make_club()
    r = client.get(f"/api/clubs/{club.id}/join-form")
    assert r.status_code == 200
    assert r.json() == {"required": False, "fields": []}


def test_leader_can_set_join_form(client, make_user, make_club, join_club, auth_cookie):
    leader = make_user()
    club = make_club()
    join_club(leader, club, role="동아리장")

    payload = {
        "required": True,
        "fields": [{"key": "motive", "label": "지원 동기", "type": "text", "required": True}],
    }
    r = client.put(f"/api/clubs/{club.id}/join-form", json=payload, cookies=auth_cookie(leader))
    assert r.status_code == 200
    assert r.json() == payload

    r2 = client.get(f"/api/clubs/{club.id}/join-form")
    assert r2.json() == payload


def test_non_leader_cannot_set_join_form(client, make_user, make_club, auth_cookie):
    user = make_user()
    club = make_club()
    r = client.put(
        f"/api/clubs/{club.id}/join-form",
        json={"required": False, "fields": []},
        cookies=auth_cookie(user),
    )
    assert r.status_code == 403
