"""AI 활동 글 초안 — 명세: docs/api.md §7 · 기획서 §7

⚠️ 게이트웨이 연동은 스모크 테스트로 먼저 확인한다: ① 텍스트 생성 ② 이미지 입력.
  → 2026-08-06 확인 완료. 둘 다 지원된다 (기획서 §7.0).
"""

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from .. import errors
from ..config import settings
from ..db import get_db
from ..deps import verified_user
from ..models import Club, User
from ..security import decrypt_ai_key
from ..services import ai_draft, pdf_text

router = APIRouter(tags=["ai"])

MAX_PHOTO_BYTES = 8 * 1024 * 1024  # base64 로 실어 보내므로 무제한으로 받지 않는다


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

    NOTE(wj): 권한이 `인증` 인 것은 api.md §7 계약 그대로다. 실제로 글을 쓸 수 있는 건
    동아리장뿐이므로(api.md §6) 초안도 `장` 이어야 일관되는데, 지금은 계약을 따른다.
    비용은 각자 개인 키에서 나가므로 남에게 전가되지는 않는다. PM 과 합의되면 좁힌다.
    """
    club = db.get(Club, club_id)
    if club is None:
        raise errors.not_found("동아리를 찾을 수 없습니다.")

    key = decrypt_ai_key(user.ai_key_enc) if user.ai_key_enc else None
    if not key and not settings.demo_fallback:
        raise errors.ApiError(
            403, "AI_KEY_NOT_REGISTERED", "내 정보에서 AI API 키를 등록하면 사용할 수 있어요."
        )

    extracted = None
    if pdf is not None and pdf.filename:
        extracted = pdf_text.extract(pdf.file.read())
        if extracted is None:
            # 스캔본은 글자가 안 나온다. 실패가 아니라 예상된 경우다 (기획서 §7.1)
            raise errors.ApiError(
                422, "PDF_UNREADABLE", "내용을 읽을 수 없습니다. 메모로 적어주세요."
            )

    memo = (memo or "").strip() or None
    if not memo and not extracted:
        raise errors.ApiError(
            422,
            "MEMO_REQUIRED",
            "무슨 활동이었는지 한 줄만 적어주세요. 사진만으로는 초안을 만들지 않습니다.",
        )

    images: list[bytes] = []
    for f in photos:
        if not f.filename:
            continue
        raw = f.file.read(MAX_PHOTO_BYTES + 1)
        if len(raw) > MAX_PHOTO_BYTES:
            raise errors.ApiError(400, "INVALID_INPUT", "사진 한 장은 8MB 이하여야 합니다.")
        images.append(raw)

    try:
        return ai_draft.generate(
            api_key=key or "",
            club_name=club.name,
            category=club.category,
            memo=memo,
            pdf_text=extracted,
            photos=images,
        )
    except ai_draft.QuotaExceeded as e:
        raise errors.ApiError(429, "AI_QUOTA_EXCEEDED", "키의 사용 한도를 초과했습니다.") from e
    except ai_draft.GatewayError as e:
        raise errors.ApiError(
            502, "AI_GATEWAY_ERROR", "AI 응답을 받지 못했습니다. 잠시 후 다시 시도해주세요."
        ) from e
