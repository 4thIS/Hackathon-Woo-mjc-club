"""공용 테스트 픽스처. T3/T4(th) 테스트에서 쓴다."""

import itertools
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app import enums
from app.db import SessionLocal
from app.main import app
from app.models import Club, ClubMember, User
from app.security import SESSION_COOKIE, hash_password, sign_session

PW = hash_password("test1234")
_uid_seq = itertools.count(1)
_club_seq = itertools.count(1)


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
        uid = f"77{next(_uid_seq):06d}"
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
            name=f"테스트동아리{next(_club_seq)}",
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
