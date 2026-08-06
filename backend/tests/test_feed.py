"""전체 피드 — GET /api/posts. 명세: docs/api.md §3

동아리 타임라인과 두 가지가 다르다: **최신순**이고, 동아리를 가리지 않는다.
비공개 글이 남의 동아리 것까지 섞이면 초상권 사고이므로 그 경계를 테스트로 고정한다.
"""

from datetime import date

import pytest

from app import enums
from app.models import ClubMember, Post


@pytest.fixture
def feed_data(db, make_user, make_club):
    """두 동아리 × (공개 2 + 비공개 1). 날짜를 섞어 두어 정렬을 검증할 수 있게 한다.

    이름은 `make_club` 기본값(매번 다른 이름)을 그대로 쓴다 — clubs.name 이 unique 라
    고정 문자열을 쓰면 이 픽스처를 두 번째 쓰는 테스트에서 충돌한다.
    """
    a = make_club(category=enums.CATEGORIES[0])
    b = make_club(category=enums.CATEGORIES[2])
    author = make_user(name="글쓴이")

    rows = [
        (a, "성북동 출사", "필름 두 롤을 현상했습니다.", date(2026, 5, 1), ["출사"], True),
        (a, "비공개 회의록", "내부 논의 기록입니다.", date(2026, 5, 20), [], False),
        (b, "주말 리그 3차전", "연장까지 갔습니다.", date(2026, 6, 10), ["리그"], True),
        (b, "정기 연습", "기초 훈련을 했습니다.", date(2026, 4, 2), ["연습"], True),
    ]
    posts = []
    for club, title, body, when, tags, public in rows:
        p = Post(
            club_id=club.id,
            author_id=author.id,
            title=title,
            body=body,
            photos=[],
            activity_date=when,
            tags=tags,
            is_public=public,
        )
        db.add(p)
        posts.append(p)
    db.commit()

    yield {"a": a, "b": b, "author": author, "posts": posts}

    # 테스트마다 지운다. conftest 는 세션 시작·끝에만 쓸어내므로, 여기서 안 지우면
    # 2026년 날짜의 공개 글이 14개 테스트만큼 쌓여 **다른 테스트의 캐러셀(동아리당 1건,
    # 최신 20건)을 밀어낸다.** 실제로 test_t2 가 그렇게 깨졌다.
    for p in posts:
        db.delete(p)
    db.commit()
    for club in (a, b):
        db.query(ClubMember).filter_by(club_id=club.id).delete()
        db.delete(club)
    db.commit()


def titles(res):
    return [it["title"] for it in res.json()["items"]]


def test_비로그인은_공개글만_최신순으로_본다(client, feed_data):
    res = client.get("/api/posts", params={"limit": 30})
    assert res.status_code == 200

    got = titles(res)
    assert "비공개 회의록" not in got
    # 최신순 — 6/10 → 5/1 → 4/2
    mine = [t for t in got if t in {"주말 리그 3차전", "성북동 출사", "정기 연습"}]
    assert mine == ["주말 리그 3차전", "성북동 출사", "정기 연습"]


def test_여러_동아리_글이_한_피드에_섞인다(client, feed_data):
    res = client.get("/api/posts", params={"limit": 30})
    names = {it["club_name"] for it in res.json()["items"]}
    assert {feed_data["a"].name, feed_data["b"].name} <= names


def test_소속_부원은_자기_동아리_비공개_글을_본다(
    client, feed_data, make_user, join_club, auth_cookie
):
    member = make_user()
    join_club(member, feed_data["a"])

    got = titles(client.get("/api/posts", params={"limit": 30}, cookies=auth_cookie(member)))
    assert "비공개 회의록" in got


def test_남의_동아리_비공개_글은_보이지_않는다(
    client, feed_data, make_user, join_club, auth_cookie
):
    outsider = make_user()
    join_club(outsider, feed_data["b"])          # B 소속인데 비공개 글은 A 것이다

    got = titles(client.get("/api/posts", params={"limit": 30}, cookies=auth_cookie(outsider)))
    assert "비공개 회의록" not in got


def test_관리자는_모든_비공개_글을_본다(client, feed_data, make_user, auth_cookie):
    admin = make_user(admin=True)
    got = titles(client.get("/api/posts", params={"limit": 30}, cookies=auth_cookie(admin)))
    assert "비공개 회의록" in got


def test_제목으로_검색한다(client, feed_data):
    """세션 DB 에는 다른 테스트가 만든 글도 남아 있다 — 포함 여부와 조건 충족만 본다."""
    got = titles(client.get("/api/posts", params={"q": "출사", "limit": 30}))
    assert "성북동 출사" in got
    assert all("출사" in t for t in got)


def test_본문으로_검색한다(client, feed_data):
    ids = {it["id"] for it in client.get("/api/posts", params={"q": "연장까지", "limit": 30}).json()["items"]}
    target = next(p for p in feed_data["posts"] if p.title == "주말 리그 3차전")
    assert target.id in ids


def test_동아리명으로_검색한다(client, feed_data):
    b = feed_data["b"].name
    res = client.get("/api/posts", params={"q": b, "limit": 30})
    assert {it["club_name"] for it in res.json()["items"]} == {b}


def test_태그로_검색한다(client, feed_data):
    got = titles(client.get("/api/posts", params={"q": "리그", "limit": 30}))
    assert "주말 리그 3차전" in got


def test_검색은_비공개_경계를_넘지_않는다(client, feed_data):
    """검색어가 맞아도 볼 권한이 없으면 나오지 않는다."""
    got = titles(client.get("/api/posts", params={"q": "회의록", "limit": 30}))
    assert got == []


def test_검색_결과가_없으면_빈_목록이다(client, feed_data):
    body = client.get("/api/posts", params={"q": "존재하지않는검색어zzz"}).json()
    assert body["items"] == []
    assert body["total"] == 0
    assert body["has_more"] is False


def test_배치_로드는_겹치지_않고_이어진다(client, feed_data):
    first = client.get("/api/posts", params={"limit": 2}).json()
    assert len(first["items"]) == 2
    assert first["has_more"] is True

    second = client.get("/api/posts", params={"offset": 2, "limit": 2}).json()
    ids = {it["id"] for it in first["items"]} & {it["id"] for it in second["items"]}
    assert not ids


def test_total_은_현재_필터_기준이다(client, feed_data):
    """total 이 전체 개수로 고정돼 있으면 '더 보기'가 영영 끝나지 않는다.

    동아리 이름은 실행마다 다르게 지어지므로 이 픽스처의 글만 정확히 걸린다.
    A 동아리는 공개 1 · 비공개 1 이고, 비로그인에게는 공개 1건만 보여야 한다.
    """
    body = client.get("/api/posts", params={"q": feed_data["a"].name, "limit": 1}).json()
    assert body["total"] == 1
    assert body["has_more"] is False


def test_카드에_필요한_필드가_다_온다(client, feed_data):
    it = client.get("/api/posts", params={"q": "출사"}).json()["items"][0]
    # 전체 피드는 동아리를 가로지르므로 club_name·category 가 없으면 카드를 못 그린다
    for key in ("id", "club_id", "club_name", "category", "title", "excerpt", "activity_date", "tags"):
        assert key in it
