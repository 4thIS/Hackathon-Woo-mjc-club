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
