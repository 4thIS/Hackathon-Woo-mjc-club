"""T2 — 동아리 탐색 (담당 cw). 명세: docs/api.md §3

T0 시점에 목록·상세·지표는 구현해 둔다. 도커를 띄우면 바로 확인되는 것이 있어야
나머지 Task가 자기 코드를 의심하지 않는다. 타임라인·인원·캐러셀은 T2에서 채운다.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import enums, errors
from ..db import get_db
from ..deps import current_user_optional, get_club, membership_of
from ..models import Club, ClubMember, Post, User

router = APIRouter(tags=["clubs"])


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


@router.get("/clubs")
def list_clubs(
    category: str | None = None,
    recruit: str | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
):
    stmt = select(Club).where(Club.status == enums.CLUB_ACTIVE)
    if category:
        stmt = stmt.where(Club.category == category)
    if recruit:
        stmt = stmt.where(Club.recruit_status == recruit)
    if q:
        stmt = stmt.where(Club.name.ilike(f"%{q}%"))
    clubs = db.scalars(stmt.order_by(Club.category, Club.name)).all()
    items = [club_summary(db, c) for c in clubs]
    return {"items": items, "total": len(items)}


@router.get("/clubs/{club_id}")
def club_detail(
    club: Club = Depends(get_club),
    user: User | None = Depends(current_user_optional),
    db: Session = Depends(get_db),
):
    members = db.scalars(select(ClubMember).where(ClubMember.club_id == club.id)).all()
    active = sum(1 for m in members if m.membership == enums.MEMBERSHIP_ACTIVE)
    leader = next((m for m in members if m.role == enums.ROLE_LEADER), None)

    mine = None
    if user is not None:
        m = membership_of(db, user, club.id)
        recruiting = club.recruit_status in (enums.RECRUIT_MOJIP, enums.RECRUIT_ALWAYS)
        is_ob = m is not None and m.membership == enums.MEMBERSHIP_OB
        graduated = user.academic_status == enums.ACADEMIC_GRADUATED
        mine = {
            "is_member": m is not None,
            "role": m.role if m else None,
            "membership": m.membership if m else None,
            "gen": m.gen if m else None,
            "join_request_status": None,  # TODO(T3): 심사중/거절 반영
            "can_apply": bool(
                user.email_verified and recruiting and m is None and not is_ob and not graduated
            ),
        }

    return {
        "id": club.id,
        "name": club.name,
        "category": club.category,
        "founded_year": club.founded_year,
        "purpose": club.purpose,
        "advisor": club.advisor,
        "image": club.image,
        "meet_day": club.meet_day,
        "meet_time": club.meet_time,
        "meet_place": club.meet_place,
        "recruit_status": club.recruit_status,
        "current_gen": club.current_gen,
        "status": club.status,
        "leader": (
            {"id": leader.user.id, "name": leader.user.name, "dept": leader.user.dept} if leader else None
        ),
        "counts": {"active": active, "ob": len(members) - active, "total": len(members)},
        "has_join_form": False,  # TODO(T3): JoinForm 존재 여부
        "my": mine,
    }


@router.get("/clubs/{club_id}/posts")
def club_posts(
    club: Club = Depends(get_club),
    offset: int = 0,
    limit: int = Query(5, le=20),
    db: Session = Depends(get_db),
):
    raise errors.todo("동아리 활동 글 타임라인")


@router.get("/clubs/{club_id}/members")
def club_members(club: Club = Depends(get_club), db: Session = Depends(get_db)):
    # 비로그인·미인증에는 members 를 빈 배열로 (api.md §3, §9-2)
    raise errors.todo("동아리 인원 목록")


@router.get("/stats")
def stats(db: Session = Depends(get_db)):
    clubs = db.scalar(select(func.count()).select_from(Club).where(Club.status == enums.CLUB_ACTIVE))
    recruiting = db.scalar(
        select(func.count())
        .select_from(Club)
        .where(Club.status == enums.CLUB_ACTIVE)
        .where(Club.recruit_status.in_((enums.RECRUIT_MOJIP, enums.RECRUIT_ALWAYS)))
    )
    posts = db.scalar(select(func.count()).select_from(Post).where(Post.is_public.is_(True)))
    return {
        "clubs": clubs or 0,
        "recruiting": recruiting or 0,
        "posts": posts or 0,
        "categories": len(enums.CATEGORIES),
    }
