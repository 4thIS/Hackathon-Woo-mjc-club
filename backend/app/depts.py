"""학과 목록 — crawl_depts.py 가 만든 data/depts.json 이 원본이다.

앱이 학교 홈페이지를 직접 호출하지 않는다. 파일을 한 번 읽어 메모리에 둔다.
목록이 비면 아무도 가입할 수 없으므로, 파일이 없거나 깨졌으면 빈 목록 대신
**검증을 통과시킨다** — 가입을 막는 것보다 학과 값이 자유로운 편이 낫다.
"""

import json
import logging
from functools import lru_cache
from pathlib import Path

log = logging.getLogger(__name__)

DATA_PATH = Path(__file__).parent.parent / "data" / "depts.json"


@lru_cache(maxsize=1)
def dept_names() -> tuple[str, ...]:
    try:
        raw = json.loads(DATA_PATH.read_text(encoding="utf-8"))
        names = tuple(str(x) for x in raw.get("items", []) if str(x).strip())
    except (OSError, ValueError) as e:
        log.warning("학과 목록을 읽지 못했습니다 (%s). 학과 검증을 건너뜁니다.", e)
        return ()
    if not names:
        log.warning("학과 목록이 비어 있습니다. 학과 검증을 건너뜁니다.")
    return names


def is_valid(name: str) -> bool:
    """목록에 있는 학과인가. 목록을 못 읽었으면 막지 않는다."""
    names = dept_names()
    return not names or name in names
