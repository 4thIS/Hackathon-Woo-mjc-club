"""T4-C — 관리자 동아리 관리. 명세: docs/api.md §5

권한은 원래 있었다(`deps.club_leader` 가 관리자를 통과시킨다). 없던 건 목록이다 —
공개 목록이 활동중만 주기 때문에 관리자가 보관된 동아리에 도달할 수 없었다.
"""

from app import enums


def test_list_requires_admin(client, make_user, auth_cookie):
    user = make_user()
    assert client.get("/api/admin/clubs", cookies=auth_cookie(user)).status_code == 403


def test_archived_clubs_are_visible_to_admin_only(client, make_user, make_club, auth_cookie):
    """공개 목록에서 사라진 동아리도 관리자는 봐야 되살릴 수 있다."""
    admin = make_user(admin=True)
    club = make_club(status=enums.CLUB_ARCHIVED)

    public = client.get("/api/clubs").json()["items"]
    assert club.id not in [c["id"] for c in public]

    mine = client.get("/api/admin/clubs", params={"q": club.name},
                      cookies=auth_cookie(admin)).json()
    assert [c["id"] for c in mine["items"]] == [club.id]
    assert mine["items"][0]["status"] == enums.CLUB_ARCHIVED


def test_list_shows_leader_and_counts(client, make_user, make_club, join_club, auth_cookie):
    admin = make_user(admin=True)
    leader = make_user(name="동아리장이름")
    member = make_user()
    club = make_club()
    join_club(leader, club, role=enums.ROLE_LEADER)
    join_club(member, club)

    item = client.get("/api/admin/clubs", params={"q": club.name},
                      cookies=auth_cookie(admin)).json()["items"][0]
    assert item["leader"]["name"] == "동아리장이름"
    assert item["member_count"] == 2
    assert item["post_count"] == 0


def test_leaderless_club_is_flagged(client, make_user, make_club, auth_cookie):
    """동아리장이 없으면 강제 교체 대상이다 (기획서 §5.5)."""
    admin = make_user(admin=True)
    club = make_club()

    item = client.get("/api/admin/clubs", params={"q": club.name},
                      cookies=auth_cookie(admin)).json()["items"][0]
    assert item["leader"] is None


def test_filters(client, make_user, make_club, auth_cookie):
    admin = make_user(admin=True)
    make_club(status=enums.CLUB_ARCHIVED)
    make_club(category="체육")

    archived = client.get("/api/admin/clubs", params={"status": "보관"},
                          cookies=auth_cookie(admin)).json()
    assert all(c["status"] == "보관" for c in archived["items"])

    sports = client.get("/api/admin/clubs", params={"category": "체육"},
                        cookies=auth_cookie(admin)).json()
    assert all(c["category"] == "체육" for c in sports["items"])


def test_admin_can_archive_and_restore(client, make_user, make_club, auth_cookie):
    """삭제가 아니라 보관이다 — 활동 기록은 남는다 (기획서 §5.6)."""
    admin = make_user(admin=True)
    club = make_club()

    r = client.patch(f"/api/admin/clubs/{club.id}", json={"status": "보관"},
                     cookies=auth_cookie(admin))
    assert r.status_code == 200
    assert club.id not in [c["id"] for c in client.get("/api/clubs").json()["items"]]

    client.patch(f"/api/admin/clubs/{club.id}", json={"status": "활동중"},
                 cookies=auth_cookie(admin))
    assert club.id in [c["id"] for c in client.get("/api/clubs").json()["items"]]


def test_admin_can_force_transfer_leader(client, make_user, make_club, join_club, auth_cookie, db):
    """동아리장이 잠수하면 동아리가 마비된다. 관리자가 풀어준다 (기획서 §5.5)."""
    admin = make_user(admin=True)
    old = make_user()
    new = make_user()
    club = make_club()
    join_club(old, club, role=enums.ROLE_LEADER)
    join_club(new, club)

    r = client.patch(f"/api/admin/clubs/{club.id}", json={"leader_id": new.id},
                     cookies=auth_cookie(admin))
    assert r.status_code == 200

    db.expire_all()
    item = client.get("/api/admin/clubs", params={"q": club.name},
                      cookies=auth_cookie(admin)).json()["items"][0]
    assert item["leader"]["id"] == new.id


def test_admin_can_edit_any_club(client, make_user, make_club, auth_cookie):
    """관리자는 동아리장 전용 API 도 통과한다 (deps.club_leader)."""
    admin = make_user(admin=True)
    club = make_club()

    r = client.patch(f"/api/clubs/{club.id}", json={"recruit_status": "모집마감"},
                     cookies=auth_cookie(admin))
    assert r.status_code == 200
    assert client.get(f"/api/clubs/{club.id}").json()["recruit_status"] == "모집마감"
