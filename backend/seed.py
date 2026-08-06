"""데모 데이터 주입.

    uv run python seed.py          # 비어 있을 때만 넣는다
    uv run python seed.py --reset  # 전부 지우고 다시 넣는다

**시연 중 빈 화면이 나오면 안 된다** (구현계획 T7). 동아리·활동 글·좋아요까지
채워 두고, 데모 계정 비밀번호는 전부 `test1234` 다.
"""

import sys
from datetime import date, timedelta

# Windows 콘솔은 기본이 cp949 라 '—' 같은 글자에서 UnicodeEncodeError 로 죽는다.
# 주입은 이미 끝난 뒤 마지막 print 에서 터져서 실패한 것처럼 보인다.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from sqlalchemy import select

from app import enums
from app.db import SessionLocal, create_all, engine
from app.models import Base, Club, ClubMember, Like, Post, User
from app.security import hash_password

PW = hash_password("test1234")


def u(sid: str, name: str, dept: str, *, admin: bool = False, status: str = enums.ACADEMIC_ENROLLED) -> User:
    return User(
        id=sid,
        email=f"{sid}@mjc.ac.kr",
        pw_hash=PW,
        name=name,
        dept=dept,
        birth=date(2000 + int(sid[:2]) - 19, 3, 11),
        gender="남",
        academic_status=status,
        is_admin=admin,
        email_verified=True,
    )


USERS = [
    u("00000000", "관리자", "학생지원팀", admin=True),
    u("24010001", "이우진", "시각디자인과"),
    u("24010002", "김태희", "실용음악과"),
    u("24010003", "박찬우", "컴퓨터공학과"),
    u("26011234", "신입생", "컴퓨터공학과"),
    u("26011235", "김서연", "간호학과"),
    u("19010001", "졸업생", "컴퓨터공학과", status=enums.ACADEMIC_GRADUATED),
]

CLUBS = [
    dict(name="필름사진동아리 그늘", category="취미·교양", founded_year=2014, advisor="김지훈",
         purpose="필름 카메라로 학교와 동네를 기록합니다.\n매달 한 번 출사를 나가고, 학기말에 전시를 엽니다.",
         meet_day="수요일", meet_time="18:00", meet_place="학생회관 302",
         recruit_status=enums.RECRUIT_MOJIP, current_gen=12),
    dict(name="알고리즘연구회 AlgoMJC", category="학술·전공", founded_year=2018, advisor="정민석",
         purpose="매주 문제를 풀고 풀이를 공유합니다. 교내 프로그래밍 대회를 운영합니다.",
         meet_day="화요일", meet_time="19:00", meet_place="공학관 401",
         recruit_status=enums.RECRUIT_MOJIP, current_gen=8),
    dict(name="아카펠라 소리결", category="공연·예술", founded_year=2011, advisor="한유진",
         purpose="반주 없이 목소리만으로 무대를 만듭니다. 매 학기 정기공연이 있습니다.",
         meet_day="목요일", meet_time="18:30", meet_place="예술관 소극장",
         recruit_status=enums.RECRUIT_CLOSED, current_gen=15),
    dict(name="축구부 MJC FC", category="체육", founded_year=2005, advisor="오세준",
         purpose="주말 리그에 참가합니다. 초보도 받습니다.",
         meet_day="토요일", meet_time="10:00", meet_place="대운동장",
         recruit_status=enums.RECRUIT_ALWAYS, current_gen=21),
    dict(name="봉사동아리 손길", category="봉사", founded_year=2009, advisor="배수정",
         purpose="지역 아동센터에서 학습 멘토링을 합니다.",
         meet_day="금요일", meet_time="16:00", meet_place="학생회관 201",
         recruit_status=enums.RECRUIT_MOJIP, current_gen=17),
    dict(name="보드게임연구회", category="취미·교양", founded_year=2021, advisor="김지훈",
         purpose="매주 보드게임을 하고 룰을 뜯어봅니다.",
         meet_day="월요일", meet_time="17:00", meet_place="학생회관 305",
         recruit_status=enums.RECRUIT_CLOSED, current_gen=5),
    dict(name="로봇공학회 MJBot", category="학술·전공", founded_year=2016, advisor="정민석",
         purpose="자율주행 소형 로봇을 만들고 교외 대회에 나갑니다.",
         meet_day="수요일", meet_time="19:00", meet_place="공학관 지하 1층",
         recruit_status=enums.RECRUIT_MOJIP, current_gen=10),
    dict(name="연극동아리 무대뒤", category="공연·예술", founded_year=2013, advisor="한유진",
         purpose="1년에 두 번 자체 제작 연극을 올립니다.",
         meet_day="화요일", meet_time="18:00", meet_place="예술관 연습실",
         recruit_status=enums.RECRUIT_ALWAYS, current_gen=14),
]

# (동아리 index, 며칠 전, 제목, 본문, 태그, 공개)
POSTS = [
    (0, 24, "성북동 출사, 필름 두 롤",
     "10월 12일 성북동 일대에서 출사를 진행했습니다. 12명이 참여했고 각자 준비한 필름 카메라로 "
     "골목과 담장을 담았습니다.\n현상은 다음 주 정기 모임에서 함께 합니다.",
     ["출사", "필름"], True),
    (0, 61, "암실 워크숍 — 직접 인화해보기",
     "학교 암실을 빌려 흑백 인화 실습을 했습니다. 처음 해본 부원이 절반이었지만 전원이 한 장씩 완성했습니다.",
     ["워크숍", "암실"], True),
    (0, 5, "학기말 전시 준비 회의",
     "전시 공간과 출품작 선정 기준을 정했습니다. 아직 외부 공개 전입니다.",
     ["전시"], False),
    (1, 12, "교내 프로그래밍 대회 예선 운영",
     "1학년 32명이 참가했습니다. 문제는 4문항, 평균 해결 수는 2.1문항이었습니다.\n본선은 다음 달에 열립니다.",
     ["대회", "운영"], True),
    (1, 40, "그래프 스터디 4주차 마무리",
     "최단경로까지 진도를 마쳤습니다. 주차별 풀이 노트는 깃허브에 정리했습니다.",
     ["스터디", "알고리즘"], True),
    (2, 18, "가을 정기공연 <목소리로 짓는 집>",
     "소극장에서 정기공연을 올렸습니다. 6곡을 준비했고 객석 90석이 찼습니다.",
     ["공연", "정기공연"], True),
    (3, 8, "주말 리그 3차전 승리",
     "3대 1로 이겼습니다. 후반 교체 투입된 신입 2명이 각각 한 골씩 넣었습니다.",
     ["리그", "경기"], True),
    (4, 15, "아동센터 멘토링 8주차",
     "초등 4~6학년 14명과 수학 학습을 진행했습니다. 이번 주로 1학기 일정이 끝났습니다.",
     ["멘토링", "봉사"], True),
    (6, 30, "자율주행 로봇 예선 통과",
     "교외 대회 예선에서 트랙 완주에 성공했습니다. 라인 인식 실패가 2회 있어 본선 전까지 보완합니다.",
     ["대회", "로봇"], True),
    (7, 22, "정기공연 <두 번째 문> 무대 철수",
     "3회 공연을 마치고 무대를 정리했습니다. 누적 관객은 210명입니다.",
     ["공연"], True),
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

        # 동아리장 3명이 8개 동아리를 나눠 맡는다
        leaders = ["24010001", "24010002", "24010003"]
        for i, club in enumerate(clubs):
            db.add(ClubMember(user_id=leaders[i % 3], club_id=club.id,
                              role=enums.ROLE_LEADER, gen=1))
            db.add(ClubMember(user_id="26011234", club_id=club.id,
                              role=enums.ROLE_MEMBER, gen=club.current_gen))
            if i % 2 == 0:
                db.add(ClubMember(user_id="26011235", club_id=club.id,
                                  role=enums.ROLE_MEMBER, gen=club.current_gen))
            db.add(ClubMember(user_id="19010001", club_id=club.id, role=enums.ROLE_MEMBER,
                              membership=enums.MEMBERSHIP_OB, gen=max(1, (club.current_gen or 2) - 4)))
        db.flush()

        today = date.today()
        posts = []
        for club_idx, days_ago, title, body, tags, is_public in POSTS:
            club = clubs[club_idx]
            posts.append(Post(
                club_id=club.id,
                author_id=leaders[club_idx % 3],
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
                db.add(Like(user_id="26011234", post_id=p.id))
                if i % 3 == 0:
                    db.add(Like(user_id="26011235", post_id=p.id))

        db.commit()
        print(f"완료 — 유저 {len(USERS)} · 동아리 {len(clubs)} · 활동글 {len(posts)}")
        print("데모 계정: 26011234@mjc.ac.kr / test1234 (학생), 24010001@mjc.ac.kr / test1234 (동아리장)")
        print("관리자:   00000000@mjc.ac.kr / test1234")
    finally:
        db.close()


if __name__ == "__main__":
    main()
