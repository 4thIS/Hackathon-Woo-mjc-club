"""동아리 대표·활동 사진을 모은다 — Openverse 에서 CC0/퍼블릭도메인만.

    uv run --with pillow python collect_photos.py

라이선스가 분명한 것만 받는다. 받은 사진의 출처·라이선스는 photo_credits.json 에
함께 남긴다 — 시연물이라도 출처 없는 사진을 쓰지 않기 위해서다.
"""
import io
import json
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import httpx  # noqa: E402
from PIL import Image  # noqa: E402

UA = "MJC-Club-Archive/1.0 (hackathon demo)"
OUT = Path(__file__).parent / "uploads" / "seed"
CREDITS = Path(__file__).parent / "data" / "photo_credits.json"
WIDTH = 1200

# 동아리 → 검색어. 성격이 드러나는 사진을 고른다
TOPICS = {
    "T.M.I.M": ["volunteer cleanup", "food bank volunteers", "charity volunteers"],
    "C.F.M": ["sign language", "stage performance", "volunteer group"],
    "고리사진부": ["photography camera", "darkroom photography", "photo exhibition"],
    "유스호스텔": ["backpacker travel", "hostel travel", "train journey"],
    "씨네필": ["cinema movie theater", "film projector", "movie screening"],
    "P.T.P": ["students talking campus", "group discussion", "friends meeting"],
    "블랙비트": ["hip hop dance", "rap microphone", "street dance"],
    "때깔": ["art painting studio", "watercolor painting", "sketch drawing"],
    "궁상각치우": ["traditional korean music", "orchestra rehearsal", "music concert"],
    "물레방아": ["acoustic guitar", "band music practice", "singing performance"],
    "노래창고": ["choir singing", "vocal concert", "microphone stage"],
    "한울": ["korean traditional drum", "folk performance", "traditional dance"],
    "희비": ["theater stage play", "drama rehearsal", "stage lighting"],
    "e-sports": ["gaming keyboard", "computer lab students", "esports arena"],
    "R-eve": ["virtual reality headset", "augmented reality", "3d design computer"],
    "산악부": ["hiking mountain", "mountain trail", "climbing rocks"],
    "테니스부": ["tennis court", "tennis racket", "tennis player"],
    "ACE": ["basketball game", "sports team", "gym workout"],
    "탁구부": ["table tennis", "ping pong paddle", "sports hall"],
    "축구부": ["soccer football match", "football stadium", "soccer training"],
    "Freestep": ["dance performance", "dance practice studio", "street dance"],
    "C.U(응원단)": ["cheerleaders squad", "cheerleading performance", "marching band"],
    "기독교학생회": ["church interior", "bible open", "worship service"],
    "카톨릭학생회": ["cathedral interior", "chapel candles", "catholic cathedral"],
    "C.C.C.": ["campus students group", "prayer meeting", "youth gathering"],
}


def search(q: str, n: int = 20) -> list[dict]:
    r = httpx.get(
        "https://api.openverse.org/v1/images/",
        params={"q": q, "license": "cc0,pdm", "page_size": n, "mature": "false"},
        headers={"User-Agent": UA}, timeout=30,
    )
    r.raise_for_status()
    return r.json().get("results", [])


def on_topic(it: dict, must: list[str]) -> bool:
    """CC0 풀이 얕아 검색어와 무관한 사진이 섞인다.
    제목·태그에 핵심어가 실제로 있는 것만 쓴다."""
    # 태그는 업로더가 아무렇게나 붙인다 — 제목만 믿는다
    hay = (it.get("title") or "").lower()
    return any(w in hay for w in must)


def fetch_image(url: str) -> Image.Image | None:
    try:
        r = httpx.get(url, headers={"User-Agent": UA}, timeout=40, follow_redirects=True)
        r.raise_for_status()
        im = Image.open(io.BytesIO(r.content))
        im.load()
        return im
    except Exception:
        return None


def is_flat(im: Image.Image) -> bool:
    """단색에 가까운 이미지는 카드에서 색판처럼 보인다. 표준편차로 거른다."""
    from PIL import ImageStat
    st = ImageStat.Stat(im.convert("L").resize((64, 64)))
    return st.stddev[0] < 18


def save(im: Image.Image, path: Path) -> bool:
    try:
        im = im.convert("RGB")
        if im.width > WIDTH:
            im = im.resize((WIDTH, round(im.height * WIDTH / im.width)), Image.LANCZOS)
        # 가로가 지나치게 긴 파노라마는 카드에서 보기 나쁘다 — 가운데를 4:3 으로 자른다
        if im.width / im.height > 2.2:
            h = im.height
            w = int(h * 4 / 3)
            left = (im.width - w) // 2
            im = im.crop((left, 0, left + w, h))
        path.parent.mkdir(parents=True, exist_ok=True)
        im.save(path, "JPEG", quality=82, optimize=True)
        return True
    except Exception:
        return False


def main() -> None:
    credits = []
    for club, queries in TOPICS.items():
        slug = f"{abs(hash(club)) % 10**8:08d}"
        got = 0
        for q in queries:
            if got >= 4:
                break
            # 첫 단어가 곧 핵심어다. 'match' 같은 흔한 낱말까지 받아주면
            # 검색어와 무관한 사진이 그대로 통과한다
            must = [q.lower().split()[0]]
            for it in search(q):
                if got >= 4:
                    break
                if not on_topic(it, must):
                    continue
                url = it.get("url")
                if not url:
                    continue
                im = fetch_image(url)
                if im is None or im.width < 500:
                    continue
                if is_flat(im):
                    continue
                name = f"{slug}-{got}.jpg"
                if not save(im, OUT / name):
                    continue
                credits.append({
                    "club": club, "file": f"seed/{name}",
                    "title": it.get("title"), "creator": it.get("creator"),
                    "license": it.get("license"), "source": it.get("foreign_landing_url"),
                })
                got += 1
            time.sleep(0.4)
        print(f"{club:14} {got}장" + ("  ← 부족" if got < 4 else ""))

    CREDITS.parent.mkdir(parents=True, exist_ok=True)
    CREDITS.write_text(json.dumps({"items": credits}, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")
    print(f"\n총 {len(credits)}장 · 출처 기록 {CREDITS}")


if __name__ == "__main__":
    main()
