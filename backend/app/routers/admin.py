"""T4 — 동아리 개설·관리자 (담당 th). 명세: docs/api.md §5"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import errors
from ..db import get_db
from ..deps import admin_user, verified_user
from ..models import User

router = APIRouter(tags=["admin"])


@router.post("/club-applications", status_code=201)
def apply_club(user: User = Depends(verified_user), db: Session = Depends(get_db)):
    # OB는 403 OB_NOT_ALLOWED (기획서 §3.2)
    raise errors.todo("동아리 개설 신청")


@router.delete("/club-applications/{app_id}")
def cancel_application(app_id: int, user: User = Depends(verified_user), db: Session = Depends(get_db)):
    raise errors.todo("개설 신청 취소")


@router.get("/admin/club-applications")
def list_applications(
    status: str | None = None,
    admin: User = Depends(admin_user),
    db: Session = Depends(get_db),
):
    raise errors.todo("개설 신청 목록")


@router.post("/admin/club-applications/{app_id}/approve")
def approve_application(app_id: int, admin: User = Depends(admin_user), db: Session = Depends(get_db)):
    # 승인하면 동아리가 생기고 신청자가 동아리장 1기가 된다
    raise errors.todo("개설 승인")


@router.post("/admin/club-applications/{app_id}/reject")
def reject_application(app_id: int, admin: User = Depends(admin_user), db: Session = Depends(get_db)):
    # reason 은 필수. 사유와 함께 메일 통보 (기획서 §5.2)
    raise errors.todo("개설 거절")


@router.patch("/admin/clubs/{club_id}")
def admin_update_club(club_id: int, admin: User = Depends(admin_user), db: Session = Depends(get_db)):
    # status 보관 전환 · leader_id 동아리장 강제 교체 (기획서 §5.5, §5.6)
    raise errors.todo("관리자 동아리 수정")
