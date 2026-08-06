"""T6 — AI 활동 글 초안 (담당 wj). 명세: docs/api.md §7 · 기획서 §7

⚠️ 이 Task가 시연 하이라이트다. T1 끝나는 즉시 게이트웨이 스모크 테스트부터 할 것
(구현계획 T6): ① 텍스트 생성 ② 이미지 입력. ②가 안 되면 30분 안에 폴백 확정.
"""

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from .. import errors
from ..db import get_db
from ..deps import verified_user
from ..models import User

router = APIRouter(tags=["ai"])


@router.post("/ai/draft")
def draft(
    club_id: int = Form(...),
    memo: str | None = Form(None),
    photos: list[UploadFile] = File(default=[]),
    pdf: UploadFile | None = File(None),
    user: User = Depends(verified_user),
    db: Session = Depends(get_db),
):
    """사진만 있고 메모·PDF가 없으면 초안을 만들지 않는다 — 버그가 아니라 설계다 (기획서 §7.2).

    if not memo and not pdf_text:
        raise errors.ApiError(422, "MEMO_REQUIRED",
            "무슨 활동이었는지 한 줄만 적어주세요. 사진만으로는 초안을 만들지 않습니다.")
    """
    raise errors.todo("AI 활동 글 초안")
