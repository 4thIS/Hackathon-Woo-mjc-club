"""권한 검사는 **여기서만** 한다. 서비스 레이어에서 중복 검사하지 않는다 (backend/CLAUDE.md).

라우터 사용 예:

    def my_page(user: User = Depends(current_user)): ...                 # 로그인
    def apply(user: User = Depends(verified_user)): ...                  # 로그인 + 이메일 인증
    def approve(m: ClubMember = Depends(club_leader)): ...               # 해당 동아리 동아리장
"""

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from . import enums, errors
from .db import get_db
from .models import Club, ClubMember, User
from .security import SESSION_COOKIE, read_session


def current_user_optional(request: Request, db: Session = Depends(get_db)) -> User | None:
    uid = read_session(request.cookies.get(SESSION_COOKIE))
    if not uid:
        return None
    return db.get(User, uid)


def current_user(user: User | None = Depends(current_user_optional)) -> User:
    if user is None:
        raise errors.unauthorized()
    return user


def verified_user(user: User = Depends(current_user)) -> User:
    """미인증 계정은 비로그인과 같은 권한이다 (기획서 §3.2)."""
    if not user.email_verified:
        raise errors.ApiError(403, "EMAIL_NOT_VERIFIED", "이메일 인증을 먼저 완료해주세요.")
    return user


def admin_user(user: User = Depends(current_user)) -> User:
    if not user.is_admin:
        raise errors.forbidden("관리자만 사용할 수 있습니다.")
    return user


def get_club(club_id: int, db: Session = Depends(get_db)) -> Club:
    club = db.get(Club, club_id)
    if club is None:
        raise errors.not_found("동아리를 찾을 수 없습니다.")
    return club


def membership_of(db: Session, user: User | None, club_id: int) -> ClubMember | None:
    if user is None:
        return None
    return db.get(ClubMember, {"user_id": user.id, "club_id": club_id})


def club_member(
    club: Club = Depends(get_club),
    user: User = Depends(verified_user),
    db: Session = Depends(get_db),
) -> ClubMember:
    """활동중인 부원 이상. OB는 통과하지 못한다 (기획서 §3.2)."""
    m = membership_of(db, user, club.id)
    if m is None:
        raise errors.forbidden("동아리 소속이 아닙니다.")
    if m.membership == enums.MEMBERSHIP_OB:
        raise errors.ApiError(403, "OB_NOT_ALLOWED", "OB는 열람과 좋아요만 가능합니다.")
    return m


def club_leader(
    club: Club = Depends(get_club),
    user: User = Depends(verified_user),
    db: Session = Depends(get_db),
) -> ClubMember:
    m = membership_of(db, user, club.id)
    if m is None or m.role != enums.ROLE_LEADER:
        if user.is_admin:
            return ClubMember(user_id=user.id, club_id=club.id, role=enums.ROLE_LEADER)
        raise errors.forbidden("동아리장만 사용할 수 있습니다.")
    return m
