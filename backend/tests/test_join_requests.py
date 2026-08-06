"""T3 — 가입 신청. 명세: docs/api.md §4"""

from app import enums


def test_create_join_request_success(client, make_user, make_club, auth_cookie):
    user = make_user()
    club = make_club(recruit_status=enums.RECRUIT_MOJIP)
    r = client.post(
        f"/api/clubs/{club.id}/join-requests",
        json={"answers": {"motive": "배우고 싶습니다"}},
        cookies=auth_cookie(user),
    )
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "심사중"
    assert isinstance(body["id"], int)


def test_join_request_already_member(client, make_user, make_club, join_club, auth_cookie):
    user = make_user()
    club = make_club()
    join_club(user, club)
    r = client.post(f"/api/clubs/{club.id}/join-requests", json={"answers": {}}, cookies=auth_cookie(user))
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "ALREADY_MEMBER"


def test_join_request_ob_forbidden(client, make_user, make_club, auth_cookie):
    user = make_user(academic_status=enums.ACADEMIC_GRADUATED)
    club = make_club()
    r = client.post(f"/api/clubs/{club.id}/join-requests", json={"answers": {}}, cookies=auth_cookie(user))
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "OB_NOT_ALLOWED"


def test_join_request_duplicate_pending(client, make_user, make_club, auth_cookie):
    user = make_user()
    club = make_club()
    client.post(f"/api/clubs/{club.id}/join-requests", json={"answers": {}}, cookies=auth_cookie(user))
    r = client.post(f"/api/clubs/{club.id}/join-requests", json={"answers": {}}, cookies=auth_cookie(user))
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "ALREADY_REQUESTED"


def test_join_request_club_not_recruiting(client, make_user, make_club, auth_cookie):
    user = make_user()
    club = make_club(recruit_status=enums.RECRUIT_CLOSED)
    r = client.post(f"/api/clubs/{club.id}/join-requests", json={"answers": {}}, cookies=auth_cookie(user))
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "CLUB_NOT_RECRUITING"


def test_join_request_form_required_blocks_empty_answer(
    client, make_user, make_club, join_club, auth_cookie
):
    leader = make_user()
    user = make_user()
    club = make_club()
    join_club(leader, club, role=enums.ROLE_LEADER)
    client.put(
        f"/api/clubs/{club.id}/join-form",
        json={
            "required": True,
            "fields": [{"key": "motive", "label": "지원 동기", "type": "text", "required": True}],
        },
        cookies=auth_cookie(leader),
    )

    r = client.post(f"/api/clubs/{club.id}/join-requests", json={"answers": {}}, cookies=auth_cookie(user))
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "FORM_REQUIRED"

    r2 = client.post(
        f"/api/clubs/{club.id}/join-requests",
        json={"answers": {"motive": "배우고 싶습니다"}},
        cookies=auth_cookie(user),
    )
    assert r2.status_code == 201


def test_join_request_after_reject_can_reapply(client, make_user, make_club, join_club, auth_cookie):
    leader = make_user()
    user = make_user()
    club = make_club()
    join_club(leader, club, role=enums.ROLE_LEADER)

    r1 = client.post(f"/api/clubs/{club.id}/join-requests", json={"answers": {}}, cookies=auth_cookie(user))
    req_id = r1.json()["id"]
    r2 = client.post(f"/api/join-requests/{req_id}/reject", json={}, cookies=auth_cookie(leader))
    assert r2.status_code == 200
    assert r2.json()["status"] == "거절"

    r3 = client.post(f"/api/clubs/{club.id}/join-requests", json={"answers": {}}, cookies=auth_cookie(user))
    assert r3.status_code == 201


def test_list_join_requests_hides_sensitive_fields(client, make_user, make_club, join_club, auth_cookie):
    leader = make_user()
    user = make_user(name="박찬우")
    club = make_club()
    join_club(leader, club, role=enums.ROLE_LEADER)
    client.post(
        f"/api/clubs/{club.id}/join-requests", json={"answers": {"motive": "x"}}, cookies=auth_cookie(user)
    )

    r = client.get(f"/api/clubs/{club.id}/join-requests", cookies=auth_cookie(leader))
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 1
    item = items[0]
    assert item["name"] == "박찬우"
    assert item["dept"] == "컴퓨터공학과"
    assert "grade" in item
    assert item["answers"] == {"motive": "x"}
    assert set(item) == {"id", "name", "dept", "grade", "answers", "created_at", "status"}


def test_list_join_requests_requires_leader(client, make_user, make_club, auth_cookie):
    user = make_user()
    club = make_club()
    r = client.get(f"/api/clubs/{club.id}/join-requests", cookies=auth_cookie(user))
    assert r.status_code == 403


def test_approve_join_assigns_current_gen_and_creates_membership(
    client, make_user, make_club, join_club, auth_cookie, db
):
    leader = make_user()
    user = make_user()
    club = make_club(current_gen=12)
    join_club(leader, club, role=enums.ROLE_LEADER)

    r1 = client.post(f"/api/clubs/{club.id}/join-requests", json={"answers": {}}, cookies=auth_cookie(user))
    req_id = r1.json()["id"]

    r2 = client.post(f"/api/join-requests/{req_id}/approve", cookies=auth_cookie(leader))
    assert r2.status_code == 200
    assert r2.json() == {"status": "승인", "gen": 12}

    from app.models import ClubMember

    member = db.get(ClubMember, {"user_id": user.id, "club_id": club.id})
    assert member is not None
    assert member.gen == 12
    assert member.role == "부원"
    assert member.membership == "활동중"


def test_approve_join_requires_leader_of_that_club(client, make_user, make_club, join_club, auth_cookie):
    outsider = make_user()
    user = make_user()
    club = make_club()

    r1 = client.post(f"/api/clubs/{club.id}/join-requests", json={"answers": {}}, cookies=auth_cookie(user))
    req_id = r1.json()["id"]

    r2 = client.post(f"/api/join-requests/{req_id}/approve", cookies=auth_cookie(outsider))
    assert r2.status_code == 403


def test_cancel_join_request_by_owner(client, make_user, make_club, auth_cookie):
    user = make_user()
    club = make_club()
    r1 = client.post(f"/api/clubs/{club.id}/join-requests", json={"answers": {}}, cookies=auth_cookie(user))
    req_id = r1.json()["id"]

    r2 = client.delete(f"/api/join-requests/{req_id}", cookies=auth_cookie(user))
    assert r2.status_code == 200
    assert r2.json()["status"] == "취소"


def test_cancel_join_request_forbidden_for_others(client, make_user, make_club, auth_cookie):
    user = make_user()
    other = make_user()
    club = make_club()
    r1 = client.post(f"/api/clubs/{club.id}/join-requests", json={"answers": {}}, cookies=auth_cookie(user))
    req_id = r1.json()["id"]

    r2 = client.delete(f"/api/join-requests/{req_id}", cookies=auth_cookie(other))
    assert r2.status_code == 403


def test_processed_requests_leave_the_leader_list(client, make_user, make_club, join_club, auth_cookie):
    """승인·거절한 신청은 동아리장 목록에서 빠진다 — 이 화면은 '할 일 목록'이다."""
    leader = make_user(verified=True)
    club = make_club()
    join_club(leader, club, role="동아리장")

    ids = []
    for _ in range(3):
        applicant = make_user(verified=True)
        r = client.post(f"/api/clubs/{club.id}/join-requests", json={"answers": {}},
                        cookies=auth_cookie(applicant))
        assert r.status_code == 201
        ids.append(r.json()["id"])

    lead = auth_cookie(leader)
    assert len(client.get(f"/api/clubs/{club.id}/join-requests", cookies=lead).json()) == 3

    assert client.post(f"/api/join-requests/{ids[0]}/approve", cookies=lead).status_code == 200
    assert client.post(f"/api/join-requests/{ids[1]}/reject", json={"reason": "정원 초과"},
                       cookies=lead).status_code == 200

    left = client.get(f"/api/clubs/{club.id}/join-requests", cookies=lead).json()
    assert [r["id"] for r in left] == [ids[2]]
    assert all(r["status"] == "심사중" for r in left)
