"""데모 데이터 주입.

    uv run python seed.py          # 비어 있을 때만 넣는다
    uv run python seed.py --reset  # 전부 지우고 다시 넣는다

**동아리 정보(이름·분야·창립년도·목적)는 학교 공개 자료다** —
data/clubs.json, 출처는 https://www.mjc.ac.kr/ibuilder.do?menu_idx=155
**활동 글과 계정은 데모용 창작이다.**

25개 중 6개(DEMO_LED)에만 동아리장을 배정하고 모집중으로 둔다.
승인해줄 사람이 없는 동아리를 모집중으로 두지 않기 위해서다.
데모 계정 비밀번호는 전부 `test1234!` 다.
"""

import json
import sys
from datetime import date, timedelta
from pathlib import Path

# Windows 콘솔은 기본이 cp949 라 '—' 같은 글자에서 UnicodeEncodeError 로 죽는다.
# 주입은 이미 끝난 뒤 마지막 print 에서 터져서 실패한 것처럼 보인다.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from sqlalchemy import select

from app import enums
from app.db import SessionLocal, create_all, engine
from app.models import (
    Base,
    Club,
    ClubApplication,
    ClubMember,
    JoinForm,
    JoinRequest,
    LeaveRequest,
    Like,
    Post,
    User,
)
from app.security import hash_password

PW = hash_password("test1234!")


def u(
    sid: str,
    name: str,
    dept: str,
    *,
    grade: int | None = None,
    admin: bool = False,
    status: str = enums.ACADEMIC_ENROLLED,
) -> User:
    """학번은 10자리 숫자다 (예: 2022261026). 앞 4자리가 입학년도.

    학년은 학번에서 유추하지 않는다 — 휴학·재수·편입이면 어긋난다. 본인이 고른 값이다.
    """
    return User(
        id=sid,
        email=f"{sid}@mjc.ac.kr",
        pw_hash=PW,
        name=name,
        dept=dept,
        birth=date(int(sid[:4]) - 19, 3, 11),
        gender="남",
        grade=grade,
        academic_status=status,
        is_admin=admin,
        email_verified=True,
    )


USERS = [
    u("2015260001", "관리자", "공공행정서비스과", admin=True),
    u("2024260001", "이우진", "커뮤니케이션디자인과", grade=3),
    u("2024260002", "김태희", "실용음악과", grade=3),
    u("2024260003", "박찬우", "컴퓨터공학과", grade=3),
    u("2026261234", "신입생", "컴퓨터공학과", grade=1),
    u("2026261235", "김서연", "보건의료정보과", grade=2),  # 편입 — 학번은 26학번이지만 2학년
    u("2019260001", "졸업생", "컴퓨터공학과", status=enums.ACADEMIC_GRADUATED),
    # 어느 동아리에도 속하지 않은 지원자들 — 시연에서 '신청자 목록 → 승인' 을 보여주려면
    # 심사중인 신청이 미리 쌓여 있어야 한다 (시연 시나리오 1:30)
    u("2026261240", "김도윤", "전기공학과", grade=1),
    u("2026261241", "이서준", "경영학과", grade=1),
    u("2025260242", "최유진", "보건의료정보과", grade=2),
]

ADMIN_ID = "2015260001"
LEADER_IDS = ["2024260001", "2024260002", "2024260003"]
STUDENT_ID = "2026261234"
STUDENT2_ID = "2026261235"
OB_ID = "2019260001"
APPLICANTS = ["2026261240", "2026261241", "2025260242"]

# 동아리장이 배정되는 데모 동아리. 이 여섯 곳만 모집중이고 활동 글이 붙는다.
# 승인해줄 사람이 없는 동아리를 모집중으로 두지 않기 위해서다 (설계 §3.3)
DEMO_LED = ["고리사진부", "축구부", "노래창고", "희비", "T.M.I.M", "e-sports"]

CLUBS_JSON = Path(__file__).parent / "data" / "clubs.json"
POSTS_JSON = Path(__file__).parent / "data" / "seed_posts.json"
CREDITS_JSON = Path(__file__).parent / "data" / "photo_credits.json"


def load_photos() -> dict[str, list[str]]:
    """collect_photos.py 가 받아 둔 사진을 동아리별로 묶는다.

    전부 CC0·퍼블릭도메인이고 출처는 photo_credits.json 에 남아 있다.
    파일이 없으면 사진 없이 시드한다 — 사진 때문에 시드가 실패하면 안 된다.
    """
    if not CREDITS_JSON.exists():
        return {}
    raw = json.loads(CREDITS_JSON.read_text(encoding="utf-8"))
    out: dict[str, list[str]] = {}
    for it in raw.get("items", []):
        out.setdefault(it["club"], []).append(f"/uploads/{it['file']}")
    return out


PHOTOS = load_photos()


def load_clubs() -> list[dict]:
    """crawl_clubs.py 가 만든 JSON 을 Club 생성 인자로 바꾼다.

    지도교수·정기모임·현재 기수는 원본에 없다. 비워 둔다.
    대표 이미지는 collect_photos.py 가 받아 둔 첫 장을 쓴다.
    """
    raw = json.loads(CLUBS_JSON.read_text(encoding="utf-8"))
    out = []
    for c in raw["clubs"]:
        purpose = c["purpose"]
        if c.get("main_activities"):
            purpose = f"{purpose}\n\n주요사업: {c['main_activities']}"
        demo = c["name"] in DEMO_LED
        out.append(
            dict(
                name=c["name"],
                category=c["category"],
                founded_year=c["founded_year"],
                purpose=purpose,
                advisor="",
                image=(PHOTOS.get(c["name"]) or [None])[0],
                recruit_status=enums.RECRUIT_MOJIP if demo else enums.RECRUIT_CLOSED,
                current_gen=1 if demo else None,
            )
        )
    return out


CLUBS = load_clubs()

# 활동 글 — data/seed_posts.json 이 원본이다.
# ★ 활동 글은 데모용 창작이다. 동아리 정보(이름·분야·창립년도·목적)만 학교 공개 자료다.
def load_posts() -> list[tuple]:
    raw = json.loads(POSTS_JSON.read_text(encoding="utf-8"))
    out = []
    for club_name, rows in raw["posts"].items():
        for days_ago, title, body, tags, is_public in rows:
            out.append((club_name, days_ago, title, body, tags, is_public))
    return out


POSTS = load_posts()

# 가입폼이 있는 동아리 — 신청 모달에 폼이 렌더되는 걸 시연에서 보여준다 (기획서 §5.3)
JOIN_FORM_FIELDS = [
    {"key": "motive", "label": "지원 동기", "type": "textarea", "required": True},
    {"key": "camera", "label": "가지고 있는 카메라가 있나요?", "type": "text", "required": False},
]

# 심사중인 가입 신청 — (지원자 학번, 동아리 이름, 폼 답변)
# 시연 1:30 '신청자 확인 → 승인 → 기수 자동 부여' 장면의 재료다
PENDING_JOINS = [
    (APPLICANTS[0], "고리사진부", {"motive": "필름 사진을 배우고 싶어서 지원합니다.", "camera": "없습니다"}),
    (APPLICANTS[1], "고리사진부", {"motive": "동아리 전시를 보고 관심이 생겼습니다.", "camera": "펜탁스 ME"}),
    (APPLICANTS[2], "축구부", {}),
]


def main() -> None:
    reset = "--reset" in sys.argv
    create_all()

    if reset:
        Base.metadata.drop_all(bind=engine)
        create_all()
        print("기존 데이터 삭제 후 재생성")

    db = SessionLocal()
    try:
        if db.scalar(select(User).limit(1)) is not None:
            print("이미 데이터가 있습니다. 다시 넣으려면 --reset")
            return

        db.add_all(USERS)
        db.flush()

        clubs = [Club(**c) for c in CLUBS]
        db.add_all(clubs)
        db.flush()
        by_name = {c.name: c for c in clubs}

        # 모든 동아리에 동아리장을 둔다 — 활동 기록이 붙으려면 쓴 사람이 있어야 한다.
        # 다만 '모집중' 은 데모 여섯 곳뿐이다(load_clubs). 활동은 쌓였지만 지금은
        # 모집을 닫아 둔 동아리가 대부분인, 실제에 가까운 모습이다.
        ordered = DEMO_LED + [c.name for c in clubs if c.name not in DEMO_LED]
        leader_of = {}
        for i, name in enumerate(ordered):
            club = by_name[name]
            leader_of[name] = LEADER_IDS[i % 3]
            db.add(ClubMember(user_id=leader_of[name], club_id=club.id,
                              role=enums.ROLE_LEADER, gen=1))
            if name not in DEMO_LED:
                continue
            db.add(ClubMember(user_id=OB_ID, club_id=club.id, role=enums.ROLE_MEMBER,
                              membership=enums.MEMBERSHIP_OB, gen=1))
            # 학생 데모 계정은 두 곳에만 넣는다 —
            # 전부 부원이면 시연에서 '가입 신청'을 누를 곳이 없다
            if i < 2:
                db.add(ClubMember(user_id=STUDENT_ID, club_id=club.id,
                                  role=enums.ROLE_MEMBER, gen=club.current_gen))
            if i == 0 or i == 3:
                db.add(ClubMember(user_id=STUDENT2_ID, club_id=club.id,
                                  role=enums.ROLE_MEMBER, gen=club.current_gen))
        db.flush()

        today = date.today()
        posts = []
        used_photo = {}          # 동아리별로 사진을 돌려 쓴다 (대표 0번은 빼고)
        for club_name, days_ago, title, body, tags, is_public in POSTS:
            club = by_name[club_name]
            pool = PHOTOS.get(club_name, [])[1:]
            shot = []
            if pool:
                k = used_photo.get(club_name, 0)
                shot = [pool[k % len(pool)]]
                used_photo[club_name] = k + 1
            posts.append(Post(
                club_id=club.id,
                # flush 직후 club.members 는 아직 안 채워질 수 있다. 위에서 모은 dict 를 쓴다
                author_id=leader_of[club_name],
                title=title,
                body=body,
                photos=shot,
                activity_date=today - timedelta(days=days_ago),
                tags=tags,
                is_public=is_public,
            ))
        db.add_all(posts)
        db.flush()

        for i, p in enumerate(posts):
            if p.is_public:
                db.add(Like(user_id=STUDENT_ID, post_id=p.id))
                if i % 3 == 0:
                    db.add(Like(user_id=STUDENT2_ID, post_id=p.id))

        # --- 시연용 심사 대기 건 (빈 화면 금지) ---------------------------
        db.add(JoinForm(club_id=by_name["고리사진부"].id, fields=JOIN_FORM_FIELDS, required=True))

        for uid, club_name, answers in PENDING_JOINS:
            db.add(JoinRequest(user_id=uid, club_id=by_name[club_name].id, form_answer=answers))

        # 관리자 승인 장면용
        db.add(ClubApplication(
            applicant_id=APPLICANTS[0],
            name="독서토론회 책갈피",
            category="학술·전공",
            founded_year=2026,
            purpose="한 달에 한 권을 정해 읽고 토론합니다. 학기말에 서평집을 냅니다.",
            advisor="정민석",
        ))

        # 동아리장 화면의 탈퇴 요청 목록도 비지 않게 한다
        db.add(LeaveRequest(user_id=STUDENT2_ID, club_id=by_name["고리사진부"].id))

        db.commit()
        print(f"완료 — 유저 {len(USERS)} · 동아리 {len(clubs)} · 활동글 {len(posts)}")
        print(f"        심사중 가입신청 {len(PENDING_JOINS)} · 개설신청 1 · 탈퇴요청 1 · 가입폼 1")
        print(f"데모 계정: {STUDENT_ID}@mjc.ac.kr (학생) · {LEADER_IDS[0]}@mjc.ac.kr (동아리장)")
        print(f"관리자:   {ADMIN_ID}@mjc.ac.kr · 비밀번호는 전부 test1234!")
    finally:
        db.close()


if __name__ == "__main__":
    main()
