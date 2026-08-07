"""인증·계정 — 명세: docs/api.md §2

라우트 선언은 계약이다. 함수 본문만 채우면 된다.
"""

import secrets
from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, Depends, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import depts, enums, errors, serializers
from ..config import settings
from ..db import get_db
from ..deps import current_user, verified_user
from ..models import (
    Club,
    ClubApplication,
    ClubMember,
    EmailToken,
    JoinRequest,
    LeaveRequest,
    Like,
    Post,
    User,
)
from ..security import (
    SESSION_COOKIE,
    decrypt_ai_key,
    encrypt_ai_key,
    hash_password,
    password_problem,
    sign_session,
    verify_password,
)
from ..services import ai_draft, mailer

router = APIRouter(tags=["auth"])

ALLOWED_DOMAINS = ("mjc.ac.kr", "on.mjc.ac.kr")
STUDENT_ID_LEN = 10  # 명지전문대 학번 (예: 2022261026)
GRADES = (1, 2, 3, 4)
TOKEN_TTL = timedelta(hours=24)  # api.md 에 미정 — 24시간. 만료돼도 재발송으로 복구된다
# 재발송 간격. 60초면 몇 분 만지작거리는 사이 여러 통이 나가고, 무료 Gmail 의
# 하루 한도를 소진하면 그 뒤로는 아무에게도 메일이 가지 않는다.
RESEND_COOLDOWN = timedelta(minutes=3)
LEAVE_AUTO_DAYS = 7  # 기획서 §5.4


# ── 요청 본문 ──────────────────────────────────────────────


class SignupIn(BaseModel):
    email: str
    password: str
    student_id: str
    name: str
    dept: str
    birth: date
    gender: str
    grade: int | None = None  # 1~4. 학번에서 유추하지 않는다


class LoginIn(BaseModel):
    email: str
    password: str


class ResendIn(BaseModel):
    email: str


class UpdateMeIn(BaseModel):
    """이름·학번·생년월일·성별·이메일은 받지 않는다 (기획서 §4.3).

    NOTE(wj): 비밀번호 변경에 현재 비밀번호 확인이 없다. 디자인 기획 §5.1 의 내 정보
    화면은 '현재/새/확인' 3필드다. 지금은 계약(api.md §2)을 그대로 따르고,
    화면을 붙일 때 PM 과 합의해 `current_password` 를 추가한다.
    """

    password: str | None = None
    dept: str | None = None
    academic_status: str | None = None
    # 학년은 본인만 안다 — 휴학·재수·편입이면 학번과 어긋난다.
    # null 을 명시적으로 보내면 학년을 비운다 (model_fields_set 으로 구분한다)
    grade: int | None = None


class AiKeyIn(BaseModel):
    api_key: str


# ── 공통 ───────────────────────────────────────────────────


def me_payload(user: User) -> dict:
    """api.md §2 의 Me 객체. 로그인·조회·수정이 모두 같은 형태를 돌려준다."""
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
        "ai_key": {
            "registered": user.ai_key_enc is not None,
            "masked": f"****{user.ai_key_tail}" if user.ai_key_tail else None,
        },
    }


def iso(dt: datetime) -> str:
    """DB 드라이버가 naive 로 돌려주는 경우가 있어 UTC 로 맞춘다."""
    return (dt if dt.tzinfo else dt.replace(tzinfo=UTC)).isoformat()


def _in_cooldown(db: Session, user: User) -> bool:
    """마지막 발급 후 RESEND_COOLDOWN 이 지나지 않았는가.

    실제 메일이 나가기 시작하면 재발송은 무제한 발송기가 된다. Gmail 일일 한도를
    소진하면 그 뒤로는 아무에게도 메일이 가지 않는다.

    발급 시각 컬럼을 새로 만들지 않고 `expires_at - TOKEN_TTL` 로 역산한다 —
    스키마를 건드리면 DB 를 재생성해야 하기 때문이다 (backend/CLAUDE.md).
    """
    latest = db.scalar(
        select(EmailToken)
        .where(EmailToken.user_id == user.id)
        .order_by(EmailToken.expires_at.desc())
    )
    if latest is None:
        return False
    expires = latest.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    return datetime.now(UTC) - (expires - TOKEN_TTL) < RESEND_COOLDOWN


def issue_verification(db: Session, user: User) -> bool:
    """인증 토큰을 새로 발급하고 메일을 보낸다. 발송 성공 여부를 돌려준다."""
    db.query(EmailToken).filter(EmailToken.user_id == user.id).delete()
    token = EmailToken(
        token=secrets.token_urlsafe(32),
        user_id=user.id,
        expires_at=datetime.now(UTC) + TOKEN_TTL,
    )
    db.add(token)
    db.commit()

    link = mailer.verification_link(token.token)
    return mailer.send(
        user.email,
        "[MJC Club Archive] 이메일 인증",
        f"{user.name}님, 아래 주소를 열면 인증이 완료됩니다.\n\n{link}\n\n"
        f"이 링크는 {int(TOKEN_TTL.total_seconds() // 3600)}시간 뒤 만료됩니다.",
    )


# ── 인증 ───────────────────────────────────────────────────


@router.post("/auth/signup", status_code=201)
def signup(body: SignupIn, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    _, _, domain = email.partition("@")

    if domain not in ALLOWED_DOMAINS:
        raise errors.ApiError(
            400, "INVALID_EMAIL_DOMAIN", "@mjc.ac.kr 또는 @on.mjc.ac.kr 주소만 가입할 수 있습니다."
        )
    if not (body.student_id.isdigit() and len(body.student_id) == STUDENT_ID_LEN):
        raise errors.ApiError(
            400, "INVALID_STUDENT_ID", f"학번은 숫자 {STUDENT_ID_LEN}자리입니다."
        )
    # 이메일 로컬파트가 학번과 같아야 한다는 제약은 두지 않는다 — 학교 메일 주소가
    # 학번과 다른 계정(별칭·구계정)이 실제로 있다. 학번은 PK 로, 이메일은 유니크로
    # 각각 중복만 막으면 충분하다.
    if (why := password_problem(body.password)) is not None:
        raise errors.ApiError(400, "WEAK_PASSWORD", why)
    if body.gender not in enums.GENDERS:
        raise errors.ApiError(400, "INVALID_INPUT", "성별 값이 올바르지 않습니다.")
    if not depts.is_valid(body.dept.strip()):
        raise errors.ApiError(400, "INVALID_DEPT", "학과는 목록에서 골라주세요.")
    if body.grade is not None and body.grade not in GRADES:
        raise errors.ApiError(400, "INVALID_INPUT", "학년은 1~4 중에서 고릅니다.")

    # 학번이 PK다. 도메인이 달라도 같은 학번이면 여기서 막힌다 (기획서 §4.1)
    if db.get(User, body.student_id) is not None:
        raise errors.ApiError(409, "DUPLICATE_STUDENT_ID", "이미 가입된 학번입니다.")
    if db.scalar(select(User).where(User.email == email)) is not None:
        raise errors.ApiError(409, "DUPLICATE_EMAIL", "이미 가입된 이메일입니다.")

    user = User(
        id=body.student_id,
        email=email,
        pw_hash=hash_password(body.password),
        name=body.name.strip(),
        dept=body.dept.strip(),
        birth=body.birth,
        gender=body.gender,
        grade=body.grade,
    )
    db.add(user)
    db.commit()

    return {"student_id": user.id, "email_sent": issue_verification(db, user)}


@router.post("/auth/login")
def login(body: LoginIn, response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.strip().lower()))
    if user is None or not verify_password(body.password, user.pw_hash):
        raise errors.ApiError(401, "INVALID_CREDENTIALS", "이메일 또는 비밀번호가 올바르지 않습니다.")

    # 미인증 계정도 로그인은 성공한다. 권한만 비로그인 수준이다 (기획서 §4.2)
    response.set_cookie(
        SESSION_COOKIE, sign_session(user.id), httponly=True, samesite="lax", path="/"
    )
    return me_payload(user)


@router.post("/auth/logout", status_code=204)
def logout(response: Response):
    response.delete_cookie(SESSION_COOKIE, path="/")
    return Response(status_code=204, headers=dict(response.headers))


@router.get("/auth/verify")
def verify(token: str, db: Session = Depends(get_db)):
    """이메일 링크가 직접 여는 주소. JSON이 아니라 302 리다이렉트다."""

    def go(status: str) -> RedirectResponse:
        return RedirectResponse(f"{settings.frontend_url}/verify?status={status}", status_code=302)

    row = db.get(EmailToken, token)
    if row is None:
        return go("invalid")

    expires = row.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    if expires < datetime.now(UTC):
        db.delete(row)
        db.commit()
        return go("expired")

    user = db.get(User, row.user_id)
    if user is None:
        return go("invalid")

    user.email_verified = True
    db.delete(row)
    db.commit()
    return go("ok")


@router.post("/auth/verify/resend", status_code=204)
def resend(body: ResendIn, db: Session = Depends(get_db)):
    """존재 여부를 노출하지 않기 위해 없는 이메일이어도 204 다 (api.md §2).

    쿨다운에 걸려도 204 다. 여기서 429 를 주면 "이 이메일은 존재한다"를 알려주게 된다.
    """
    user = db.scalar(select(User).where(User.email == body.email.strip().lower()))
    if user is not None and not user.email_verified and not _in_cooldown(db, user):
        issue_verification(db, user)
    return Response(status_code=204)


# ── 내 정보 ────────────────────────────────────────────────


@router.get("/me")
def me(user: User = Depends(current_user)):
    return me_payload(user)


@router.patch("/me")
def update_me(body: UpdateMeIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if body.password is not None:
        if (why := password_problem(body.password)) is not None:
            raise errors.ApiError(400, "WEAK_PASSWORD", why)
        user.pw_hash = hash_password(body.password)

    if body.dept is not None:
        dept = body.dept.strip()
        if not dept:
            raise errors.ApiError(400, "INVALID_INPUT", "학과를 입력해주세요.")
        if not depts.is_valid(dept):
            raise errors.ApiError(400, "INVALID_DEPT", "학과는 목록에서 골라주세요.")
        user.dept = dept

    # 학년은 본인만 안다. `grade` 를 **보냈는지**로 판단한다 —
    # 안 보내면 그대로 두고, null 을 보내면 비운다 (다른 필드와 달리 비우기가 유효한 값이다)
    if "grade" in body.model_fields_set:
        if body.grade is not None and body.grade not in GRADES:
            raise errors.ApiError(400, "INVALID_INPUT", "학년은 1~4 중에서 고릅니다.")
        user.grade = body.grade

    if body.academic_status is not None:
        status = body.academic_status
        if status not in enums.ACADEMIC_STATUSES:
            raise errors.ApiError(400, "INVALID_INPUT", "학적 상태 값이 올바르지 않습니다.")

        if status == enums.ACADEMIC_GRADUATED:
            # 동아리장이 OB 가 되면 그 동아리 운영이 통째로 멈춘다 (기획서 §4.3)
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
                    f"{names} 의 동아리장입니다. 먼저 위임하거나 관리자에게 교체를 요청해주세요.",
                )
            # 졸업하면 모든 소속이 OB 가 된다 (기획서 §3.1)
            for m in db.scalars(select(ClubMember).where(ClubMember.user_id == user.id)):
                m.membership = enums.MEMBERSHIP_OB

        user.academic_status = status

    db.commit()
    db.refresh(user)
    return me_payload(user)


@router.get("/me/clubs")
def my_clubs(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(ClubMember).where(ClubMember.user_id == user.id).order_by(ClubMember.club_id)
    ).all()
    return [
        {
            # 요약 형태는 serializers 가 소유한다. 여기서 다시 조립하지 않는다 (api.md §0.4)
            "club": serializers.club_summary(db, m.club),
            "role": m.role,
            "membership": m.membership,
            "gen": m.gen,
        }
        for m in rows
    ]


@router.get("/me/requests")
def my_requests(user: User = Depends(current_user), db: Session = Depends(get_db)):
    """진행중인 것과 **거절**만 준다.

    승인·취소된 건은 뺀다 — 승인 결과는 '내 동아리' 목록이 보여주고, 취소는 본인이 한
    일이라 다시 알릴 이유가 없다. 다 끝난 항목이 쌓이면 지금 뭘 기다리는 중인지 흐려진다.
    거절만 남기는 것은 사유를 확인해야 하기 때문이다.
    """
    SHOWN = (enums.REQ_PENDING, enums.REQ_REJECTED)

    joins = db.scalars(
        select(JoinRequest)
        .where(JoinRequest.user_id == user.id, JoinRequest.status.in_(SHOWN))
        .order_by(JoinRequest.id.desc())
    ).all()
    creates = db.scalars(
        select(ClubApplication)
        .where(ClubApplication.applicant_id == user.id, ClubApplication.status.in_(SHOWN))
        .order_by(ClubApplication.id.desc())
    ).all()
    leaves = db.scalars(
        select(LeaveRequest)
        .where(LeaveRequest.user_id == user.id, LeaveRequest.status.in_(SHOWN))
        .order_by(LeaveRequest.id.desc())
    ).all()

    return {
        "join": [
            {
                "id": r.id,
                "club_id": r.club_id,
                "club_name": r.club.name,
                "status": r.status,
                "created_at": iso(r.created_at),
                "cancellable": r.status == enums.REQ_PENDING,
            }
            for r in joins
        ],
        "create": [
            {
                "id": a.id,
                "name": a.name,
                "status": a.status,
                "reject_reason": a.reject_reason,
                "created_at": iso(a.created_at),
                "cancellable": a.status == enums.REQ_PENDING,
            }
            for a in creates
        ],
        "leave": [
            {
                "id": r.id,
                "club_id": r.club_id,
                "club_name": r.club.name,
                "status": r.status,
                "created_at": iso(r.created_at),
                # 실제 자동 승인은 탈퇴 요청 목록이 조회 시점에 처리한다
                "auto_approve_at": iso(r.created_at + timedelta(days=LEAVE_AUTO_DAYS)),
                "cancellable": r.status == enums.REQ_PENDING,
            }
            for r in leaves
        ],
    }


# ── AI 키 ──────────────────────────────────────────────────


@router.post("/me/ai-key")
def register_ai_key(
    body: AiKeyIn, user: User = Depends(verified_user), db: Session = Depends(get_db)
):
    key = body.api_key.strip()
    if not key:
        raise errors.ApiError(400, "INVALID_AI_KEY", "키를 입력해주세요.")

    # 저장 전에 게이트웨이가 실제로 받아주는 키인지 확인한다 (기획서 §4.5).
    # 글 쓰다가 실패하는 상황을 막는 게 목적이다.
    try:
        valid = ai_draft.verify_key(key)
    except Exception as e:  # noqa: BLE001 — 게이트웨이 장애와 키 오류를 구분해야 한다
        raise errors.ApiError(
            502, "AI_GATEWAY_ERROR", "AI 서버에 연결하지 못했습니다. 잠시 후 다시 시도해주세요."
        ) from e
    if not valid:
        raise errors.ApiError(400, "INVALID_AI_KEY", "키가 유효하지 않습니다. 다시 확인해주세요.")

    user.ai_key_enc = encrypt_ai_key(key)
    user.ai_key_tail = key[-4:]
    db.commit()
    return {"registered": True, "masked": f"****{user.ai_key_tail}"}


@router.delete("/me/ai-key", status_code=204)
def delete_ai_key(user: User = Depends(verified_user), db: Session = Depends(get_db)):
    user.ai_key_enc = None
    user.ai_key_tail = None
    db.commit()
    return Response(status_code=204)


# ── 회원 탈퇴 ──────────────────────────────────────────────


class WithdrawIn(BaseModel):
    password: str


def leading_clubs(db: Session, user_id: str) -> list[Club]:
    """이 사람이 동아리장인 동아리들. 비어 있지 않으면 계정을 지울 수 없다."""
    return list(db.scalars(
        select(Club)
        .join(ClubMember, ClubMember.club_id == Club.id)
        .where(ClubMember.user_id == user_id, ClubMember.role == enums.ROLE_LEADER)
    ).all())


def is_last_admin(db: Session, user: User) -> bool:
    if not user.is_admin:
        return False
    others = db.scalar(
        select(func.count()).select_from(User).where(User.is_admin.is_(True), User.id != user.id)
    )
    return not others


def purge_user(db: Session, user: User) -> None:
    """계정과 딸린 것을 지운다. **활동 글은 남긴다** — 기록은 동아리의 자산이다.

    본인 탈퇴(DELETE /me)와 관리자 삭제(DELETE /admin/users/{id})가 같은 규칙을 쓴다.
    두 벌로 두면 한쪽만 고쳐져 데이터가 어긋난다.
    """
    for post in db.scalars(select(Post).where(Post.author_id == user.id)):
        post.author_id = None

    for model, cond in (
        (Like, Like.user_id == user.id),
        (JoinRequest, JoinRequest.user_id == user.id),
        (LeaveRequest, LeaveRequest.user_id == user.id),
        (ClubApplication, ClubApplication.applicant_id == user.id),
        (ClubMember, ClubMember.user_id == user.id),
        (EmailToken, EmailToken.user_id == user.id),
    ):
        db.query(model).filter(cond).delete(synchronize_session=False)

    db.delete(user)


@router.delete("/me", status_code=204)
def withdraw(body: WithdrawIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """계정을 지운다. **활동 글은 남긴다** — 기록은 동아리의 자산이다 (api.md §2).

    되돌릴 수 없으므로 비밀번호를 다시 확인한다.
    """
    if not verify_password(body.password, user.pw_hash):
        raise errors.ApiError(403, "INVALID_PASSWORD", "비밀번호가 올바르지 않습니다.")

    # 동아리장이 사라지면 그 동아리가 마비된다. 졸업과 같은 불변식이다 (기획서 §4.3, §5.5)
    led = leading_clubs(db, user.id)
    if led:
        names = " · ".join(c.name for c in led)
        raise errors.ApiError(
            409, "LEADER_CANNOT_LEAVE", f"{names} 의 동아리장입니다. 먼저 동아리장을 위임해주세요."
        )
    if is_last_admin(db, user):
        raise errors.ApiError(
            409, "LAST_ADMIN", "마지막 관리자입니다. 다른 관리자를 먼저 지정해주세요."
        )

    purge_user(db, user)
    db.commit()

    resp = Response(status_code=204)
    resp.delete_cookie(SESSION_COOKIE, path="/")
    return resp


def current_ai_key(user: User) -> str | None:
    """AI 초안이 쓴다. 저장된 키를 복호화해 돌려준다 — 응답에는 절대 싣지 않는다."""
    return decrypt_ai_key(user.ai_key_enc) if user.ai_key_enc else None
