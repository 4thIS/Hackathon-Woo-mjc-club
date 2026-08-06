"""시드 데이터의 규칙을 고정한다.

동아리 정보는 학교 공개 자료이고, 활동 글은 데모용 창작이다.
'동아리장이 있는 동아리만 모집중' 규칙이 깨지면 승인해줄 사람 없는 곳에
신입생이 신청하게 된다.
"""

from app import enums
from seed import CLUBS, DEMO_LED, POSTS


def test_loads_25_clubs_from_json():
    assert len(CLUBS) == 25


def test_every_category_is_a_known_enum_value():
    assert {c["category"] for c in CLUBS} <= set(enums.CATEGORIES)


def test_school_categories_are_present():
    assert {c["category"] for c in CLUBS} == {"학술·전공", "체육", "봉사", "종교"}


def test_only_demo_led_clubs_are_recruiting():
    """승인해줄 동아리장이 없는 곳을 모집중으로 두지 않는다."""
    for c in CLUBS:
        recruiting = c["recruit_status"] != enums.RECRUIT_CLOSED
        assert recruiting == (c["name"] in DEMO_LED), c["name"]


def test_posts_only_attach_to_demo_led_clubs():
    assert {p[0] for p in POSTS} <= set(DEMO_LED)


def test_enough_clubs_have_public_posts_for_the_carousel():
    """캐러셀은 동아리당 1건만 뽑는다. 6개 미만이면 허전해진다 (api.md §9-4)."""
    with_public = {p[0] for p in POSTS if p[5]}
    assert len(with_public) >= 6


def test_purpose_carries_main_activities():
    assert any("주요사업:" in c["purpose"] for c in CLUBS)
