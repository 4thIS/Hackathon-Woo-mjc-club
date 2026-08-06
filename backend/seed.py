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
    # 어느 동아리에도 속하지 않은 지원자들 — 시연에서 '신청자 목록 → 승인' 을 보여주려면
    # 심사중인 신청이 미리 쌓여 있어야 한다 (시연 시나리오 1:30)
    u("26011240", "김도윤", "전기공학과"),
    u("26011241", "이서준", "경영학과"),
    u("26011242", "최유진", "간호학과"),
]

APPLICANTS = ["26011240", "26011241", "26011242"]

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
    # --- 아래는 T7 보강분 — 어느 동아리를 눌러도 타임라인이 비지 않게 한다 ---
    (2, 55, "신입 오디션 결과 발표",
     "지원 21명 중 6명이 합격했습니다. 파트별로 베이스 2 · 테너 2 · 소프라노 2 입니다.",
     ["모집", "오디션"], True),
    (3, 34, "우천으로 순연된 2차전",
     "비로 경기가 밀려 다음 주 같은 시간에 다시 치릅니다. 훈련은 실내 체육관에서 이어갑니다.",
     ["리그"], True),
    (4, 47, "연탄 나눔 봉사 300장",
     "지역 복지관과 함께 연탄 300장을 배달했습니다. 11명이 참여했습니다.",
     ["봉사", "나눔"], True),
    (5, 9, "보드게임 나이트 — 40명이 다녀갔습니다",
     "학생회관 305호를 개방해 하루 동안 자유 플레이를 진행했습니다. 준비한 게임은 22종입니다.",
     ["행사", "개방"], True),
    (5, 44, "룰 해설 세미나: 협력형 게임의 구조",
     "협력형 보드게임이 어떻게 난이도를 조절하는지 사례 세 가지로 뜯어봤습니다.",
     ["세미나"], True),
    (6, 6, "본선 진출 확정",
     "예선 통과 후 보완한 라인 인식 코드로 완주 시간을 18초 줄였습니다.",
     ["대회", "로봇"], True),
    (7, 58, "신작 대본 리딩 1회차",
     "다음 정기공연 대본 초고를 함께 읽었습니다. 배역은 다음 주에 정합니다.",
     ["연습"], True),
    (1, 3, "알고리즘 스터디 신규 모집 안내",
     "2학기 스터디를 새로 엽니다. 주 1회 2시간, 초급/중급 두 트랙으로 나눠 진행합니다.",
     ["모집", "스터디"], True),
]

# 가입폼이 있는 동아리 — 신청 모달에 폼이 렌더되는 걸 시연에서 보여준다 (기획서 §5.3)
JOIN_FORM_FIELDS = [
    {"key": "motive", "label": "지원 동기", "type": "textarea", "required": True},
    {"key": "camera", "label": "가지고 있는 카메라가 있나요?", "type": "text", "required": False},
]

# 심사중인 가입 신청 — (지원자 학번, 동아리 index, 폼 답변)
PENDING_JOINS = [
    ("26011240", 0, {"motive": "필름 사진을 배우고 싶어서 지원합니다.", "camera": "없습니다"}),
    ("26011241", 0, {"motive": "동아리 전시를 보고 관심이 생겼습니다.", "camera": "펜탁스 ME"}),
    ("26011242", 1, {}),
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

        # --- 시연용 심사 대기 건 (구현계획 T7 — 빈 화면 금지) -----------------
        db.add(JoinForm(club_id=clubs[0].id, fields=JOIN_FORM_FIELDS, required=True))

        for uid, club_idx, answers in PENDING_JOINS:
            db.add(JoinRequest(user_id=uid, club_id=clubs[club_idx].id, form_answer=answers))

        # 관리자 승인 장면용
        db.add(ClubApplication(
            applicant_id="26011240",
            name="독서토론회 책갈피",
            category="학술·전공",
            founded_year=2026,
            purpose="한 달에 한 권을 정해 읽고 토론합니다. 학기말에 서평집을 냅니다.",
            advisor="정민석",
        ))

        # 동아리장 화면의 탈퇴 요청 목록도 비지 않게 한다
        db.add(LeaveRequest(user_id="26011235", club_id=clubs[2].id))

        db.commit()
        print(f"완료 — 유저 {len(USERS)} · 동아리 {len(clubs)} · 활동글 {len(posts)}")
        print(f"        심사중 가입신청 {len(PENDING_JOINS)} · 개설신청 1 · 탈퇴요청 1 · 가입폼 1")
        print("데모 계정: 26011234@mjc.ac.kr / test1234 (학생), 24010001@mjc.ac.kr / test1234 (동아리장)")
        print("관리자:   00000000@mjc.ac.kr / test1234")
    finally:
        db.close()


if __name__ == "__main__":
    main()
