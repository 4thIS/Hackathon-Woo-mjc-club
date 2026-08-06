"""동아리 개설·관리자 — 명세: docs/api.md §5"""

from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from .. import depts, enums, errors, serializers
from ..db import get_db
from ..deps import admin_user, verified_user
from ..models import Club, ClubApplication, ClubMember, Post, User
from ..routers.auth import ALLOWED_DOMAINS
from ..services import mailer

router = APIRouter(tags=["admin"])


class ClubApplicationIn(BaseModel):
    name: str
    category: str
    founded_year: int
    purpose: str = ""
    advisor: str = ""


class RejectIn(BaseModel):
    reason: str


class AdminClubPatchIn(BaseModel):
    status: str | None = None
    leader_id: str | None = None


def _get_application_or_404(db: Session, app_id: int) -> ClubApplication:
    app_ = db.get(ClubApplication, app_id)
    if app_ is None:
        raise errors.not_found("개설 신청을 찾을 수 없습니다.")
    return app_


@router.post("/club-applications", status_code=201)
def apply_club(
    payload: ClubApplicationIn, user: User = Depends(verified_user), db: Session = Depends(get_db)
):
    # OB는 403 OB_NOT_ALLOWED (기획서 §3.2)
    if user.academic_status == enums.ACADEMIC_GRADUATED:
        raise errors.ApiError(403, "OB_NOT_ALLOWED", "OB는 동아리 개설을 신청할 수 없습니다.")

    app_ = ClubApplication(applicant_id=user.id, **payload.model_dump())
    db.add(app_)
    db.commit()
    db.refresh(app_)
    return {"id": app_.id, "status": app_.status}


@router.delete("/club-applications/{app_id}")
def cancel_application(app_id: int, user: User = Depends(verified_user), db: Session = Depends(get_db)):
    app_ = _get_application_or_404(db, app_id)
    if app_.applicant_id != user.id:
        raise errors.forbidden("본인의 신청만 취소할 수 있습니다.")
    if app_.status != enums.REQ_PENDING:
        raise errors.ApiError(409, "ALREADY_PROCESSED", "이미 처리된 신청입니다.")
    app_.status = enums.REQ_CANCELLED
    db.commit()
    return {"status": enums.REQ_CANCELLED}


@router.get("/admin/club-applications")
def list_applications(
    status: str | None = None,
    admin: User = Depends(admin_user),
    db: Session = Depends(get_db),
):
    stmt = select(ClubApplication)
    if status:
        stmt = stmt.where(ClubApplication.status == status)
    apps = db.scalars(stmt.order_by(ClubApplication.created_at)).all()
    return [
        {
            "id": a.id,
            "name": a.name,
            "category": a.category,
            "founded_year": a.founded_year,
            "purpose": a.purpose,
            "advisor": a.advisor,
            "applicant": {"id": a.applicant.id, "name": a.applicant.name, "dept": a.applicant.dept},
            "status": a.status,
            "created_at": a.created_at.isoformat().replace("+00:00", "Z"),
        }
        for a in apps
    ]


@router.post("/admin/club-applications/{app_id}/approve")
def approve_application(app_id: int, admin: User = Depends(admin_user), db: Session = Depends(get_db)):
    # 승인하면 동아리가 생기고 신청자가 동아리장 1기가 된다
    app_ = _get_application_or_404(db, app_id)
    if app_.status != enums.REQ_PENDING:
        raise errors.ApiError(409, "ALREADY_PROCESSED", "이미 처리된 신청입니다.")

    club = Club(
        name=app_.name,
        category=app_.category,
        founded_year=app_.founded_year,
        purpose=app_.purpose,
        advisor=app_.advisor,
        current_gen=1,
    )
    db.add(club)
    db.flush()
    db.add(ClubMember(user_id=app_.applicant_id, club_id=club.id, role=enums.ROLE_LEADER, gen=1))
    app_.status = enums.REQ_APPROVED
    db.commit()

    applicant = db.get(User, app_.applicant_id)
    mailer.send(applicant.email, f"[{club.name}] 개설 신청이 승인되었습니다", "동아리 개설이 승인되었습니다.")
    return {"status": enums.REQ_APPROVED, "club_id": club.id}


@router.post("/admin/club-applications/{app_id}/reject")
def reject_application(
    app_id: int, payload: RejectIn, admin: User = Depends(admin_user), db: Session = Depends(get_db)
):
    # reason 은 필수. 사유와 함께 메일 통보 (기획서 §5.2)
    app_ = _get_application_or_404(db, app_id)
    if app_.status != enums.REQ_PENDING:
        raise errors.ApiError(409, "ALREADY_PROCESSED", "이미 처리된 신청입니다.")
    app_.status = enums.REQ_REJECTED
    app_.reject_reason = payload.reason
    db.commit()

    applicant = db.get(User, app_.applicant_id)
    mailer.send(applicant.email, f"[{app_.name}] 개설 신청이 거절되었습니다", payload.reason)
    return {"status": enums.REQ_REJECTED}


@router.patch("/admin/clubs/{club_id}")
def admin_update_club(
    club_id: int, payload: AdminClubPatchIn, admin: User = Depends(admin_user), db: Session = Depends(get_db)
):
    # status 보관 전환 · leader_id 동아리장 강제 교체 (기획서 §5.5, §5.6)
    club = db.get(Club, club_id)
    if club is None:
        raise errors.not_found("동아리를 찾을 수 없습니다.")

    if payload.status is not None:
        club.status = payload.status

    if payload.leader_id is not None:
        target = db.get(ClubMember, {"user_id": payload.leader_id, "club_id": club_id})
        if target is None or target.membership != enums.MEMBERSHIP_ACTIVE:
            raise errors.ApiError(400, "TARGET_NOT_ACTIVE_MEMBER", "대상은 활동중인 부원이어야 합니다.")
        current_leader = db.scalar(
            select(ClubMember).where(
                ClubMember.club_id == club_id, ClubMember.role == enums.ROLE_LEADER
            )
        )
        if current_leader is not None:
            current_leader.role = enums.ROLE_MEMBER
        target.role = enums.ROLE_LEADER

    db.commit()
    return {"id": club.id, "status": club.status}


@router.get("/admin/clubs")
def list_clubs_for_admin(
    q: str | None = None,
    status: str | None = None,
    category: str | None = None,
    _: User = Depends(admin_user),
    db: Session = Depends(get_db),
):
    """공개 목록은 활동중만 준다. 관리자는 보관된 동아리도 봐야 한다 (api.md §5)."""
    stmt = select(Club)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Club.name.ilike(like), Club.category.ilike(like)))
    if status:
        stmt = stmt.where(Club.status == status)
    if category:
        stmt = stmt.where(Club.category == category)

    clubs = db.scalars(stmt.order_by(Club.status, Club.category, Club.name)).all()

    items = []
    for club in clubs:
        members = db.scalars(select(ClubMember).where(ClubMember.club_id == club.id)).all()
        leader = next((m for m in members if m.role == enums.ROLE_LEADER), None)
        items.append({
            "id": club.id,
            "name": club.name,
            "category": club.category,
            "recruit_status": club.recruit_status,
            "status": club.status,
            "current_gen": club.current_gen,
            "member_count": len(members),
            "post_count": db.scalar(
                select(func.count()).select_from(Post).where(Post.club_id == club.id)
            ) or 0,
            # 비어 있으면 관리자가 강제 교체해야 할 동아리다 (기획서 §5.5)
            "leader": serializers.user_brief(leader.user) if leader else None,
        })
    return {"total": len(items), "items": items}


# ── 유저 관리 (api.md §5) ──────────────────────────────────
#
# 기획서 §4.3 이 잠긴 필드에 대해 "변경이 필요하면 관리자 문의" 라고 안내한다.
# 그래서 관리자는 이름·생년월일·성별·이메일까지 고칠 수 있다. 학번만 PK 라 불가.


class AdminUserPatchIn(BaseModel):
    name: str | None = None
    dept: str | None = None
    birth: date | None = None
    gender: str | None = None
    email: str | None = None
    academic_status: str | None = None
    email_verified: bool | None = None
    is_admin: bool | None = None


def admin_user_payload(db: Session, user: User) -> dict:
    memberships = db.scalars(select(ClubMember).where(ClubMember.user_id == user.id)).all()
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "dept": user.dept,
        "birth": user.birth.isoformat(),
        "gender": user.gender,
        "grade": user.grade,
        "academic_status": user.academic_status,
        "email_verified": user.email_verified,
        "is_admin": user.is_admin,
        # 졸업 전환이 막히는 이유를 화면에서 미리 보여주기 위해 함께 준다
        "clubs": [
            {
                "id": m.club_id,
                "name": m.club.name,
                "role": m.role,
                "membership": m.membership,
            }
            for m in memberships
        ],
    }


@router.get("/admin/users")
def list_users(
    q: str | None = None,
    status: str | None = None,
    admin: bool | None = None,
    _: User = Depends(admin_user),
    db: Session = Depends(get_db),
):
    stmt = select(User)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(User.name.ilike(like), User.id.ilike(like), User.dept.ilike(like),
                User.email.ilike(like))
        )
    if status:
        stmt = stmt.where(User.academic_status == status)
    if admin is not None:
        stmt = stmt.where(User.is_admin.is_(admin))

    users = db.scalars(stmt.order_by(User.is_admin.desc(), User.id)).all()
    return {"total": len(users), "items": [admin_user_payload(db, u) for u in users]}


@router.patch("/admin/users/{user_id}")
def update_user(
    user_id: str,
    payload: AdminUserPatchIn,
    admin: User = Depends(admin_user),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if user is None:
        raise errors.not_found("유저를 찾을 수 없습니다.")

    if payload.email is not None:
        email = payload.email.strip().lower()
        _, _, domain = email.partition("@")
        if domain not in ALLOWED_DOMAINS:
            raise errors.ApiError(
                400, "INVALID_EMAIL_DOMAIN", "@mjc.ac.kr 또는 @on.mjc.ac.kr 주소만 쓸 수 있습니다."
            )
        # 학번과 로컬파트 일치는 요구하지 않는다 (가입과 같은 규칙)
        clash = db.scalar(select(User).where(User.email == email, User.id != user.id))
        if clash is not None:
            raise errors.ApiError(409, "DUPLICATE_EMAIL", "이미 쓰이는 이메일입니다.")
        user.email = email

    if payload.gender is not None:
        if payload.gender not in enums.GENDERS:
            raise errors.ApiError(400, "INVALID_INPUT", "성별 값이 올바르지 않습니다.")
        user.gender = payload.gender

    if payload.academic_status is not None:
        status = payload.academic_status
        if status not in enums.ACADEMIC_STATUSES:
            raise errors.ApiError(400, "INVALID_INPUT", "학적 상태 값이 올바르지 않습니다.")

        if status == enums.ACADEMIC_GRADUATED:
            # 관리자도 예외가 아니다. 동아리장이 OB 가 되면 그 동아리가 마비된다 (기획서 §4.3).
            # 먼저 위임하거나 PATCH /admin/clubs/{id} 로 강제 교체한다 (§5.5).
            led = db.scalars(
                select(Club)
                .join(ClubMember, ClubMember.club_id == Club.id)
                .where(ClubMember.user_id == user.id, ClubMember.role == enums.ROLE_LEADER)
            ).all()
            if led:
                names = " · ".join(c.name for c in led)
                raise errors.ApiError(
                    409,
                    "LEADER_CANNOT_GRADUATE",
                    f"{names} 의 동아리장입니다. 먼저 동아리장을 교체해주세요.",
                )
            for m in db.scalars(select(ClubMember).where(ClubMember.user_id == user.id)):
                m.membership = enums.MEMBERSHIP_OB

        user.academic_status = status

    if payload.is_admin is not None and payload.is_admin != user.is_admin:
        # 관리자가 0명이 되면 아무도 되돌릴 수 없다
        if not payload.is_admin:
            others = db.scalar(
                select(func.count()).select_from(User)
                .where(User.is_admin.is_(True), User.id != user.id)
            )
            if not others:
                raise errors.ApiError(
                    409, "LAST_ADMIN", "마지막 관리자입니다. 다른 관리자를 먼저 지정해주세요."
                )
        user.is_admin = payload.is_admin

    if payload.name is not None:
        name = payload.name.strip()
        if not name:
            raise errors.ApiError(400, "INVALID_INPUT", "이름을 입력해주세요.")
        user.name = name

    if payload.dept is not None:
        dept = payload.dept.strip()
        if not dept:
            raise errors.ApiError(400, "INVALID_INPUT", "학과를 입력해주세요.")
        if not depts.is_valid(dept):
            raise errors.ApiError(400, "INVALID_DEPT", "학과는 목록에서 골라주세요.")
        user.dept = dept

    if payload.birth is not None:
        user.birth = payload.birth

    if payload.email_verified is not None:
        user.email_verified = payload.email_verified

    db.commit()
    db.refresh(user)
    return admin_user_payload(db, user)
