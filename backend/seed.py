"""데모 데이터 주입.

    uv run python seed.py          # 비어 있을 때만 넣는다
    uv run python seed.py --reset  # 전부 지우고 다시 넣는다

**동아리 정보(이름·분야·창립년도·목적)는 학교 공개 자료다** —
data/clubs.json, 출처는 https://www.mjc.ac.kr/ibuilder.do?menu_idx=155
**활동 글과 계정은 데모용 창작이다.**

25개 중 6개(DEMO_LED)에만 동아리장을 배정하고 모집중으로 둔다.
승인해줄 사람이 없는 동아리를 모집중으로 두지 않기 위해서다.
데모 계정 비밀번호는 전부 `test1234` 다.
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

PW = hash_password("test1234")


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
    u("2015260001", "관리자", "학생지원팀", admin=True),
    u("2024260001", "이우진", "시각디자인과", grade=3),
    u("2024260002", "김태희", "실용음악과", grade=3),
    u("2024260003", "박찬우", "컴퓨터공학과", grade=3),
    u("2026261234", "신입생", "컴퓨터공학과", grade=1),
    u("2026261235", "김서연", "간호학과", grade=2),  # 편입 — 학번은 26학번이지만 2학년
    u("2019260001", "졸업생", "컴퓨터공학과", status=enums.ACADEMIC_GRADUATED),
    # 어느 동아리에도 속하지 않은 지원자들 — 시연에서 '신청자 목록 → 승인' 을 보여주려면
    # 심사중인 신청이 미리 쌓여 있어야 한다 (시연 시나리오 1:30)
    u("2026261240", "김도윤", "전기공학과", grade=1),
    u("2026261241", "이서준", "경영학과", grade=1),
    u("2025260242", "최유진", "간호학과", grade=2),
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


def load_clubs() -> list[dict]:
    """crawl_clubs.py 가 만든 JSON 을 Club 생성 인자로 바꾼다.

    지도교수·정기모임·대표 이미지·현재 기수는 원본에 없다. 비워 둔다.
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
                recruit_status=enums.RECRUIT_MOJIP if demo else enums.RECRUIT_CLOSED,
                current_gen=1 if demo else None,
            )
        )
    return out


CLUBS = load_clubs()

# (동아리 이름, 며칠 전, 제목, 본문, 태그, 공개)
# ★ 활동 글은 데모용 창작이다. 동아리 정보(이름·분야·창립년도·목적)만 학교 공개 자료다.
POSTS = [
    ("고리사진부", 24, "성북동 출사, 필름 두 롤",
     "10월 12일 성북동 일대에서 출사를 진행했습니다. 12명이 참여했고 각자 준비한 필름 카메라로 "
     "골목과 담장을 담았습니다.\n현상은 다음 주 정기 모임에서 함께 합니다.",
     ["출사", "필름"], True),
    ("고리사진부", 61, "암실 워크숍 — 직접 인화해보기",
     "학교 암실을 빌려 흑백 인화 실습을 했습니다. 처음 해본 부원이 절반이었지만 전원이 한 장씩 완성했습니다.",
     ["워크숍", "암실"], True),
    ("고리사진부", 5, "학기말 전시 준비 회의",
     "전시 공간과 출품작 선정 기준을 정했습니다. 아직 외부 공개 전입니다.",
     ["전시"], False),

    ("축구부", 8, "주말 리그 3차전 승리",
     "3대 1로 이겼습니다. 후반 교체 투입된 신입 2명이 각각 한 골씩 넣었습니다.",
     ["리그", "경기"], True),
    ("축구부", 34, "우천으로 순연된 2차전",
     "비로 경기가 밀려 다음 주 같은 시간에 다시 치릅니다. 훈련은 실내 체육관에서 이어갑니다.",
     ["리그"], True),

    ("노래창고", 18, "가을 정기발표회 <목소리로 짓는 집>",
     "소극장에서 정기발표회를 열었습니다. 6곡을 준비했고 객석 90석이 찼습니다.",
     ["공연", "정기발표회"], True),
    ("노래창고", 55, "신입 오디션 결과 발표",
     "지원 21명 중 6명이 합격했습니다. 파트별로 베이스 2 · 테너 2 · 소프라노 2 입니다.",
     ["모집", "오디션"], True),

    ("희비", 22, "정기공연 <두 번째 문> 무대 철수",
     "3회 공연을 마치고 무대를 정리했습니다. 누적 관객은 210명입니다.",
     ["공연"], True),
    ("희비", 58, "신작 대본 리딩 1회차",
     "다음 정기공연 대본 초고를 함께 읽었습니다. 배역은 다음 주에 정합니다.",
     ["연습"], True),

    ("T.M.I.M", 15, "아동센터 멘토링 8주차",
     "초등 4~6학년 14명과 수학 학습을 진행했습니다. 이번 주로 1학기 일정이 끝났습니다.",
     ["멘토링", "봉사"], True),
    ("T.M.I.M", 47, "연탄 나눔 봉사 300장",
     "지역 복지관과 함께 연탄 300장을 배달했습니다. 11명이 참여했습니다.",
     ["봉사", "나눔"], True),

    ("e-sports", 12, "교내 대회 예선 운영",
     "1학년 32명이 참가했습니다. 종목은 2개, 조별 예선 후 상위 8명이 본선에 올라갑니다.",
     ["대회", "운영"], True),
    ("e-sports", 6, "본선 진출자 확정",
     "예선 이틀 일정을 마치고 본선 진출 8명이 확정됐습니다. 본선은 다음 달에 열립니다.",
     ["대회"], True),
]

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

        # 동아리장은 데모 운영 동아리 6곳에만 배정한다.
        # 나머지 19곳은 leader 가 없다 — 학교가 등록한 목록은 있지만
        # 운영 주체가 아직 이 서비스에 들어오지 않은 상태다 (설계 §3.2)
        leader_of = {}
        for i, name in enumerate(DEMO_LED):
            club = by_name[name]
            leader_of[name] = LEADER_IDS[i % 3]
            db.add(ClubMember(user_id=leader_of[name], club_id=club.id,
                              role=enums.ROLE_LEADER, gen=1))
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
        for club_name, days_ago, title, body, tags, is_public in POSTS:
            club = by_name[club_name]
            posts.append(Post(
                club_id=club.id,
                # flush 직후 club.members 는 아직 안 채워질 수 있다. 위에서 모은 dict 를 쓴다
                author_id=leader_of[club_name],
                title=title,
                body=body,
                photos=[],
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
        print(f"관리자:   {ADMIN_ID}@mjc.ac.kr · 비밀번호는 전부 test1234")
    finally:
        db.close()


if __name__ == "__main__":
    main()
