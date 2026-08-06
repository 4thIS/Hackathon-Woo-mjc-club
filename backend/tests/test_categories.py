"""분야 열거값 — 학교 공식 분류(봉사·학술·체육·종교)를 담을 수 있어야 한다."""

from app import enums
from app.models import Club


def test_religion_category_exists():
    assert "종교" in enums.CATEGORIES


def test_club_can_be_created_with_religion_category(client, db):
    club = Club(name="테스트종교동아리_T1", category="종교", founded_year=1974)
    db.add(club)
    db.commit()
    try:
        r = client.get("/api/clubs", params={"category": "종교"})
        assert r.status_code == 200
        assert "테스트종교동아리_T1" in [c["name"] for c in r.json()["items"]]
    finally:
        db.query(Club).filter(Club.id == club.id).delete()
        db.commit()


def test_stats_counts_used_categories_not_enum_length(client, db):
    """지표는 열거값 개수가 아니라 화면에서 셀 수 있는 값이어야 한다."""
    used = {c.category for c in db.query(Club).all()}
    assert client.get("/api/stats").json()["categories"] == len(used)


def test_stats_excludes_categories_only_used_by_archived_clubs(client, db):
    """보관 상태 동아리만 가진 분야는 stats().categories 에서 빠져야 한다.

    구현(routers/clubs.py stats())은 Club.status == enums.CLUB_ACTIVE 로 거른다.
    이 테스트는 그 필터가 실제로 동작하는지 직접 확인한다 — 상태 필터 없이 세면
    보관 전용 분야도 잡혀서 통과해버린다.
    """
    active_categories = {
        c.category for c in db.query(Club).filter(Club.status == enums.CLUB_ACTIVE).all()
    }
    candidates = [c for c in enums.CATEGORIES if c not in active_categories]
    assert candidates, "활동중 동아리가 모든 분야를 이미 쓰고 있어 테스트 전제가 깨졌다"
    archived_only_category = candidates[0]

    before = client.get("/api/stats").json()["categories"]

    club = Club(
        name="테스트보관동아리_T1",
        category=archived_only_category,
        founded_year=2000,
        status=enums.CLUB_ARCHIVED,
    )
    db.add(club)
    db.commit()
    try:
        after = client.get("/api/stats").json()["categories"]
        assert after == before
    finally:
        db.query(Club).filter(Club.id == club.id).delete()
        db.commit()
