"""T5 — 활동 글 (담당 cw). 명세: docs/api.md §3(읽기) · §6(쓰기)"""

from fastapi import APIRouter, Depends, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import errors, serializers
from ..db import get_db
from ..deps import club_leader, current_user_optional, verified_user
from ..models import ClubMember, Post, User

router = APIRouter(tags=["posts"])


@router.get("/posts/highlights")
def highlights(
    limit: int = Query(12, le=20),
    user: User | None = Depends(current_user_optional),
    db: Session = Depends(get_db),
):
    """메인 곡선 캐러셀. 공개 글 최신순, **동아리당 최대 1건** (api.md §9-4).

    한 동아리가 캐러셀을 독점하면 "여러 동아리가 살아 있다"는 메시지가 죽는다.
    """
    rows = db.scalars(
        select(Post).where(Post.is_public.is_(True)).order_by(Post.activity_date.desc(), Post.id.desc())
    ).all()

    picked: list[Post] = []
    seen: set[int] = set()
    for p in rows:
        if p.club_id in seen:
            continue
        seen.add(p.club_id)
        picked.append(p)
        if len(picked) >= limit:
            break

    return [serializers.post_summary(db, p, user) for p in picked]


@router.get("/posts/{post_id}")
def post_detail(
    post_id: int,
    user: User | None = Depends(current_user_optional),
    db: Session = Depends(get_db),
):
    post = db.get(Post, post_id)
    if post is None:
        raise errors.not_found("글을 찾을 수 없습니다.")

    # 비공개 글을 권한 없이 요청하면 403이 아니라 404 — 존재 자체를 숨긴다 (api.md §9-5)
    if not post.is_public and not serializers.can_see_private(db, post.club_id, user):
        raise errors.not_found("글을 찾을 수 없습니다.")

    return serializers.post_detail(db, post, user, serializers.can_edit_post(db, post, user))


@router.post("/uploads", status_code=201)
def upload(file: UploadFile, user: User = Depends(verified_user)):
    raise errors.todo("파일 업로드")


@router.post("/clubs/{club_id}/posts", status_code=201)
def create_post(m: ClubMember = Depends(club_leader), db: Session = Depends(get_db)):
    # is_public 기본 false (기획서 §6.1)
    raise errors.todo("활동 글 작성")


@router.patch("/posts/{post_id}")
def update_post(post_id: int, user: User = Depends(verified_user), db: Session = Depends(get_db)):
    raise errors.todo("활동 글 수정")


@router.delete("/posts/{post_id}", status_code=204)
def delete_post(post_id: int, user: User = Depends(verified_user), db: Session = Depends(get_db)):
    raise errors.todo("활동 글 삭제")


@router.post("/posts/{post_id}/like")
def toggle_like(post_id: int, user: User = Depends(verified_user), db: Session = Depends(get_db)):
    raise errors.todo("좋아요 토글")
