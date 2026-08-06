"""명지전문대학 AI Gateway 호출 (담당 wj · T6).

Base URL·인증 방식은 기획서 §7.0. 키는 **사용자 개인 키**를 복호화해서 쓴다 —
서비스가 공용 키로 대신 호출하지 않는다 (기획서 §9-7).

환각 방지 규칙(기획서 §7.2)은 프롬프트에 반드시 넣는다:
  - 메모와 PDF가 사실의 출처다
  - 사진은 그 사실을 구체화하는 데만 쓴다
  - 메모에 없는 사실을 사진만 보고 쓰지 않는다
"""

import base64
import json
import logging

import httpx

from ..config import settings

log = logging.getLogger("ai_draft")

MAX_PHOTOS = 4  # 더 넣어도 초안이 좋아지지 않고 토큰만 는다
TIMEOUT = 90  # 비전 + 긴 보고서면 30초를 넘기기도 한다

# 선언한 media type 과 실제 바이트가 다르면 게이트웨이가 400 으로 거부한다.
# 파일 확장자·Content-Type 은 못 믿으므로 매직 넘버로 판별한다.
_MAGIC = (
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
)


def _media_type(raw: bytes) -> str:
    for sig, mime in _MAGIC:
        if raw.startswith(sig):
            return mime
    if raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
        return "image/webp"
    return "image/jpeg"  # 알 수 없으면 가장 흔한 것으로 시도한다


class GatewayError(Exception):
    """게이트웨이가 응답하지 않거나 형태가 깨졌다 → 라우터가 502 로 바꾼다."""


class QuotaExceeded(Exception):
    """키의 사용 한도 초과 → 라우터가 429 로 바꾼다."""


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
2. 사진은 이미 있는 사실을 구체화하는 데만 씁니다. 사진에서 새로운 사실(인원, 장소,
   날짜, 성과)을 만들어내지 않습니다. 확실하지 않으면 쓰지 않습니다.
3. "뜻깊은 시간이었습니다", "즐거운 추억을 만들었습니다" 처럼 어느 동아리에나 붙는
   문장을 쓰지 않습니다. 과장하지 않고 담담하게 씁니다.
4. 본문은 평문입니다. 마크다운 기호와 이모지를 쓰지 않습니다.
5. 제목은 25자 이내로 무슨 활동이었는지 알 수 있게 씁니다.
6. 본문은 3~5문장이며, **모든 문장을 '~습니다' 체로 끝냅니다.**
   ('~했다', '~이다' 같은 평서체를 섞지 않습니다. 한 목록에 두 문체가 섞이면 지저분해 보입니다.)
7. 태그는 2~4개, 각 8자 이내의 명사입니다.

JSON 하나만 출력합니다. 설명이나 코드블록을 덧붙이지 않습니다.
{"title": "...", "body": "...", "tags": ["...", "..."]}"""


def _user_content(
    club_name: str, category: str, memo: str | None, pdf_text: str | None, photos: list[bytes]
) -> list[dict]:
    """사실(메모·PDF)을 먼저 주고 사진을 뒤에 붙인다. 순서가 곧 우선순위다."""
    lines = [f"동아리: {club_name} ({category})"]
    if memo:
        lines.append(f"\n[메모 — 사실의 출처]\n{memo.strip()}")
    if pdf_text:
        lines.append(f"\n[활동 결과보고서에서 추출한 텍스트]\n{pdf_text.strip()}")

    if photos:
        lines.append(
            f"\n사진 {len(photos)}장이 첨부되어 있습니다. 위 사실을 구체화하는 데만 참고하세요."
        )

    content: list[dict] = [{"type": "text", "text": "\n".join(lines)}]
    for raw in photos:
        b64 = base64.b64encode(raw).decode()
        content.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:{_media_type(raw)};base64,{b64}"},
            }
        )
    return content


def _parse(raw: str) -> dict:
    """모델이 코드블록으로 감싸는 경우가 있어 중괄호 구간만 떼어 읽는다."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        text = text.removeprefix("json").strip()

    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise GatewayError("JSON 을 찾지 못했습니다")
    try:
        data = json.loads(text[start : end + 1])
    except json.JSONDecodeError as e:
        raise GatewayError(f"JSON 파싱 실패: {e}") from e

    title = str(data.get("title") or "").strip()
    body = str(data.get("body") or "").strip()
    if not title or not body:
        raise GatewayError("제목·본문이 비어 있습니다")

    tags = [str(t).strip() for t in (data.get("tags") or []) if str(t).strip()]
    return {"title": title[:60], "body": body, "tags": tags[:4]}


def generate(
    api_key: str,
    club_name: str,
    category: str,
    memo: str | None,
    pdf_text: str | None,
    photos: list[bytes] | None = None,
) -> dict:
    """제목·본문·태그 초안을 만든다. 실패는 예외가 아니라 라우터에서 code로 변환한다."""
    photos = (photos or [])[:MAX_PHOTOS]

    if settings.demo_fallback:
        # 시연 중 게이트웨이가 죽었을 때의 탈출구 (구현계획 §6)
        return {**DEMO_DRAFT, "used": {**DEMO_DRAFT["used"], "photos": len(photos)}}

    payload = {
        "model": settings.ai_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _user_content(club_name, category, memo, pdf_text, photos)},
        ],
        "max_tokens": 1200,
        "temperature": 0.4,  # 사실 위주라 창의성이 필요 없다
    }

    try:
        r = httpx.post(
            f"{settings.ai_base_url}/chat/completions/",  # 끝 슬래시 유지
            headers=_headers(api_key),
            json=payload,
            timeout=TIMEOUT,
        )
    except httpx.HTTPError as e:
        raise GatewayError(str(e)) from e

    if r.status_code == 429:
        raise QuotaExceeded(r.text[:200])
    if r.status_code >= 400:
        log.warning("게이트웨이 %s: %s", r.status_code, r.text[:300])
        raise GatewayError(f"{r.status_code}")

    try:
        content = r.json()["choices"][0]["message"]["content"]
    except (KeyError, IndexError, ValueError) as e:
        raise GatewayError("응답 형태가 예상과 다릅니다") from e

    draft = _parse(content)
    draft["used"] = {
        "memo": bool(memo),
        "pdf": bool(pdf_text),
        "photos": len(photos),
        # 사진을 실제로 실어 보냈는지. 이 모델은 비전을 받는 것이 확인됐다 (기획서 §7.0)
        "vision": bool(photos),
    }
    return draft


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
