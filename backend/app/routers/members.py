"""가입·탈퇴·부원 — 명세: docs/api.md §4"""

import re
from datetime import timedelta

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import enums, errors
from ..db import get_db
from ..deps import club_leader, club_member, get_club, membership_of, verified_user
from ..models import Club, ClubMember, JoinForm, JoinRequest, LeaveRequest, User, utcnow
from ..services import mailer

router = APIRouter(tags=["members"])


def _leader_of(db: Session, user: User, club_id: int) -> None:
    m = membership_of(db, user, club_id)
    if (m is None or m.role != enums.ROLE_LEADER) and not user.is_admin:
        raise errors.forbidden("동아리장만 사용할 수 있습니다.")


def _iso(dt) -> str:
    return dt.isoformat().replace("+00:00", "Z")


# --- 가입폼 -------------------------------------------------------------


# 저장 이름은 답변을 담는 JSON 의 키다. 화면에 보이는 글은 label 이 맡는다.
# 한글·공백이 섞이면 주소·스크립트에서 다루기 번거롭고, 답변을 내보낼 때도 깨지기 쉽다.
KEY_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]{0,29}$")


class JoinFormField(BaseModel):
    key: str
    label: str
    type: str
    required: bool = False

    @field_validator("key")
    @classmethod
    def _check_key(cls, v: str) -> str:
        if not KEY_RE.fullmatch(v.strip()):
            raise ValueError("저장 이름은 영문으로 시작하는 영문·숫자·밑줄 30자 이내입니다.")
        return v.strip()


class JoinFormIn(BaseModel):
    required: bool = False
    fields: list[JoinFormField] = []


@router.get("/clubs/{club_id}/join-form")
def get_join_form(club: Club = Depends(get_club), db: Session = Depends(get_db)):
    # 폼이 없어도 404가 아니라 {"required": false, "fields": []} 를 준다 (api.md §4)
    form = db.get(JoinForm, club.id)
    if form is None:
        return {"required": False, "fields": []}
    return {"required": form.required, "fields": form.fields}


@router.put("/clubs/{club_id}/join-form")
def put_join_form(payload: JoinFormIn, m: ClubMember = Depends(club_leader), db: Session = Depends(get_db)):
    form = db.get(JoinForm, m.club_id)
    if form is None:
        form = JoinForm(club_id=m.club_id)
        db.add(form)
    form.required = payload.required
    form.fields = [f.model_dump() for f in payload.fields]
    db.commit()
    return {"required": form.required, "fields": form.fields}


# --- 가입 신청 ----------------------------------------------------------


class JoinRequestIn(BaseModel):
    answers: dict = {}


class RejectIn(BaseModel):
    reason: str | None = None


def _get_join_request_or_404(db: Session, req_id: int) -> JoinRequest:
    req = db.get(JoinRequest, req_id)
    if req is None:
        raise errors.not_found("가입 신청을 찾을 수 없습니다.")
    return req


@router.post("/clubs/{club_id}/join-requests", status_code=201)
def create_join_request(
    payload: JoinRequestIn,
    club: Club = Depends(get_club),
    user: User = Depends(verified_user),
    db: Session = Depends(get_db),
):
    # OB(졸업생)는 새 동아리 가입을 할 수 없다 (기획서 §3.2)
    if user.academic_status == enums.ACADEMIC_GRADUATED:
        raise errors.ApiError(403, "OB_NOT_ALLOWED", "OB는 신규 가입을 신청할 수 없습니다.")

    existing = membership_of(db, user, club.id)
    if existing is not None:
        if existing.membership == enums.MEMBERSHIP_OB:
            raise errors.ApiError(403, "OB_NOT_ALLOWED", "OB는 신규 가입을 신청할 수 없습니다.")
        raise errors.ApiError(409, "ALREADY_MEMBER", "이미 가입된 동아리입니다.")

    pending = db.scalar(
        select(JoinRequest).where(
            JoinRequest.club_id == club.id,
            JoinRequest.user_id == user.id,
            JoinRequest.status == enums.REQ_PENDING,
        )
    )
    if pending is not None:
        raise errors.ApiError(409, "ALREADY_REQUESTED", "이미 심사중인 신청이 있습니다.")

    if club.recruit_status == enums.RECRUIT_CLOSED:
        raise errors.ApiError(409, "CLUB_NOT_RECRUITING", "현재 모집중이 아닙니다.")

    form = db.get(JoinForm, club.id)
    if form is not None and form.required:
        for field in form.fields:
            if field.get("required") and not str(payload.answers.get(field["key"], "")).strip():
                raise errors.ApiError(400, "FORM_REQUIRED", "필수 항목을 작성해주세요.")

    req = JoinRequest(user_id=user.id, club_id=club.id, form_answer=payload.answers)
    db.add(req)
    db.commit()
    db.refresh(req)
    return {"id": req.id, "status": req.status}


@router.get("/clubs/{club_id}/join-requests")
def list_join_requests(m: ClubMember = Depends(club_leader), db: Session = Depends(get_db)):
    # ★ 이름·학과·학년만. 학번 전체·성별·생년월일은 응답에 넣지 않는다 (기획서 §5.3·§9)
    #
    # 심사중인 것만 준다. 처리한 신청이 계속 남아 있으면 동아리장은 매번 어느 것이
    # 안 끝났는지 다시 찾아야 한다 — 이 화면은 '할 일 목록'이다.
    reqs = db.scalars(
        select(JoinRequest)
        .where(JoinRequest.club_id == m.club_id, JoinRequest.status == enums.REQ_PENDING)
        .order_by(JoinRequest.created_at)
    ).all()
    return [
        {
            "id": r.id,
            "name": r.user.name,
            "dept": r.user.dept,
            "grade": r.user.grade,
            "answers": r.form_answer,
            "created_at": _iso(r.created_at),
            "status": r.status,
        }
        for r in reqs
    ]


@router.post("/join-requests/{req_id}/approve")
def approve_join(req_id: int, user: User = Depends(verified_user), db: Session = Depends(get_db)):
    # 승인 시 동아리의 current_gen 을 자동 부여 (기획서 §5.3.1)
    req = _get_join_request_or_404(db, req_id)
    _leader_of(db, user, req.club_id)
    if req.status != enums.REQ_PENDING:
        raise errors.ApiError(409, "ALREADY_PROCESSED", "이미 처리된 신청입니다.")

    club = db.get(Club, req.club_id)
    req.status = enums.REQ_APPROVED

    member = db.get(ClubMember, {"user_id": req.user_id, "club_id": req.club_id})
    if member is None:
        member = ClubMember(
            user_id=req.user_id, club_id=req.club_id, role=enums.ROLE_MEMBER, gen=club.current_gen
        )
        db.add(member)
    else:
        member.membership = enums.MEMBERSHIP_ACTIVE
        member.gen = club.current_gen
    db.commit()

    applicant = db.get(User, req.user_id)
    mailer.send(
        applicant.email,
        f"[{club.name}] 가입 신청이 승인되었습니다",
        f"{club.name} 가입이 승인되었습니다. 기수: {club.current_gen if club.current_gen else '-'}",
    )
    return {"status": enums.REQ_APPROVED, "gen": club.current_gen}


@router.post("/join-requests/{req_id}/reject")
def reject_join(
    req_id: int,
    payload: RejectIn = RejectIn(),
    user: User = Depends(verified_user),
    db: Session = Depends(get_db),
):
    req = _get_join_request_or_404(db, req_id)
    _leader_of(db, user, req.club_id)
    if req.status != enums.REQ_PENDING:
        raise errors.ApiError(409, "ALREADY_PROCESSED", "이미 처리된 신청입니다.")

    club = db.get(Club, req.club_id)
    req.status = enums.REQ_REJECTED
    req.reject_reason = payload.reason
    db.commit()

    applicant = db.get(User, req.user_id)
    mailer.send(
        applicant.email,
        f"[{club.name}] 가입 신청이 거절되었습니다",
        payload.reason or "가입 신청이 거절되었습니다.",
    )
    return {"status": enums.REQ_REJECTED}


@router.delete("/join-requests/{req_id}")
def cancel_join(req_id: int, user: User = Depends(verified_user), db: Session = Depends(get_db)):
    req = _get_join_request_or_404(db, req_id)
    if req.user_id != user.id:
        raise errors.forbidden("본인의 신청만 취소할 수 있습니다.")
    if req.status != enums.REQ_PENDING:
        raise errors.ApiError(409, "ALREADY_PROCESSED", "이미 처리된 신청입니다.")
    req.status = enums.REQ_CANCELLED
    db.commit()
    return {"status": enums.REQ_CANCELLED}


# --- 탈퇴 ---------------------------------------------------------------


def _finalize_leave(db: Session, req: LeaveRequest) -> None:
    req.status = enums.REQ_APPROVED
    member = db.get(ClubMember, {"user_id": req.user_id, "club_id": req.club_id})
    if member is not None:
        db.delete(member)


def _auto_approve_expired_leaves(db: Session, club_id: int) -> None:
    cutoff = utcnow() - timedelta(days=7)
    expired = db.scalars(
        select(LeaveRequest).where(
            LeaveRequest.club_id == club_id,
            LeaveRequest.status == enums.REQ_PENDING,
            LeaveRequest.created_at <= cutoff,
        )
    ).all()
    for req in expired:
        _finalize_leave(db, req)
    if expired:
        db.commit()


@router.post("/clubs/{club_id}/leave-requests", status_code=201)
def create_leave_request(m: ClubMember = Depends(club_member), db: Session = Depends(get_db)):
    # 동아리장 본인은 403 LEADER_MUST_TRANSFER (기획서 §5.4)
    if m.role == enums.ROLE_LEADER:
        raise errors.ApiError(403, "LEADER_MUST_TRANSFER", "동아리장은 위임 후 탈퇴할 수 있습니다.")

    pending = db.scalar(
        select(LeaveRequest).where(
            LeaveRequest.club_id == m.club_id,
            LeaveRequest.user_id == m.user_id,
            LeaveRequest.status == enums.REQ_PENDING,
        )
    )
    if pending is not None:
        raise errors.ApiError(409, "ALREADY_REQUESTED", "이미 처리중인 탈퇴 요청이 있습니다.")

    req = LeaveRequest(user_id=m.user_id, club_id=m.club_id)
    db.add(req)
    db.commit()
    db.refresh(req)
    return {"id": req.id, "status": req.status, "auto_approve_at": _iso(req.created_at + timedelta(days=7))}


@router.get("/clubs/{club_id}/leave-requests")
def list_leave_requests(m: ClubMember = Depends(club_leader), db: Session = Depends(get_db)):
    # ★ 조회 시점에 7일 지난 건을 먼저 자동 승인 처리한다. 스케줄러 없음 (구현계획 §2)
    _auto_approve_expired_leaves(db, m.club_id)
    # 가입 신청과 같다 — 처리한 것은 목록에서 빠진다
    reqs = db.scalars(
        select(LeaveRequest)
        .where(LeaveRequest.club_id == m.club_id, LeaveRequest.status == enums.REQ_PENDING)
        .order_by(LeaveRequest.created_at)
    ).all()
    return [
        {
            "id": r.id,
            "user": {"id": r.user.id, "name": r.user.name, "dept": r.user.dept},
            "status": r.status,
            "created_at": _iso(r.created_at),
        }
        for r in reqs
    ]


@router.post("/leave-requests/{req_id}/approve")
def approve_leave(req_id: int, user: User = Depends(verified_user), db: Session = Depends(get_db)):
    req = db.get(LeaveRequest, req_id)
    if req is None:
        raise errors.not_found("탈퇴 요청을 찾을 수 없습니다.")
    _leader_of(db, user, req.club_id)
    if req.status != enums.REQ_PENDING:
        raise errors.ApiError(409, "ALREADY_PROCESSED", "이미 처리된 요청입니다.")
    _finalize_leave(db, req)
    db.commit()
    return {"status": enums.REQ_APPROVED}


# --- 부원 관리 ----------------------------------------------------------


class MemberPatchIn(BaseModel):
    """동아리장이 바꾸는 값.

    학적(재학·휴학·졸업)은 여기 없다 — 사람 전역 값이라 동아리장이 건드리면
    그 사람의 다른 동아리까지 영향을 받는다 (기획서 §3.1). 본인 또는 관리자만 바꾼다.
    동아리 안에서의 상태는 membership(활동중·OB)이다.
    """

    gen: int | None = None
    membership: str | None = None


class ClubPatchIn(BaseModel):
    purpose: str | None = None
    image: str | None = None
    meet_day: str | None = None
    meet_time: str | None = None
    meet_place: str | None = None
    recruit_status: str | None = None
    current_gen: int | None = None


class TransferIn(BaseModel):
    user_id: str


@router.get("/clubs/{club_id}/members/manage")
def manage_members(m: ClubMember = Depends(club_leader), db: Session = Depends(get_db)):
    members = db.scalars(select(ClubMember).where(ClubMember.club_id == m.club_id)).all()
    return [
        {
            "user": {"id": mm.user.id, "name": mm.user.name, "dept": mm.user.dept},
            "role": mm.role,
            "membership": mm.membership,
            # 학적은 읽기 전용으로 함께 준다 — 동아리장이 OB 전환을 판단하는 근거다
            "academic_status": mm.user.academic_status,
            "gen": mm.gen,
        }
        for mm in members
    ]


@router.patch("/clubs/{club_id}/members/{user_id}")
def update_member(
    user_id: str, payload: MemberPatchIn, m: ClubMember = Depends(club_leader), db: Session = Depends(get_db)
):
    target = db.get(ClubMember, {"user_id": user_id, "club_id": m.club_id})
    if target is None:
        raise errors.not_found("부원을 찾을 수 없습니다.")

    sent = payload.model_dump(exclude_unset=True)
    if "gen" in sent:
        target.gen = payload.gen

    if "membership" in sent:
        if payload.membership not in enums.MEMBERSHIPS:
            raise errors.ApiError(400, "INVALID_INPUT", "멤버십 값이 올바르지 않습니다.")
        # 동아리장이 OB 가 되면 그 동아리가 마비된다 (기획서 §4.3 과 같은 불변식)
        if payload.membership == enums.MEMBERSHIP_OB and target.role == enums.ROLE_LEADER:
            raise errors.ApiError(
                409, "LEADER_MUST_STAY_ACTIVE", "동아리장은 OB 로 바꿀 수 없습니다. 먼저 위임해주세요."
            )
        target.membership = payload.membership

    db.commit()
    return {"user_id": target.user_id, "gen": target.gen, "membership": target.membership}


@router.delete("/clubs/{club_id}/members/{user_id}", status_code=204)
def remove_member(
    user_id: str, m: ClubMember = Depends(club_leader), db: Session = Depends(get_db)
):
    """동아리장이 부원을 내보낸다. 탈퇴 요청을 기다리지 않는 강제 처리다.

    본인 요청에 의한 탈퇴는 leave-requests 쪽이다 (기획서 §5.4).
    """
    target = db.get(ClubMember, {"user_id": user_id, "club_id": m.club_id})
    if target is None:
        raise errors.not_found("부원을 찾을 수 없습니다.")
    if target.role == enums.ROLE_LEADER:
        raise errors.ApiError(
            409, "CANNOT_REMOVE_LEADER", "동아리장은 내보낼 수 없습니다. 먼저 위임해주세요."
        )

    # 심사중인 탈퇴 요청이 남으면 유령 항목이 된다
    db.query(LeaveRequest).filter(
        LeaveRequest.user_id == user_id, LeaveRequest.club_id == m.club_id,
        LeaveRequest.status == enums.REQ_PENDING,
    ).update({"status": enums.REQ_APPROVED}, synchronize_session=False)

    db.delete(target)
    db.commit()
    return Response(status_code=204)


@router.patch("/clubs/{club_id}")
def update_club(payload: ClubPatchIn, m: ClubMember = Depends(club_leader), db: Session = Depends(get_db)):
    # 이름·카테고리·창립년도·지도교수는 여기서 바꾸지 않는다 (기획서 §5.1)
    club = db.get(Club, m.club_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(club, key, value)
    db.commit()
    return {
        "id": club.id,
        "purpose": club.purpose,
        "image": club.image,
        "meet_day": club.meet_day,
        "meet_time": club.meet_time,
        "meet_place": club.meet_place,
        "recruit_status": club.recruit_status,
        "current_gen": club.current_gen,
    }


@router.post("/clubs/{club_id}/transfer")
def transfer_leader(
    payload: TransferIn, m: ClubMember = Depends(club_leader), db: Session = Depends(get_db)
):
    target = db.get(ClubMember, {"user_id": payload.user_id, "club_id": m.club_id})
    if target is None or target.membership != enums.MEMBERSHIP_ACTIVE:
        raise errors.ApiError(400, "TARGET_NOT_ACTIVE_MEMBER", "대상은 활동중인 부원이어야 합니다.")

    current_leader = db.get(ClubMember, {"user_id": m.user_id, "club_id": m.club_id})
    if current_leader is not None:
        current_leader.role = enums.ROLE_MEMBER
    target.role = enums.ROLE_LEADER
    db.commit()
    return {"status": "ok"}
