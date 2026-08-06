"""★ 계약 파일 — DB 스키마.

컬럼 **추가는 자유**(additive), **삭제·개명은 PM 합의 후**. (CLAUDE.md §계약)
마이그레이션 도구를 쓰지 않는다. 스키마를 바꿨으면 다음을 팀에 공지할 것:

    docker compose down -v && docker compose up -d db && uv run python seed.py

근거: 구현계획 §2 · 기획서 §3~§6
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from . import enums


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class User(Base):
    """학번이 PK다 (기획서 §4.1).

    이메일 도메인이 2종(@mjc.ac.kr / @on.mjc.ac.kr)이지만 학번은 하나이므로,
    학번을 PK로 두면 "같은 학번으로 두 도메인 가입"이 DB 레벨에서 막힌다.
    """

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)  # 학번
    email: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    pw_hash: Mapped[str] = mapped_column(String(120))
    name: Mapped[str] = mapped_column(String(40))
    dept: Mapped[str] = mapped_column(String(60))
    birth: Mapped[date] = mapped_column(Date)
    gender: Mapped[str] = mapped_column(String(4))

    academic_status: Mapped[str] = mapped_column(String(8), default=enums.ACADEMIC_ENROLLED)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    # Fernet 암호문. 평문·해시 둘 다 금지 (기획서 §4.5). 응답에는 마지막 4자리만.
    ai_key_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_key_tail: Mapped[str | None] = mapped_column(String(4), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    memberships: Mapped[list[ClubMember]] = relationship(back_populates="user")

    @property
    def grade(self) -> int:
        """학번 앞 2자리 = 입학년도. 동아리장에게는 학번 대신 이 값만 보인다 (기획서 §5.3)."""
        try:
            entered = 2000 + int(self.id[:2])
        except ValueError:
            return 0
        return max(1, min(4, utcnow().year - entered + 1))


class Club(Base):
    __tablename__ = "clubs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(60), unique=True)
    category: Mapped[str] = mapped_column(String(20), index=True)
    founded_year: Mapped[int] = mapped_column(Integer)
    purpose: Mapped[str] = mapped_column(Text, default="")
    advisor: Mapped[str] = mapped_column(String(40), default="")

    image: Mapped[str | None] = mapped_column(String(200), nullable=True)
    meet_day: Mapped[str | None] = mapped_column(String(20), nullable=True)
    meet_time: Mapped[str | None] = mapped_column(String(20), nullable=True)
    meet_place: Mapped[str | None] = mapped_column(String(60), nullable=True)

    recruit_status: Mapped[str] = mapped_column(String(10), default=enums.RECRUIT_CLOSED, index=True)
    current_gen: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(8), default=enums.CLUB_ACTIVE, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    members: Mapped[list[ClubMember]] = relationship(back_populates="club")
    posts: Mapped[list[Post]] = relationship(back_populates="club")


class ClubMember(Base):
    """사람 × 동아리. 직책·멤버십·기수는 전부 여기 붙는다 (기획서 §3.1)."""

    __tablename__ = "club_members"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    club_id: Mapped[int] = mapped_column(ForeignKey("clubs.id"), primary_key=True)

    role: Mapped[str] = mapped_column(String(10), default=enums.ROLE_MEMBER)
    membership: Mapped[str] = mapped_column(String(8), default=enums.MEMBERSHIP_ACTIVE)
    gen: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 비면 화면에 표시하지 않는다

    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[User] = relationship(back_populates="memberships")
    club: Mapped[Club] = relationship(back_populates="members")


class JoinForm(Base):
    """동아리당 0~1개. fields 예: [{"key","label","type":"text|textarea","required":bool}]"""

    __tablename__ = "join_forms"

    club_id: Mapped[int] = mapped_column(ForeignKey("clubs.id"), primary_key=True)
    fields: Mapped[list] = mapped_column(JSON, default=list)
    required: Mapped[bool] = mapped_column(Boolean, default=False)


class JoinRequest(Base):
    __tablename__ = "join_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    club_id: Mapped[int] = mapped_column(ForeignKey("clubs.id"), index=True)
    status: Mapped[str] = mapped_column(String(8), default=enums.REQ_PENDING, index=True)
    form_answer: Mapped[dict] = mapped_column(JSON, default=dict)
    reject_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[User] = relationship()
    club: Mapped[Club] = relationship()


class LeaveRequest(Base):
    """7일 자동승인. 스케줄러 없이 **조회 시점에** 만료 건을 처리한다 (구현계획 §2)."""

    __tablename__ = "leave_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    club_id: Mapped[int] = mapped_column(ForeignKey("clubs.id"), index=True)
    status: Mapped[str] = mapped_column(String(8), default=enums.REQ_PENDING, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[User] = relationship()
    club: Mapped[Club] = relationship()


class ClubApplication(Base):
    """개설 신청. 신규 창설과 기존 동아리 등록을 하나로 처리한다 (기획서 §5.2)."""

    __tablename__ = "club_applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    applicant_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(60))
    category: Mapped[str] = mapped_column(String(20))
    founded_year: Mapped[int] = mapped_column(Integer)
    purpose: Mapped[str] = mapped_column(Text, default="")
    advisor: Mapped[str] = mapped_column(String(40), default="")
    status: Mapped[str] = mapped_column(String(8), default=enums.REQ_PENDING, index=True)
    reject_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    applicant: Mapped[User] = relationship()


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    club_id: Mapped[int] = mapped_column(ForeignKey("clubs.id"), index=True)
    # 작성자가 탈퇴해도 활동 기록은 동아리에 남는다 — 개인 소유가 아니다.
    # 탈퇴 시 여기만 비우고 화면에는 '탈퇴한 회원' 으로 표시한다 (api.md §2 DELETE /me).
    author_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text, default="")  # 평문. 마크다운 아님 (api.md §9-3)
    photos: Mapped[list] = mapped_column(JSON, default=list)
    activity_date: Mapped[date] = mapped_column(Date, index=True)
    tags: Mapped[list] = mapped_column(JSON, default=list)

    # 기본 비공개. 사진에 학생 얼굴이 들어가기 때문이다 (기획서 §6.1)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    club: Mapped[Club] = relationship(back_populates="posts")
    author: Mapped[User] = relationship()
    likes: Mapped[list[Like]] = relationship(back_populates="post")


class Like(Base):
    __tablename__ = "likes"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id"), primary_key=True)

    post: Mapped[Post] = relationship(back_populates="likes")


class EmailToken(Base):
    __tablename__ = "email_tokens"
    __table_args__ = (UniqueConstraint("token"),)

    token: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship()
