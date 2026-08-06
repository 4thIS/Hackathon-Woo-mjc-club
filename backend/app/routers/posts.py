"""T5 — 활동 글 (담당 cw). 명세: docs/api.md §3(읽기) · §6(쓰기)"""

from fastapi import APIRouter, Depends, Query, UploadFile
from sqlalchemy.orm import Session

from .. import errors
from ..db import get_db
from ..deps import club_leader, current_user_optional, verified_user
from ..models import ClubMember, User

router = APIRouter(tags=["posts"])


@router.get("/posts/highlights")
def highlights(limit: int = Query(12, le=20), db: Session = Depends(get_db)):
    # 공개 글 최신순, 동아리당 최대 1건 (api.md §9-4)
    raise errors.todo("메인 캐러셀 하이라이트")


@router.get("/posts/{post_id}")
def post_detail(
    post_id: int,
    user: User | None = Depends(current_user_optional),
    db: Session = Depends(get_db),
):
    # 비공개 글을 권한 없이 요청하면 403이 아니라 404 (api.md §9-5)
    raise errors.todo("활동 글 상세")


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
