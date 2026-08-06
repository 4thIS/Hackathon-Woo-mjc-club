"""명지전문대학 AI Gateway 호출 (담당 wj · T6).

Base URL·인증 방식은 기획서 §7.0. 키는 **사용자 개인 키**를 복호화해서 쓴다 —
서비스가 공용 키로 대신 호출하지 않는다 (기획서 §9-7).

환각 방지 규칙(기획서 §7.2)은 프롬프트에 반드시 넣는다:
  - 메모와 PDF가 사실의 출처다
  - 사진은 그 사실을 구체화하는 데만 쓴다
  - 메모에 없는 사실을 사진만 보고 쓰지 않는다
"""

from ..config import settings

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

    # TODO(wj): httpx 로 POST {settings.ai_base_url}/chat/completions
    #   headers = {"Authorization": f"Bearer {api_key}"}
    #   model   = settings.ai_model
    #   ① 텍스트만으로 먼저 성공시킬 것. ② 이미지 입력은 지원 확인 후 (기획서 §7.4)
    raise NotImplementedError("T6 — AI Gateway 호출 미구현")


def verify_key(api_key: str) -> bool:
    """저장 전 키 유효성 확인 — 모델 목록 조회 (기획서 §4.5)."""
    # TODO(wj): GET {settings.ai_base_url}/models 로 200 확인
    raise NotImplementedError("T6 — AI 키 검증 미구현")
