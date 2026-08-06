"""T1 — 인증·계정 (담당 wj). 명세: docs/api.md §2

라우트 선언은 계약이다. 함수 본문만 채우면 된다.
"""

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from .. import errors
from ..db import get_db
from ..deps import current_user, verified_user
from ..models import User

router = APIRouter(tags=["auth"])


@router.post("/auth/signup", status_code=201)
def signup(db: Session = Depends(get_db)):
    raise errors.todo("회원가입")


@router.post("/auth/login")
def login(response: Response, db: Session = Depends(get_db)):
    # 성공 시: response.set_cookie(SESSION_COOKIE, sign_session(user.id), httponly=True, samesite="lax")
    raise errors.todo("로그인")


@router.post("/auth/logout", status_code=204)
def logout(response: Response):
    raise errors.todo("로그아웃")


@router.get("/auth/verify")
def verify(token: str, db: Session = Depends(get_db)):
    # JSON이 아니라 302 리다이렉트다 → {FRONTEND_URL}/verify?status=ok|expired|invalid
    raise errors.todo("이메일 인증")


@router.post("/auth/verify/resend", status_code=204)
def resend(db: Session = Depends(get_db)):
    raise errors.todo("인증 메일 재발송")


@router.get("/me")
def me(user: User = Depends(current_user)):
    raise errors.todo("내 정보 조회")


@router.patch("/me")
def update_me(user: User = Depends(current_user), db: Session = Depends(get_db)):
    # 졸업 전환 시 동아리장 겸직이면 409 LEADER_CANNOT_GRADUATE (기획서 §4.3)
    raise errors.todo("내 정보 수정")


@router.get("/me/clubs")
def my_clubs(user: User = Depends(current_user), db: Session = Depends(get_db)):
    raise errors.todo("내 동아리 목록")


@router.get("/me/requests")
def my_requests(user: User = Depends(current_user), db: Session = Depends(get_db)):
    raise errors.todo("내 신청 현황")


@router.post("/me/ai-key")
def register_ai_key(user: User = Depends(verified_user), db: Session = Depends(get_db)):
    # 저장 전에 게이트웨이 모델 목록 조회로 유효성 확인 (기획서 §4.5)
    raise errors.todo("AI 키 등록")


@router.delete("/me/ai-key", status_code=204)
def delete_ai_key(user: User = Depends(verified_user), db: Session = Depends(get_db)):
    raise errors.todo("AI 키 삭제")
