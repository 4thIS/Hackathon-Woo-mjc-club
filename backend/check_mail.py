"""SMTP 설정 점검 — 회원가입 절차 없이 테스트 메일 1통을 보낸다.

    uv run python check_mail.py --to 26011234@mjc.ac.kr

시연 직전에 "메일이 실제로 나가는가"만 따로 확인하기 위한 스크립트다.
비밀번호는 어떤 경우에도 출력하지 않는다.
"""

import argparse
import sys

# Windows 콘솔은 기본이 cp949 라 '—' 같은 글자에서 UnicodeEncodeError 로 죽는다.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from app.config import settings  # noqa: E402
from app.services import mailer  # noqa: E402


def masked(value: str) -> str:
    if not value:
        return "(비어 있음)"
    return f"{'*' * max(len(value) - 4, 0)}{value[-4:]}"


def main() -> int:
    ap = argparse.ArgumentParser(description="SMTP 설정 점검")
    ap.add_argument("--to", required=True, help="테스트 메일을 받을 주소")
    args = ap.parse_args()

    print("─" * 56)
    print(f"  SMTP_HOST      {settings.smtp_host or '(비어 있음)'}")
    print(f"  SMTP_PORT      {settings.smtp_port}")
    print(f"  SMTP_USER      {settings.smtp_user or '(비어 있음)'}")
    print(f"  SMTP_PASSWORD  {masked(settings.smtp_password)}")
    print(f"  발신 주소       {mailer.sender() or '(비어 있음)'}")
    print(f"  인증 링크 기준   {settings.public_base_url or settings.frontend_url}")
    print("─" * 56)

    if not settings.smtp_host:
        print("\nSMTP_HOST 가 비어 있습니다. 루트 .env 를 확인하세요.")
        print("설정 없이도 서버는 돌아갑니다 — 인증 링크가 콘솔에 출력됩니다.\n")
        return 1

    sample = mailer.verification_link("TEST-TOKEN-000")
    ok = mailer.send(
        args.to,
        "[MJC Club Archive] 메일 발송 테스트",
        "이 메일이 보이면 SMTP 설정이 정상입니다.\n\n"
        f"실제 인증 메일에는 아래와 같은 형태의 링크가 담깁니다.\n{sample}\n",
    )

    if ok:
        print(f"\n발송 성공 → {args.to}")
        print("받은편지함(및 스팸함)을 확인하세요.\n")
        return 0

    print("\n발송 실패. 위 로그의 사유를 확인하세요.")
    print("Gmail 이면 2단계 인증 후 발급한 16자리 앱 비밀번호인지,")
    print("SMTP_USER 와 발신 주소가 같은 계정인지 확인하세요.\n")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
