"""T4 — 동아리 개설·관리자 (담당 th). 명세: docs/api.md §5"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import enums, errors
from ..db import get_db
from ..deps import admin_user, verified_user
from ..models import Club, ClubApplication, ClubMember, User
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
