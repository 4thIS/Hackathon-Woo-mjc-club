"""공용 테스트 픽스처. T3/T4(th) · T5(cw) 테스트에서 쓴다.

**테스트는 자기가 만든 것을 치우고 나간다.** 안 그러면 두 가지가 깨진다.

1. 재실행 — 학번·동아리명이 겹쳐 `UniqueViolation` 이 난다. CI 는 매번 새 DB 라
   드러나지 않지만 로컬에서는 두 번째 실행부터 대부분 실패한다.
2. `seed.py` — 유저가 한 명이라도 있으면 "이미 데이터가 있습니다" 로 건너뛴다.
   테스트 찌꺼기가 남아 있으면 데모 데이터가 안 들어간 채로 시연에 들어간다.

그래서 테스트 데이터에 이 실행만의 표식을 붙이고(`_RUN`), 세션 시작·종료에 모두
지운다. 시작에도 지우는 이유는 이전 실행이 중간에 죽었을 수 있기 때문이다.
"""

import itertools
import uuid
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import or_, select

from app import enums
from app.db import SessionLocal, create_all
from app.main import app
from app.models import (
    Club,
    ClubApplication,
    ClubMember,
    EmailToken,
    JoinForm,
    JoinRequest,
    LeaveRequest,
    Like,
    Post,
    User,
)
from app.security import SESSION_COOKIE, hash_password, sign_session

PW = hash_password("test1234")

# 실행마다 다른 대역. itertools.count 만 쓰면 프로세스가 새로 뜰 때 1부터 다시 세어
# 지난 실행이 남긴 행과 겹친다.
_RUN = f"{uuid.uuid4().int % 1000:03d}"
_uid_seq = itertools.count(1)
_club_seq = itertools.count(1)

# 테스트 학번 대역. seed 는 00·24·26 으로 시작하므로 겹치지 않는다.
#   77 = conftest 픽스처 · 98 = test_ai_draft · 99 = test_auth
# 뒤의 둘은 자기 테스트에서 스스로 지우지만, 중간에 죽으면 남는다 — 여기서 함께 쓸어낸다.
USER_PREFIXES = ("77", "98", "99")
CLUB_LIKE = "테스트동아리%"


def new_club_name(label: str = "") -> str:
    """정리 대상으로 표시된 동아리 이름.

    make_club 을 안 거치고 API 로 동아리가 만들어지는 경우(개설 신청 승인 등)에도
    이 이름을 써야 conftest 가 지울 수 있다. 그냥 지으면 clubs.name 이 unique 라
    다음 실행에서 충돌한다.
    """
    return f"테스트동아리{_RUN}-{label or next(_club_seq)}"


def _purge() -> None:
    """테스트가 만든 유저·동아리와 거기 딸린 모든 행을 지운다. FK 순서를 지킨다."""
    with SessionLocal() as db:
        is_test_user = or_(*[User.id.like(f"{p}%") for p in USER_PREFIXES])
        users = select(User.id).where(is_test_user)
        clubs = select(Club.id).where(Club.name.like(CLUB_LIKE))
        posts = select(Post.id).where(or_(Post.club_id.in_(clubs), Post.author_id.in_(users)))

        drop = (
            (Like, or_(Like.user_id.in_(users), Like.post_id.in_(posts))),
            (Post, Post.id.in_(posts)),
            (JoinRequest, or_(JoinRequest.user_id.in_(users), JoinRequest.club_id.in_(clubs))),
            (LeaveRequest, or_(LeaveRequest.user_id.in_(users), LeaveRequest.club_id.in_(clubs))),
            (ClubApplication, ClubApplication.applicant_id.in_(users)),
            (JoinForm, JoinForm.club_id.in_(clubs)),
            (ClubMember, or_(ClubMember.user_id.in_(users), ClubMember.club_id.in_(clubs))),
            (EmailToken, EmailToken.user_id.in_(users)),
            (User, is_test_user),
            (Club, Club.name.like(CLUB_LIKE)),
        )
        for model, cond in drop:
            db.query(model).filter(cond).delete(synchronize_session=False)
        db.commit()


@pytest.fixture(scope="session", autouse=True)
def clean_slate():
    # 빈 DB 면 아직 테이블이 없다. 앱 lifespan 이 하는 일을 먼저 해 둔다.
    create_all()
    _purge()   # 지난 실행이 중간에 죽었을 수 있다
    yield
    _purge()


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def make_user(db):
    def _make(*, verified=True, admin=False, academic_status=enums.ACADEMIC_ENROLLED, name="테스트유저"):
        uid = f"77{_RUN}{next(_uid_seq):05d}"   # 학번 10자리 고정
        user = User(
            id=uid,
            email=f"{uid}@mjc.ac.kr",
            pw_hash=PW,
            name=name,
            dept="테스트학과",
            birth=date(2005, 1, 1),
            gender="남",
            academic_status=academic_status,
            is_admin=admin,
            email_verified=verified,
        )
        db.add(user)
        db.commit()
        return user

    return _make


@pytest.fixture
def make_club(db):
    def _make(**kw):
        defaults = dict(
            # name 은 unique 다 — 실행 표식이 없으면 재실행에서 충돌한다
            name=new_club_name(),
            category=enums.CATEGORIES[0],
            founded_year=2020,
            recruit_status=enums.RECRUIT_MOJIP,
        )
        defaults.update(kw)
        club = Club(**defaults)
        db.add(club)
        db.commit()
        return club

    return _make


@pytest.fixture
def join_club(db):
    def _join(user, club, *, role=enums.ROLE_MEMBER, membership=enums.MEMBERSHIP_ACTIVE, gen=1):
        m = ClubMember(user_id=user.id, club_id=club.id, role=role, membership=membership, gen=gen)
        db.add(m)
        db.commit()
        return m

    return _join


@pytest.fixture
def auth_cookie():
    def _cookie(user):
        return {SESSION_COOKIE: sign_session(user.id)}

    return _cookie
