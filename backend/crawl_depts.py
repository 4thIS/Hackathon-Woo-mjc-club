"""명지전문대학 학과 목록을 긁어 backend/data/depts.json 을 만든다.

    uv run python crawl_depts.py            # 긁어서 JSON 갱신
    uv run python crawl_depts.py --dry-run  # 화면에만 출력

**손으로 돌리는 스크립트다.** 앱 실행 경로에 붙이지 않는다 (crawl_clubs.py 와 같은 규칙).
가입 화면이 학교 서버 상태에 종속되면 학교가 점검할 때 아무도 가입하지 못한다.

학과 링크는 페이지 곳곳에 흩어져 있다 — 좌측 메뉴(lnb), 사이트 팝업(site_list_n),
본문 탭(tab_part04). 이 중 본문 탭만 '학과'로만 채워져 있고 나머지는 학부·제도
이름(자유전공학부 · 전과 · 융복합 모듈전공)이 섞인다. 그래서 탭만 읽는다.
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import httpx  # noqa: E402
from bs4 import BeautifulSoup  # noqa: E402

SOURCE_URL = "https://www.mjc.ac.kr/ibuilder.do?menu_idx=100"
OUT_PATH = Path(__file__).parent / "data" / "depts.json"
SELECTOR = "ul.tab_part04 li"
MIN_ROWS = 30  # 37개가 정상. 이보다 적으면 페이지가 바뀐 것으로 본다

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
)


def _clean(text: str) -> str:
    return " ".join(text.split())


def parse_depts(html: str) -> list[str]:
    """학과 이름만 뽑는다. 구조가 다르면 RuntimeError 를 올린다.

    조용히 빈 결과를 돌려주면 JSON 이 빈 채로 덮어써지고, 그 순간 아무도 가입할 수 없다.
    """
    soup = BeautifulSoup(html, "html.parser")
    items = soup.select(SELECTOR)
    if not items:
        raise RuntimeError(f"학과 목록을 찾지 못했습니다 — 페이지가 개편되었을 수 있습니다: {SOURCE_URL}")

    names = []
    for li in items:
        name = _clean(li.get_text())
        # 학부·제도는 학과가 아니다. 사람이 고르는 것은 소속 학과 하나뿐이다
        if not name or name.endswith(("학부", "전공")) or len(name) > 30:
            continue
        if name not in names:
            names.append(name)

    if len(names) < MIN_ROWS:
        raise RuntimeError(f"학과가 {len(names)}개뿐입니다 (기대: {MIN_ROWS}개 이상) — 파싱이 깨졌습니다")
    return names


def fetch(url: str) -> str:
    r = httpx.get(url, headers={"User-Agent": USER_AGENT}, timeout=20, follow_redirects=True)
    r.raise_for_status()
    return r.text


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="파일을 쓰지 않고 결과만 출력")
    args = ap.parse_args()

    names = parse_depts(fetch(SOURCE_URL))
    print(f"학과 {len(names)}개")
    for n in names:
        print("  -", n)

    if args.dry_run:
        return 0

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(
        json.dumps(
            {"source": SOURCE_URL, "fetched_at": date.today().isoformat(), "items": names},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"\n저장: {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
