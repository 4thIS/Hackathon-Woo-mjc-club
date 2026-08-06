"""AI 활동 글 초안 — 명세: docs/api.md §7 · 기획서 §7

⚠️ 게이트웨이 연동은 스모크 테스트로 먼저 확인한다: ① 텍스트 생성 ② 이미지 입력.
  → 2026-08-06 확인 완료. 둘 다 지원된다 (기획서 §7.0).
"""

from fastapi import APIRouter, Depends, File, Form, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import enums, errors
from ..config import settings
from ..db import get_db
from ..deps import verified_user
from ..models import Club, Post, User
from ..security import decrypt_ai_key
from ..services import ai_draft, ai_recommend, pdf_text

router = APIRouter(tags=["ai"])

MAX_PHOTO_BYTES = 8 * 1024 * 1024  # base64 로 실어 보내므로 무제한으로 받지 않는다
RECENT_POSTS = 2  # 동아리마다 최신 공개 활동 몇 개를 재료로 줄지
EXCERPT_LEN = 90


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


# ── 성향 설문 → 동아리 추천 ────────────────────────────────


class RecommendIn(BaseModel):
    answers: str  # 6문항 양자택일 결과. 예: "ABABBA"


def _candidates(db: Session) -> list[dict]:
    """활동중인 동아리 전부 + 각 동아리의 최신 공개 활동 몇 개.

    후보를 모집중으로 좁히지 않는다 — 지금 데이터는 26곳 중 6곳만 모집중이라
    후보가 너무 적어진다. 모집중을 우선하라는 지시는 프롬프트가 맡는다.
    """
    clubs = db.scalars(
        select(Club).where(Club.status == enums.CLUB_ACTIVE).order_by(Club.id)
    ).all()

    out = []
    for club in clubs:
        posts = db.scalars(
            select(Post)
            .where(Post.club_id == club.id, Post.is_public.is_(True))
            .order_by(Post.activity_date.desc())
            .limit(RECENT_POSTS)
        ).all()
        out.append({
            "id": club.id,
            "name": club.name,
            "category": club.category,
            "recruit_status": club.recruit_status,
            "purpose": (club.purpose or "").strip()[:200],
            "posts": [
                {
                    "date": p.activity_date.isoformat(),
                    "title": p.title,
                    "tags": p.tags or [],
                    "excerpt": " ".join((p.body or "").split())[:EXCERPT_LEN],
                }
                for p in posts
            ],
        })
    return out


@router.post("/ai/recommend")
def recommend(
    body: RecommendIn, user: User = Depends(verified_user), db: Session = Depends(get_db)
):
    """설문 결과로 동아리 TOP 3 을 추천한다. **결과는 저장하지 않는다** (api.md §7).

    초안과 같은 규칙으로 사용자 개인 키를 쓴다. 응답의 club_id 는 서버가 다시 검증해
    목록에 없는 동아리는 버린다 — 지어낸 동아리를 화면에 올리지 않기 위해서다.
    """
    answers = (body.answers or "").strip().upper()
    if not answers or any(ch not in "AB" for ch in answers):
        raise errors.ApiError(400, "INVALID_INPUT", "설문 응답 형식이 올바르지 않습니다.")

    key = decrypt_ai_key(user.ai_key_enc) if user.ai_key_enc else None
    if not key:
        raise errors.ApiError(
            403, "AI_KEY_NOT_REGISTERED", "내 정보에서 AI API 키를 등록하면 사용할 수 있어요."
        )

    clubs = _candidates(db)
    if not clubs:
        raise errors.ApiError(409, "NO_CLUBS", "추천할 동아리가 아직 없습니다.")

    try:
        items = ai_recommend.recommend(api_key=key, answers=answers, clubs=clubs)
    except ai_draft.QuotaExceeded as e:
        raise errors.ApiError(429, "AI_QUOTA_EXCEEDED", "키의 사용 한도를 초과했습니다.") from e
    except ai_draft.GatewayError as e:
        raise errors.ApiError(
            502, "AI_GATEWAY_ERROR", "AI 응답을 받지 못했습니다. 잠시 후 다시 시도해주세요."
        ) from e

    return {"items": items, "traits": ai_recommend.answers_to_lines(answers)}
