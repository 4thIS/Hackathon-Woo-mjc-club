"""T3/T4 — 가입·탈퇴·부원 (담당 th). 명세: docs/api.md §4"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import errors
from ..db import get_db
from ..deps import club_leader, club_member, get_club, verified_user
from ..models import Club, ClubMember, User

router = APIRouter(tags=["members"])


# --- 가입폼 -------------------------------------------------------------


@router.get("/clubs/{club_id}/join-form")
def get_join_form(club: Club = Depends(get_club), db: Session = Depends(get_db)):
    # 폼이 없어도 404가 아니라 {"required": false, "fields": []} 를 준다 (api.md §4)
    raise errors.todo("가입폼 조회")


@router.put("/clubs/{club_id}/join-form")
def put_join_form(m: ClubMember = Depends(club_leader), db: Session = Depends(get_db)):
    raise errors.todo("가입폼 저장")


# --- 가입 신청 ----------------------------------------------------------


@router.post("/clubs/{club_id}/join-requests", status_code=201)
def create_join_request(
    club: Club = Depends(get_club),
    user: User = Depends(verified_user),
    db: Session = Depends(get_db),
):
    # 409 ALREADY_MEMBER / ALREADY_REQUESTED / CLUB_NOT_RECRUITING, 403 OB_NOT_ALLOWED
    raise errors.todo("가입 신청")


@router.get("/clubs/{club_id}/join-requests")
def list_join_requests(m: ClubMember = Depends(club_leader), db: Session = Depends(get_db)):
    # ★ 이름·학과·학년만. 학번 전체·성별·생년월일은 응답에 넣지 않는다 (기획서 §5.3·§9)
    raise errors.todo("가입 신청자 목록")


@router.post("/join-requests/{req_id}/approve")
def approve_join(req_id: int, user: User = Depends(verified_user), db: Session = Depends(get_db)):
    # 승인 시 동아리의 current_gen 을 자동 부여 (기획서 §5.3.1)
    raise errors.todo("가입 승인")


@router.post("/join-requests/{req_id}/reject")
def reject_join(req_id: int, user: User = Depends(verified_user), db: Session = Depends(get_db)):
    raise errors.todo("가입 거절")


@router.delete("/join-requests/{req_id}")
def cancel_join(req_id: int, user: User = Depends(verified_user), db: Session = Depends(get_db)):
    raise errors.todo("가입 신청 취소")


# --- 탈퇴 ---------------------------------------------------------------


@router.post("/clubs/{club_id}/leave-requests", status_code=201)
def create_leave_request(m: ClubMember = Depends(club_member), db: Session = Depends(get_db)):
    # 동아리장 본인은 403 LEADER_MUST_TRANSFER (기획서 §5.4)
    raise errors.todo("탈퇴 요청")


@router.get("/clubs/{club_id}/leave-requests")
def list_leave_requests(m: ClubMember = Depends(club_leader), db: Session = Depends(get_db)):
    # ★ 조회 시점에 7일 지난 건을 먼저 자동 승인 처리한다. 스케줄러 없음 (구현계획 §2)
    raise errors.todo("탈퇴 요청 목록")


@router.post("/leave-requests/{req_id}/approve")
def approve_leave(req_id: int, user: User = Depends(verified_user), db: Session = Depends(get_db)):
    raise errors.todo("탈퇴 승인")


# --- 부원 관리 ----------------------------------------------------------


@router.get("/clubs/{club_id}/members/manage")
def manage_members(m: ClubMember = Depends(club_leader), db: Session = Depends(get_db)):
    raise errors.todo("부원 관리 목록")


@router.patch("/clubs/{club_id}/members/{user_id}")
def update_member(user_id: str, m: ClubMember = Depends(club_leader), db: Session = Depends(get_db)):
    raise errors.todo("부원 기수 수정")


@router.patch("/clubs/{club_id}")
def update_club(m: ClubMember = Depends(club_leader), db: Session = Depends(get_db)):
    # 이름·카테고리·창립년도·지도교수는 여기서 바꾸지 않는다 (기획서 §5.1)
    raise errors.todo("동아리 정보 수정")


@router.post("/clubs/{club_id}/transfer")
def transfer_leader(m: ClubMember = Depends(club_leader), db: Session = Depends(get_db)):
    raise errors.todo("동아리장 위임")
