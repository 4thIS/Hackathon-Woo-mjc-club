"""응답 직렬화 — docs/api.md §0.4 공통 객체.

라우터가 dict 를 직접 조립하지 않고 여기를 거친다. 같은 객체가 여러 화면에
나가는데(캐러셀·타임라인·상세) 형태가 갈리면 프론트가 분기해야 하기 때문이다.

N+1 쿼리를 감수한다 — 데이터가 수십 건 규모이고, 최적화보다 형태 일치가 중요하다.
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import enums
from .models import Club, ClubMember, Like, Post, User


def club_summary(db: Session, club: Club) -> dict:
    count = db.scalar(select(func.count()).select_from(ClubMember).where(ClubMember.club_id == club.id))
    return {
        "id": club.id,
        "name": club.name,
        "category": club.category,
        "recruit_status": club.recruit_status,
        "image": club.image,
        "member_count": count or 0,  # 활동중 + OB (api.md §9-1)
    }


def user_brief(user: User | None) -> dict:
    """탈퇴한 작성자는 None 으로 들어온다. 글 자체는 동아리에 남는다."""
    if user is None:
        return {"id": None, "name": "탈퇴한 회원", "dept": ""}
    return {"id": user.id, "name": user.name, "dept": user.dept}


def _excerpt(body: str, n: int = 120) -> str:
    return " ".join(body.split())[:n]


def _like_info(db: Session, post_id: int, viewer: User | None) -> tuple[int, bool]:
    count = db.scalar(select(func.count()).select_from(Like).where(Like.post_id == post_id)) or 0
    liked = viewer is not None and db.get(Like, {"user_id": viewer.id, "post_id": post_id}) is not None
    return count, liked


def post_summary(db: Session, post: Post, viewer: User | None = None) -> dict:
    like_count, liked = _like_info(db, post.id, viewer)
    return {
        "id": post.id,
        "club_id": post.club_id,
        "club_name": post.club.name,
        # 사진이 없는 카드는 분야 그라데이션으로 채운다 — 프론트가 동아리를 따로 조회하지
        # 않도록 여기서 함께 준다 (디자인 기획 §2 카테고리 5색)
        "category": post.club.category,
        "title": post.title,
        "excerpt": _excerpt(post.body),
        "photo": post.photos[0] if post.photos else None,
        "activity_date": post.activity_date.isoformat(),
        "tags": post.tags or [],
        "is_public": post.is_public,
        "like_count": like_count,
        "liked_by_me": liked,
    }


def post_detail(db: Session, post: Post, viewer: User | None, can_edit: bool) -> dict:
    like_count, liked = _like_info(db, post.id, viewer)
    return {
        "id": post.id,
        "club_id": post.club_id,
        "club_name": post.club.name,
        "author": user_brief(post.author),
        "title": post.title,
        "body": post.body,
        "photos": post.photos or [],
        "activity_date": post.activity_date.isoformat(),
        "tags": post.tags or [],
        "is_public": post.is_public,
        "like_count": like_count,
        "liked_by_me": liked,
        "created_at": post.created_at.isoformat() if post.created_at else None,
        "can_edit": can_edit,
    }


def can_see_private(db: Session, club_id: int, user: User | None) -> bool:
    """비공개 글 열람권 — 해당 동아리 소속(부원·OB·동아리장)과 관리자 (기획서 §6.2)."""
    if user is None:
        return False
    if user.is_admin:
        return True
    return db.get(ClubMember, {"user_id": user.id, "club_id": club_id}) is not None


def can_edit_post(db: Session, post: Post, user: User | None) -> bool:
    """작성 권한은 동아리장만 (기획서 §6.1). 관리자는 전체."""
    if user is None:
        return False
    if user.is_admin:
        return True
    m = db.get(ClubMember, {"user_id": user.id, "club_id": post.club_id})
    return m is not None and m.role == enums.ROLE_LEADER
