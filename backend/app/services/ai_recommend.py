"""성향 설문 → 동아리 추천 TOP 3.

키는 **사용자 개인 키**를 복호화해서 쓴다(AI 초안과 같은 규칙). 결과는 어디에도
저장하지 않는다 — 호출한 사람에게 한 번 보여주고 끝이다.

환각 방지는 초안과 같은 원칙이다:
  - 후보는 서버가 준 목록뿐. 목록에 없는 동아리를 만들어내지 않는다
  - 추천 이유는 준 소개·활동 기록에 있는 내용으로만 쓴다
  - 없는 활동을 지어내지 않는다 (서버가 id 를 다시 검증한다)
"""

import json
import logging

import httpx

from ..config import settings
from .ai_draft import GatewayError, QuotaExceeded, _headers

log = logging.getLogger("ai_recommend")

TIMEOUT = 60
TOP_N = 3

# 설문 6축 — 각 문항의 A/B 가 무엇을 뜻하는지. 프롬프트에 그대로 실린다
AXES = [
    ("몸을 움직이는 활동을 좋아함", "앉아서 만들고 다듬는 활동을 좋아함"),
    ("여러 사람과 넓게 어울리고 싶음", "소수와 깊게 친해지고 싶음"),
    ("대회·성과처럼 목표가 뚜렷한 편이 좋음", "부담 없는 취미·휴식이 좋음"),
    ("정해진 요일에 규칙적으로 모이는 편이 좋음", "일정이 유연한 편이 좋음"),
    ("남을 돕거나 사회에 기여하는 활동에 끌림", "내 실력을 키우는 활동에 끌림"),
    ("무대·전시처럼 결과를 보여주는 것이 좋음", "과정 자체를 즐기는 것이 좋음"),
]

SYSTEM_PROMPT = """당신은 대학 동아리 추천을 돕는 상담자입니다.

규칙:
1. 반드시 주어진 후보 목록 안에서만 고릅니다. 목록에 없는 동아리를 만들어내지 않습니다.
2. 추천 이유는 주어진 소개·주요사업·활동 기록에 실제로 적힌 내용으로만 씁니다.
   목록에 없는 활동·수상·규모를 지어내지 않습니다.
3. 설문 응답과 그 동아리의 어떤 점이 맞는지 연결해서 씁니다.
   "좋은 동아리입니다" 처럼 어디에나 붙는 문장을 쓰지 않습니다.
4. 모집중인 동아리를 우선하되, 성향이 확실히 더 맞는 곳이 있으면 모집마감이어도 넣습니다.
5. 이유는 2~3문장이며 모든 문장을 '~습니다' 체로 끝냅니다.
6. 서로 다른 동아리 3개를 순위대로 고릅니다.

JSON 하나만 출력합니다. 설명이나 코드블록을 덧붙이지 않습니다.
{"items": [{"club_id": 1, "reason": "..."},
           {"club_id": 2, "reason": "..."},
           {"club_id": 3, "reason": "..."}]}"""


def answers_to_lines(answers: str) -> list[str]:
    """'ABABBA' → 사람이 읽는 성향 문장. 길이가 모자라면 그만큼만 읽는다."""
    out = []
    for i, (a, b) in enumerate(AXES):
        if i >= len(answers):
            break
        out.append(a if answers[i].upper() == "A" else b)
    return out


def _user_content(answers: str, clubs: list[dict]) -> str:
    lines = ["[설문 결과 — 이 사람의 성향]"]
    lines += [f"- {s}" for s in answers_to_lines(answers)]

    lines.append("\n[후보 동아리 — 이 목록 안에서만 고릅니다]")
    for c in clubs:
        head = f"\n#{c['id']} {c['name']} · {c['category']} · {c['recruit_status']}"
        lines.append(head)
        if c.get("purpose"):
            lines.append(f"  소개: {c['purpose']}")
        if c.get("main_activities"):
            lines.append(f"  주요사업: {c['main_activities']}")
        for p in c.get("posts", []):
            tag = f" [{' '.join(p['tags'])}]" if p.get("tags") else ""
            lines.append(f"  최근활동({p['date']}): {p['title']}{tag} — {p['excerpt']}")
        if not c.get("posts"):
            lines.append("  최근활동: 공개된 기록 없음")

    lines.append(f"\n위 후보 중 이 사람에게 맞는 {TOP_N}곳을 순위대로 club_id 로 답하세요.")
    return "\n".join(lines)


def _parse(raw: str, allowed: dict[int, dict]) -> list[dict]:
    """모델이 코드블록으로 감싸는 경우가 있어 중괄호 구간만 떼어 읽는다.

    목록에 없는 club_id 는 버린다 — 지어낸 동아리를 화면에 올리지 않기 위해서다.
    """
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("```")[1].removeprefix("json").strip()

    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise GatewayError("JSON 을 찾지 못했습니다")
    try:
        data = json.loads(text[start : end + 1])
    except json.JSONDecodeError as e:
        raise GatewayError(f"JSON 파싱 실패: {e}") from e

    picked: list[dict] = []
    seen: set[int] = set()
    for row in data.get("items") or []:
        try:
            cid = int(row.get("club_id"))
        except (TypeError, ValueError):
            continue
        club = allowed.get(cid)
        reason = str(row.get("reason") or "").strip()
        if club is None or cid in seen or not reason:
            log.info("추천 응답에서 %s 버림 (목록에 없거나 중복·이유 없음)", row.get("club_id"))
            continue
        seen.add(cid)
        picked.append({
            "club_id": cid,
            "name": club["name"],
            "category": club["category"],
            "recruit_status": club["recruit_status"],
            "reason": reason,
        })

    if not picked:
        raise GatewayError("추천 결과가 비어 있습니다")
    return picked[:TOP_N]


def recommend(api_key: str, answers: str, clubs: list[dict]) -> list[dict]:
    """설문 응답과 동아리 목록으로 TOP 3 을 고른다. 결과는 저장하지 않는다."""
    allowed = {c["id"]: c for c in clubs}

    payload = {
        "model": settings.ai_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _user_content(answers, clubs)},
        ],
        "max_tokens": 900,
        "temperature": 0.5,
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

    return _parse(content, allowed)
