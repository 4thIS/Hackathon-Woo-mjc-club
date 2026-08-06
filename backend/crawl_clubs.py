"""명지전문대학 동아리 목록을 긁어 backend/data/clubs.json 을 만든다.

    uv run python crawl_clubs.py            # 긁어서 JSON 갱신
    uv run python crawl_clubs.py --dry-run  # 화면에만 출력

**손으로 돌리는 스크립트다.** seed.py 나 앱 실행 경로에 붙이지 않는다.
seed 가 네트워크를 타면 시연 중 학교 서버 상태에 서비스가 종속된다.

산출물 clubs.json 이 git 의 원본이다. 이 프로젝트는 마이그레이션이 없어
스키마가 바뀔 때마다 DB 를 통째로 날리므로, DB 를 원본으로 삼을 수 없다.
"""

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

# Windows 콘솔은 기본이 cp949 라 '·' 같은 글자에서 UnicodeEncodeError 로 죽는다.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import httpx  # noqa: E402
from bs4 import BeautifulSoup  # noqa: E402

SOURCE_URL = "https://www.mjc.ac.kr/ibuilder.do?menu_idx=155"
OUT_PATH = Path(__file__).parent / "data" / "clubs.json"
EXPECTED_HEADERS = ["분야", "동아리명", "창립년도", "목적", "주요사업"]
MIN_ROWS = 20  # 25개가 정상. 이보다 적으면 페이지가 바뀐 것으로 본다

# 원본 분류 → 우리 열거값. 재해석하지 않는다 (설계 §3.1)
CATEGORY_MAP = {
    "학술": "학술·전공",
    "체육": "체육",
    "봉사": "봉사",
    "종교": "종교",
}

_COUNT_SUFFIX = re.compile(r"\(\s*\d+\s*개\s*\)\s*$")


def _clean(text: str) -> str:
    return " ".join(text.split())


def parse_clubs(html: str) -> list[dict]:
    """표에서 동아리 목록을 뽑는다. 구조가 다르면 RuntimeError 를 올린다.

    조용히 빈 결과를 돌려주면 JSON 이 빈 채로 덮어써진다. 그게 최악이다.
    """
    soup = BeautifulSoup(html, "html.parser")
    table = soup.select_one("table.tbl_type01")
    if table is None:
        raise RuntimeError(f"표를 찾지 못했습니다 — 페이지가 개편되었을 수 있습니다: {SOURCE_URL}")

    headers = [_clean(th.get_text()) for th in table.select("thead th")]
    if headers != EXPECTED_HEADERS:
        raise RuntimeError(f"컬럼 구성이 다릅니다: {headers} (기대: {EXPECTED_HEADERS})")

    rows: list[dict] = []
    source_category = None
    for tr in table.select("tbody tr"):
        cells = tr.find_all(["th", "td"])
        if cells and cells[0].name == "th":
            source_category = _COUNT_SUFFIX.sub("", _clean(cells[0].get_text())).strip()
            cells = cells[1:]
        if source_category is None or len(cells) < 4:
            continue

        name, year, purpose, activities = (_clean(c.get_text()) for c in cells[:4])
        rows.append(
            {
                "name": name,
                "category": CATEGORY_MAP.get(source_category, "취미·교양"),
                "source_category": source_category,
                "founded_year": int(year),
                "purpose": purpose,
                "main_activities": activities,
            }
        )
    return rows


def fetch_html() -> str:
    r = httpx.get(SOURCE_URL, timeout=20, follow_redirects=True)
    r.raise_for_status()
    return r.text


def main() -> int:
    ap = argparse.ArgumentParser(description="명지전문대 동아리 목록 크롤러")
    ap.add_argument("--dry-run", action="store_true", help="파일을 쓰지 않고 화면에만 출력")
    args = ap.parse_args()

    clubs = parse_clubs(fetch_html())
    if len(clubs) < MIN_ROWS:
        raise RuntimeError(
            f"동아리 {len(clubs)}개만 파싱됐습니다 (최소 {MIN_ROWS}). JSON 을 건드리지 않습니다."
        )

    counts: dict[str, int] = {}
    for c in clubs:
        counts[c["source_category"]] = counts.get(c["source_category"], 0) + 1

    print(f"동아리 {len(clubs)}개")
    for k, v in counts.items():
        print(f"  {k:6s} {v}")

    if args.dry_run:
        print("\n--dry-run — 파일을 쓰지 않았습니다.")
        return 0

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {"source": SOURCE_URL, "crawled_at": date.today().isoformat(), "clubs": clubs}
    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\n저장 완료 → {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
