"""T5 — 활동 글 CRUD · 사진 업로드 · 좋아요. 명세: docs/api.md §6

작성 권한은 동아리장만이고(기획서 §6.1) 공개 기본값은 false 다. 이 두 가지가
깨지면 초상권 사고와 권한 사고가 나므로 테스트로 고정한다.
"""

from datetime import date
from pathlib import Path

import pytest

from app import enums
from app.config import settings
from app.models import Post

# 1x1 PNG. 실제 이미지 바이트여야 업로드 경로를 그대로 지난다.
PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
    "890000000a49444154789c6360000002000100ffff03000006000557bfabd400"
    "00000049454e44ae426082"
)


@pytest.fixture
def leader_club(make_user, make_club, join_club, auth_cookie):
    """동아리장 1명 + 부원 1명 + 동아리 1개."""
    leader = make_user(name="동아리장")
    member = make_user(name="부원")
    club = make_club()
    join_club(leader, club, role=enums.ROLE_LEADER)
    join_club(member, club)
    return {
        "club": club,
        "leader": leader,
        "member": member,
        "leader_cookie": auth_cookie(leader),
        "member_cookie": auth_cookie(member),
    }


def make_payload(**kw):
    base = {
        "title": "성북동 출사",
        "body": "12명이 참여했습니다.",
        "activity_date": "2026-05-01",
        "tags": ["출사", "필름"],
    }
    base.update(kw)
    return base


# --- 작성 -------------------------------------------------------------


def test_leader_can_create_and_defaults_to_private(client, leader_club):
    r = client.post(
        f"/api/clubs/{leader_club['club'].id}/posts",
        json=make_payload(),
        cookies=leader_club["leader_cookie"],
    )
    assert r.status_code == 201
    body = r.json()
    # 공개는 사람이 의식적으로 선택하는 행위여야 한다 (기획서 §6.1)
    assert body["is_public"] is False
    assert body["can_edit"] is True
    assert body["tags"] == ["출사", "필름"]
    assert body["like_count"] == 0


def test_member_cannot_create(client, leader_club):
    r = client.post(
        f"/api/clubs/{leader_club['club'].id}/posts",
        json=make_payload(),
        cookies=leader_club["member_cookie"],
    )
    assert r.status_code == 403


def test_anonymous_cannot_create(client, leader_club):
    r = client.post(f"/api/clubs/{leader_club['club'].id}/posts", json=make_payload())
    assert r.status_code == 401


def test_title_is_required(client, leader_club):
    r = client.post(
        f"/api/clubs/{leader_club['club'].id}/posts",
        json=make_payload(title="   "[:0]),  # 빈 문자열
        cookies=leader_club["leader_cookie"],
    )
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "INVALID_INPUT"


def test_external_photo_url_is_rejected(client, leader_club):
    """외부 URL 을 본문 이미지로 심는 걸 막는다."""
    r = client.post(
        f"/api/clubs/{leader_club['club'].id}/posts",
        json=make_payload(photos=["https://evil.example/x.png"]),
        cookies=leader_club["leader_cookie"],
    )
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "INVALID_PHOTO_PATH"


# --- 수정·삭제 --------------------------------------------------------


def _create(client, ctx, **kw):
    r = client.post(
        f"/api/clubs/{ctx['club'].id}/posts", json=make_payload(**kw), cookies=ctx["leader_cookie"]
    )
    assert r.status_code == 201
    return r.json()


def test_leader_can_publish_later(client, leader_club):
    post = _create(client, leader_club)
    r = client.patch(
        f"/api/posts/{post['id']}", json={"is_public": True}, cookies=leader_club["leader_cookie"]
    )
    assert r.status_code == 200
    assert r.json()["is_public"] is True

    # 공개되면 비로그인도 읽는다
    assert client.get(f"/api/posts/{post['id']}").status_code == 200


def test_member_cannot_edit_or_delete(client, leader_club):
    post = _create(client, leader_club)
    assert (
        client.patch(
            f"/api/posts/{post['id']}", json={"title": "바꿔치기"}, cookies=leader_club["member_cookie"]
        ).status_code
        == 403
    )
    assert (
        client.delete(f"/api/posts/{post['id']}", cookies=leader_club["member_cookie"]).status_code == 403
    )


def test_delete_removes_post(client, leader_club, db):
    post = _create(client, leader_club)
    assert client.delete(f"/api/posts/{post['id']}", cookies=leader_club["leader_cookie"]).status_code == 204
    assert db.get(Post, post["id"]) is None


def test_delete_works_even_with_likes(client, leader_club):
    """좋아요가 달린 글도 지워져야 한다 — FK 가 남으면 삭제가 막힌다."""
    post = _create(client, leader_club, is_public=True)
    client.post(f"/api/posts/{post['id']}/like", cookies=leader_club["member_cookie"])
    assert client.delete(f"/api/posts/{post['id']}", cookies=leader_club["leader_cookie"]).status_code == 204


# --- 좋아요 -----------------------------------------------------------


def test_like_toggles(client, leader_club):
    post = _create(client, leader_club, is_public=True)
    cookie = leader_club["member_cookie"]

    on = client.post(f"/api/posts/{post['id']}/like", cookies=cookie).json()
    assert on == {"liked": True, "like_count": 1}

    off = client.post(f"/api/posts/{post['id']}/like", cookies=cookie).json()
    assert off == {"liked": False, "like_count": 0}


def test_anonymous_cannot_like(client, leader_club):
    post = _create(client, leader_club, is_public=True)
    assert client.post(f"/api/posts/{post['id']}/like").status_code == 401


def test_like_on_private_post_hidden_from_outsider(client, leader_club, make_user, auth_cookie):
    """비공개 글은 좋아요 시도도 404 — 존재 자체를 숨긴다 (api.md §9-5)."""
    post = _create(client, leader_club)  # 기본 비공개
    outsider = make_user(name="외부인")
    r = client.post(f"/api/posts/{post['id']}/like", cookies=auth_cookie(outsider))
    assert r.status_code == 404


# --- 업로드 -----------------------------------------------------------


def test_upload_returns_url(client, leader_club):
    r = client.post(
        "/api/uploads",
        files={"file": ("shot.png", PNG, "image/png")},
        cookies=leader_club["leader_cookie"],
    )
    assert r.status_code == 201
    url = r.json()["url"]
    assert url.startswith("/uploads/")

    saved = Path(settings.upload_dir) / url.rsplit("/", 1)[-1]
    assert saved.exists()
    saved.unlink()  # 테스트가 남긴 파일은 치운다


def test_upload_rejects_non_image(client, leader_club):
    r = client.post(
        "/api/uploads",
        files={"file": ("report.pdf", b"%PDF-1.4", "application/pdf")},
        cookies=leader_club["leader_cookie"],
    )
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "UNSUPPORTED_FILE_TYPE"


def test_uploaded_photo_can_be_attached(client, leader_club):
    up = client.post(
        "/api/uploads",
        files={"file": ("shot.png", PNG, "image/png")},
        cookies=leader_club["leader_cookie"],
    ).json()

    post = _create(client, leader_club, photos=[up["url"]])
    assert post["photos"] == [up["url"]]

    Path(settings.upload_dir, up["url"].rsplit("/", 1)[-1]).unlink(missing_ok=True)


# --- 타임라인 반영 ----------------------------------------------------


def test_new_public_post_appears_in_timeline(client, leader_club):
    post = _create(client, leader_club, is_public=True, activity_date=str(date(2026, 6, 1)))
    body = client.get(f"/api/clubs/{leader_club['club'].id}/posts", params={"limit": 20}).json()
    assert post["id"] in [p["id"] for p in body["items"]]


def test_private_post_absent_from_anonymous_timeline(client, leader_club):
    post = _create(client, leader_club)
    body = client.get(f"/api/clubs/{leader_club['club'].id}/posts", params={"limit": 20}).json()
    assert post["id"] not in [p["id"] for p in body["items"]]
