"""T2 — 동아리 탐색 (담당 cw). 명세: docs/api.md §3"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import enums, serializers
from ..db import get_db
from ..deps import current_user_optional, get_club, membership_of
from ..models import Club, ClubMember, JoinForm, JoinRequest, Post, User

router = APIRouter(tags=["clubs"])


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
    items = [serializers.club_summary(db, c) for c in clubs]
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

        # 심사중·거절만 노출한다 — 승인은 is_member 로 이미 드러나고, 취소는 재신청 가능 상태와 같다.
        latest_req = db.scalar(
            select(JoinRequest)
            .where(JoinRequest.club_id == club.id, JoinRequest.user_id == user.id)
            .order_by(JoinRequest.created_at.desc())
        )
        join_request_status = (
            latest_req.status
            if latest_req is not None and latest_req.status in (enums.REQ_PENDING, enums.REQ_REJECTED)
            else None
        )

        mine = {
            "is_member": m is not None,
            "role": m.role if m else None,
            "membership": m.membership if m else None,
            "gen": m.gen if m else None,
            "join_request_status": join_request_status,
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
        "leader": serializers.user_brief(leader.user) if leader else None,
        "counts": {"active": active, "ob": len(members) - active, "total": len(members)},
        "has_join_form": db.get(JoinForm, club.id) is not None,
        "my": mine,
    }


@router.get("/clubs/{club_id}/posts")
def club_posts(
    club: Club = Depends(get_club),
    offset: int = 0,
    limit: int = Query(5, le=20),
    user: User | None = Depends(current_user_optional),
    db: Session = Depends(get_db),
):
    """타임라인 배치 로드. **오래된 순**으로 준다 (시안: 과거 → 현재)."""
    see_private = serializers.can_see_private(db, club.id, user)

    base = select(Post).where(Post.club_id == club.id)
    if not see_private:
        base = base.where(Post.is_public.is_(True))

    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0

    rows = db.scalars(
        base.order_by(Post.activity_date.asc(), Post.id.asc()).offset(offset).limit(limit)
    ).all()

    # 끝 표지("YYYY년부터 N건")에 쓸 가장 오래된 연도 — total 과 같은 필터 기준이어야 한다
    oldest = db.scalar(base.order_by(Post.activity_date.asc(), Post.id.asc()).limit(1))

    return {
        "items": [serializers.post_summary(db, p, user) for p in rows],
        "total": total,
        "has_more": offset + len(rows) < total,
        "first_year": oldest.activity_date.year if oldest else None,
    }


@router.get("/clubs/{club_id}/members")
def club_members(
    club: Club = Depends(get_club),
    user: User | None = Depends(current_user_optional),
    db: Session = Depends(get_db),
):
    """인원 모달 — 기수별 그룹. 최신 기수 → 오래된 기수 → OB 순.

    비로그인·미인증에는 `members` 를 빈 배열로 내리고 인원수만 준다
    (api.md §9-2 · 기획서 §9 최소 노출).
    """
    show_names = user is not None and user.email_verified

    rows = db.scalars(select(ClubMember).where(ClubMember.club_id == club.id)).all()

    active: dict[int | None, list[ClubMember]] = {}
    ob: list[ClubMember] = []
    for m in rows:
        if m.membership == enums.MEMBERSHIP_OB:
            ob.append(m)
        else:
            active.setdefault(m.gen, []).append(m)

    def entry(m: ClubMember) -> dict:
        return {"id": m.user.id, "name": m.user.name, "dept": m.user.dept, "role": m.role}

    def group(gen: int | None, label: str, members: list[ClubMember]) -> dict:
        # 동아리장을 맨 앞에, 나머지는 이름순
        ordered = sorted(members, key=lambda m: (m.role != enums.ROLE_LEADER, m.user.name))
        return {
            "gen": gen,
            "label": label,
            "count": len(members),
            "members": [entry(m) for m in ordered] if show_names else [],
        }

    groups = []
    # 기수 있는 그룹부터 내림차순, 기수 없는 활동중은 그다음
    for gen in sorted((g for g in active if g is not None), reverse=True):
        groups.append(group(gen, f"{gen}기", active[gen]))
    if None in active:
        groups.append(group(None, "기수 미지정", active[None]))
    if ob:
        groups.append(group(None, "OB", ob))

    return {"total": len(rows), "groups": groups}


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
    used_categories = db.scalar(
        select(func.count(func.distinct(Club.category))).where(Club.status == enums.CLUB_ACTIVE)
    )
    return {
        "clubs": clubs or 0,
        "recruiting": recruiting or 0,
        "posts": posts or 0,
        # 열거값 개수가 아니라 실제 동아리가 있는 분야 수. 화면에서 셀 수 있는 값이어야 한다
        "categories": used_categories or 0,
    }
