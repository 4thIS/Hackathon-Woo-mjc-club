"""비밀번호 해시 · 세션 쿠키 서명 · AI 키 암호화.

세션 테이블을 두지 않는다. 서명된 쿠키에 학번만 담는다 — 해커톤 규모에서
세션 저장소를 운영할 이유가 없고, 로그아웃은 쿠키 삭제로 충분하다.
"""

import base64
import hashlib

import bcrypt
from cryptography.fernet import Fernet, InvalidToken
from itsdangerous import BadSignature, URLSafeSerializer

from .config import settings

SESSION_COOKIE = "session"
_serializer = URLSafeSerializer(settings.secret_key, salt="session")


# 비밀번호 규칙 — 가입과 변경이 같은 기준을 쓴다 (한 곳에서 고친다)
PW_MIN = 8
PW_MAX = 72  # bcrypt 는 72바이트를 넘기면 조용히 잘라 버린다. 그 전에 막는다
_SPECIAL = r"""!@#$%^&*()_+-=[]{};':\"|,.<>/?~`"""


def password_problem(raw: str) -> str | None:
    """규칙에 어긋나면 사람이 읽을 이유를, 통과하면 None 을 준다."""
    if len(raw) < PW_MIN:
        return f"비밀번호는 {PW_MIN}자 이상이어야 합니다."
    if len(raw.encode()) > PW_MAX:
        return "비밀번호가 너무 깁니다."
    if not any(c.isalpha() for c in raw):
        return "비밀번호에 영문을 넣어주세요."
    if not any(c.isdigit() for c in raw):
        return "비밀번호에 숫자를 넣어주세요."
    if not any(c in _SPECIAL for c in raw):
        return "비밀번호에 특수문자를 넣어주세요."
    if " " in raw:
        return "비밀번호에 공백은 쓸 수 없습니다."
    return None


def hash_password(raw: str) -> str:
    return bcrypt.hashpw(raw.encode(), bcrypt.gensalt()).decode()


def verify_password(raw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(raw.encode(), hashed.encode())
    except ValueError:
        return False


def sign_session(user_id: str) -> str:
    return _serializer.dumps({"uid": user_id})


def read_session(raw: str | None) -> str | None:
    if not raw:
        return None
    try:
        return _serializer.loads(raw).get("uid")
    except (BadSignature, ValueError):
        return None


def _fernet() -> Fernet:
    digest = hashlib.sha256(settings.secret_key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_ai_key(raw: str) -> str:
    """복호화 가능해야 한다 — 실제로 호출에 쓰는 값이라 해시가 아니다 (기획서 §4.5)."""
    return _fernet().encrypt(raw.encode()).decode()


def decrypt_ai_key(enc: str) -> str | None:
    try:
        return _fernet().decrypt(enc.encode()).decode()
    except InvalidToken:
        return None
