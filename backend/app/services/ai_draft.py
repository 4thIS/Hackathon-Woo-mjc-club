"""명지전문대학 AI Gateway 호출 (담당 wj · T6).

Base URL·인증 방식은 기획서 §7.0. 키는 **사용자 개인 키**를 복호화해서 쓴다 —
서비스가 공용 키로 대신 호출하지 않는다 (기획서 §9-7).

환각 방지 규칙(기획서 §7.2)은 프롬프트에 반드시 넣는다:
  - 메모와 PDF가 사실의 출처다
  - 사진은 그 사실을 구체화하는 데만 쓴다
  - 메모에 없는 사실을 사진만 보고 쓰지 않는다
"""

import httpx

from ..config import settings


def _headers(api_key: str) -> dict[str, str]:
    """⚠️ User-Agent 를 반드시 넣는다. 기본 UA(python-httpx/…)로 나가면 Cloudflare 가
    403(error 1010)으로 막는다. 키 오류로 착각하기 딱 좋다 (backend/CLAUDE.md)."""
    return {
        "Authorization": f"Bearer {api_key}",
        "User-Agent": settings.ai_user_agent,
        "Accept": "application/json",
    }


DEMO_DRAFT = {
    "title": "성북동에서 필름 두 롤을 태우다",
    "body": (
        "10월 12일, 열두 명이 성북동 일대에서 출사를 진행했습니다.\n"
        "골목과 한옥 담장을 따라 걸으며 각자 준비한 필름 카메라로 촬영했고, "
        "현상은 다음 주 정기 모임에서 함께 진행할 예정입니다."
    ),
    "tags": ["출사", "필름", "성북동"],
    "used": {"memo": True, "pdf": False, "photos": 3, "vision": False},
}

SYSTEM_PROMPT = """당신은 대학 동아리의 활동 기록을 정리하는 편집자입니다.

규칙:
1. 메모와 결과보고서에 적힌 사실만 씁니다. 없는 사실을 지어내지 않습니다.
2. 사진은 이미 있는 사실을 구체화하는 데만 씁니다.
3. "뜻깊은 시간이었습니다" 같은 어느 동아리에나 붙는 문장을 쓰지 않습니다.
4. 제목 1줄, 본문 3~5문장, 태그 2~4개를 JSON으로만 응답합니다.

응답 형식: {"title": "...", "body": "...", "tags": ["...", "..."]}"""


def generate(api_key: str, club_name: str, category: str, memo: str | None, pdf_text: str | None,
             photos: list[bytes] | None = None) -> dict:
    """제목·본문·태그 초안을 만든다. 실패는 예외가 아니라 라우터에서 code로 변환한다."""
    if settings.demo_fallback:
        # 시연 중 게이트웨이가 죽었을 때의 탈출구 (구현계획 §6)
        return DEMO_DRAFT

    # TODO(wj): httpx 로 POST {settings.ai_base_url}/chat/completions/   ← 끝 슬래시 유지
    #   headers = {"Authorization": f"Bearer {api_key}", "User-Agent": settings.ai_user_agent}
    #   model   = settings.ai_model
    #   비전 지원 확인됨(2026-08-06) — 사진은 image_url 의 base64 data URI 로 넘긴다
    raise NotImplementedError("T6 — AI Gateway 호출 미구현")


def verify_key(api_key: str) -> bool:
    """저장 전 키 유효성 확인 — 모델 목록 조회 (기획서 §4.5).

    False = 키가 거부됨(401/403). 게이트웨이 자체가 죽었으면 예외를 올린다 —
    라우터가 400 INVALID_AI_KEY 와 502 AI_GATEWAY_ERROR 를 구분해야 하기 때문이다.
    """
    r = httpx.get(
        f"{settings.ai_base_url}/models/",
        headers=_headers(api_key),
        timeout=15,
    )
    if r.status_code in (401, 403):
        return False
    r.raise_for_status()  # 그 밖의 실패는 게이트웨이 문제 → 라우터가 502 로 바꾼다
    return True
