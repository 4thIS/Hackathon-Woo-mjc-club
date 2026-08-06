"""T5 — 활동 글 (담당 cw). 명세: docs/api.md §3(읽기) · §6(쓰기)"""

from datetime import date
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import errors, serializers
from ..config import settings
from ..db import get_db
from ..deps import club_leader, current_user_optional, verified_user
from ..models import ClubMember, Like, Post, User

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


# --- 사진 업로드 -------------------------------------------------------

ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp"}
MAX_UPLOAD = 10 * 1024 * 1024  # 10MB


@router.post("/uploads", status_code=201)
def upload(file: UploadFile, user: User = Depends(verified_user)):
    """로컬 저장, 원본 그대로. 리사이징·CDN 없음 (구현계획 §7)."""
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXT:
        raise errors.ApiError(400, "UNSUPPORTED_FILE_TYPE", "jpg · png · webp 이미지만 올릴 수 있습니다.")

    data = file.file.read(MAX_UPLOAD + 1)
    if len(data) > MAX_UPLOAD:
        raise errors.ApiError(400, "FILE_TOO_LARGE", "10MB 이하 이미지만 올릴 수 있습니다.")
    if not data:
        raise errors.ApiError(400, "EMPTY_FILE", "빈 파일입니다.")

    # 원본 파일명을 그대로 쓰지 않는다 — 경로 조작과 한글 파일명 인코딩 문제를 한 번에 없앤다
    name = f"{uuid4().hex}{ext}"
    target = Path(settings.upload_dir)
    target.mkdir(parents=True, exist_ok=True)
    (target / name).write_bytes(data)

    return {"url": f"/uploads/{name}"}


# --- 활동 글 CRUD ------------------------------------------------------


def _clean_tags(tags: list[str]) -> list[str]:
    seen, out = set(), []
    for t in tags:
        t = t.strip()
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    return out[:8]


def _check_photos(photos: list[str]) -> list[str]:
    """우리가 저장한 경로만 받는다. 외부 URL 을 본문 이미지로 심는 걸 막는다."""
    for p in photos:
        if not p.startswith("/uploads/") or ".." in p:
            raise errors.ApiError(400, "INVALID_PHOTO_PATH", "업로드한 사진만 첨부할 수 있습니다.")
    return photos[:10]


class PostIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = ""
    photos: list[str] = []
    activity_date: date
    tags: list[str] = []
    is_public: bool = False  # 기본 비공개 — 사진에 학생 얼굴이 들어간다 (기획서 §6.1)


class PostPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    body: str | None = None
    photos: list[str] | None = None
    activity_date: date | None = None
    tags: list[str] | None = None
    is_public: bool | None = None


def _editable_post(post_id: int, user: User, db: Session) -> Post:
    post = db.get(Post, post_id)
    if post is None:
        raise errors.not_found("글을 찾을 수 없습니다.")
    if not serializers.can_edit_post(db, post, user):
        raise errors.forbidden("동아리장만 활동 글을 수정할 수 있습니다.")
    return post


@router.post("/clubs/{club_id}/posts", status_code=201)
def create_post(
    club_id: int,
    payload: PostIn,
    m: ClubMember = Depends(club_leader),
    user: User = Depends(verified_user),
    db: Session = Depends(get_db),
):
    post = Post(
        club_id=club_id,
        author_id=user.id,
        title=payload.title.strip(),
        body=payload.body,
        photos=_check_photos(payload.photos),
        activity_date=payload.activity_date,
        tags=_clean_tags(payload.tags),
        is_public=payload.is_public,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return serializers.post_detail(db, post, user, True)


@router.patch("/posts/{post_id}")
def update_post(
    post_id: int,
    payload: PostPatch,
    user: User = Depends(verified_user),
    db: Session = Depends(get_db),
):
    post = _editable_post(post_id, user, db)

    if payload.title is not None:
        post.title = payload.title.strip()
    if payload.body is not None:
        post.body = payload.body
    if payload.photos is not None:
        post.photos = _check_photos(payload.photos)
    if payload.activity_date is not None:
        post.activity_date = payload.activity_date
    if payload.tags is not None:
        post.tags = _clean_tags(payload.tags)
    if payload.is_public is not None:
        post.is_public = payload.is_public

    db.commit()
    db.refresh(post)
    return serializers.post_detail(db, post, user, True)


@router.delete("/posts/{post_id}", status_code=204)
def delete_post(post_id: int, user: User = Depends(verified_user), db: Session = Depends(get_db)):
    post = _editable_post(post_id, user, db)
    # 좋아요를 먼저 지운다 — FK 가 남으면 삭제가 막힌다
    db.query(Like).filter(Like.post_id == post.id).delete(synchronize_session=False)
    db.delete(post)
    db.commit()
    # 업로드된 사진 파일은 그대로 둔다 (구현계획 §10 — 고아 파일 정리 없음)


@router.post("/posts/{post_id}/like")
def toggle_like(post_id: int, user: User = Depends(verified_user), db: Session = Depends(get_db)):
    post = db.get(Post, post_id)
    if post is None:
        raise errors.not_found("글을 찾을 수 없습니다.")
    # 비공개 글은 열람권이 있어야 좋아요도 가능하다. 없으면 존재를 숨긴다 (api.md §9-5)
    if not post.is_public and not serializers.can_see_private(db, post.club_id, user):
        raise errors.not_found("글을 찾을 수 없습니다.")

    existing = db.get(Like, {"user_id": user.id, "post_id": post.id})
    if existing is None:
        db.add(Like(user_id=user.id, post_id=post.id))
        liked = True
    else:
        db.delete(existing)
        liked = False
    db.commit()

    count = db.scalar(select(func.count()).select_from(Like).where(Like.post_id == post.id)) or 0
    return {"liked": liked, "like_count": count}
