"""T4-C — 관리자 유저 관리. 명세: docs/api.md §5

기획서 §4.3 이 잠긴 필드에 대해 "변경이 필요하면 관리자 문의" 라고 안내한다.
그 약속을 지키는 화면이 여기다 — 관리자는 이름·생년월일·성별·이메일까지 고칠 수 있다.
"""

from app import enums


def test_list_requires_admin(client, make_user, auth_cookie):
    user = make_user()
    assert client.get("/api/admin/users", cookies=auth_cookie(user)).status_code == 403


def test_list_returns_clubs_with_each_user(client, make_user, make_club, join_club, auth_cookie):
    """졸업 전환이 막히는 이유를 화면에서 미리 보여주려면 소속이 함께 와야 한다."""
    admin = make_user(admin=True)
    leader = make_user(name="목록확인용")
    club = make_club()
    join_club(leader, club, role=enums.ROLE_LEADER)

    r = client.get("/api/admin/users", params={"q": leader.id}, cookies=auth_cookie(admin))
    assert r.status_code == 200
    item = next(u for u in r.json()["items"] if u["id"] == leader.id)
    assert item["clubs"][0]["role"] == enums.ROLE_LEADER
    assert item["clubs"][0]["name"] == club.name


def test_search_and_filters(client, make_user, auth_cookie):
    admin = make_user(admin=True)
    target = make_user(name="검색대상자")
    make_user(academic_status=enums.ACADEMIC_GRADUATED)

    hit = client.get("/api/admin/users", params={"q": "검색대상자"}, cookies=auth_cookie(admin))
    assert [u["id"] for u in hit.json()["items"]] == [target.id]

    grad = client.get("/api/admin/users", params={"status": "졸업"}, cookies=auth_cookie(admin))
    assert all(u["academic_status"] == "졸업" for u in grad.json()["items"])

    adm = client.get("/api/admin/users", params={"admin": "true"}, cookies=auth_cookie(admin))
    assert all(u["is_admin"] for u in adm.json()["items"])


def test_admin_can_edit_locked_fields(client, make_user, auth_cookie):
    """본인은 못 바꾸는 이름·생년월일·성별을 관리자는 바꾼다 (기획서 §4.3)."""
    admin = make_user(admin=True)
    user = make_user(name="원래이름")

    r = client.patch(
        f"/api/admin/users/{user.id}",
        json={"name": "바뀐이름", "gender": "여", "birth": "2004-02-02", "dept": "전기공학과"},
        cookies=auth_cookie(admin),
    )
    assert r.status_code == 200
    d = r.json()
    assert (d["name"], d["gender"], d["birth"], d["dept"]) == (
        "바뀐이름", "여", "2004-02-02", "전기공학과",
    )


def test_email_rules_match_signup(client, make_user, auth_cookie):
    admin = make_user(admin=True)
    user = make_user()

    bad_domain = client.patch(f"/api/admin/users/{user.id}",
                              json={"email": f"{user.id}@gmail.com"}, cookies=auth_cookie(admin))
    assert bad_domain.json()["detail"]["code"] == "INVALID_EMAIL_DOMAIN"

    # 학번과 다른 로컬파트도 허용한다 (가입과 같은 규칙)
    free = client.patch(f"/api/admin/users/{user.id}",
                        json={"email": "hongkildong@mjc.ac.kr"}, cookies=auth_cookie(admin))
    assert free.status_code == 200
    assert free.json()["email"] == "hongkildong@mjc.ac.kr"

    ok = client.patch(f"/api/admin/users/{user.id}",
                      json={"email": f"{user.id}@on.mjc.ac.kr"}, cookies=auth_cookie(admin))
    assert ok.status_code == 200
    assert ok.json()["email"] == f"{user.id}@on.mjc.ac.kr"


def test_leader_cannot_be_graduated_even_by_admin(client, make_user, make_club, join_club, auth_cookie):
    """동아리장이 OB 가 되면 그 동아리가 마비된다. 관리자도 예외가 아니다 (기획서 §4.3)."""
    admin = make_user(admin=True)
    leader = make_user()
    join_club(leader, make_club(), role=enums.ROLE_LEADER)

    r = client.patch(f"/api/admin/users/{leader.id}",
                     json={"academic_status": "졸업"}, cookies=auth_cookie(admin))
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "LEADER_CANNOT_GRADUATE"


def test_graduation_turns_memberships_into_ob(client, make_user, make_club, join_club, auth_cookie):
    admin = make_user(admin=True)
    member = make_user()
    join_club(member, make_club())
    join_club(member, make_club())

    r = client.patch(f"/api/admin/users/{member.id}",
                     json={"academic_status": "졸업"}, cookies=auth_cookie(admin))
    assert r.status_code == 200
    assert [c["membership"] for c in r.json()["clubs"]] == ["OB", "OB"]


def test_last_admin_cannot_be_demoted(client, make_user, auth_cookie, db):
    """관리자가 0명이 되면 아무도 되돌릴 수 없다."""
    from app.models import User

    admin = make_user(admin=True)
    # 이 테스트 동안만 유일한 관리자로 만든다
    others = db.query(User).filter(User.is_admin.is_(True), User.id != admin.id).all()
    for o in others:
        o.is_admin = False
    db.commit()
    try:
        r = client.patch(f"/api/admin/users/{admin.id}",
                         json={"is_admin": False}, cookies=auth_cookie(admin))
        assert r.status_code == 409
        assert r.json()["detail"]["code"] == "LAST_ADMIN"
        # 실제로 막혔는지 — 권한이 남아 있어야 조회가 된다
        assert client.get("/api/admin/users", cookies=auth_cookie(admin)).status_code == 200
    finally:
        for o in others:
            o.is_admin = True
        db.commit()


def test_admin_can_be_demoted_when_another_exists(client, make_user, auth_cookie):
    keeper = make_user(admin=True)
    spare = make_user(admin=True)

    r = client.patch(f"/api/admin/users/{spare.id}",
                     json={"is_admin": False}, cookies=auth_cookie(keeper))
    assert r.status_code == 200
    assert r.json()["is_admin"] is False


def test_unknown_user_is_404(client, make_user, auth_cookie):
    admin = make_user(admin=True)
    r = client.patch("/api/admin/users/00000001", json={"dept": "X"}, cookies=auth_cookie(admin))
    assert r.status_code == 404
