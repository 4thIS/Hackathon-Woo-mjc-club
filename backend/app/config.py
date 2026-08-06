from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # 저장소 루트 `.env` 하나만 채우면 개발·도커 양쪽에서 동작한다.
    # 개발 실행은 cwd 가 backend/ 라 `../.env` 가 루트를 가리키고, 도커 안에서는
    # 그 경로가 없어 무시된다. 뒤 파일이 이기므로 backend/.env 가 있으면 그쪽이 우선.
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"), env_file_encoding="utf-8", extra="ignore"
    )

    database_url: str = "postgresql+psycopg://mjc:mjc@localhost:5432/mjcclub"

    # 세션 쿠키 서명 + AI 키 Fernet 암호화에 함께 쓴다. 운영이면 분리할 값.
    secret_key: str = "dev-only-change-me"

    frontend_url: str = "http://localhost:5173"
    cors_origins: str = "http://localhost:5173,http://localhost:4173"

    # 메일에 넣는 인증 링크의 기준 주소. 비어 있으면 frontend_url 을 쓴다.
    # 개발(vite)·도커(nginx) 모두 프론트 오리진에서 /api 를 백엔드로 프록시하므로
    # 보통 비워두면 된다. API 가 다른 호스트에 있을 때만 채운다.
    public_base_url: str = ""

    upload_dir: str = "uploads"

    # SMTP — 비어 있으면 메일을 보내지 않고 콘솔에 링크를 출력한다 (backend/CLAUDE.md 규칙)
    # Gmail 을 쓰려면 smtp.gmail.com:587 + 앱 비밀번호. starttls 는 mailer 가 이미 건다.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    # ⚠️ 비워둘 것. Gmail 은 인증한 계정과 다른 From 을 허용하지 않으므로
    #    비어 있으면 smtp_user 를 발신자로 쓴다 (mailer.sender()).
    smtp_from: str = ""
    smtp_sender_name: str = "MJC Club Archive"

    # 명지전문대학 AI Gateway (기획서 §7.0)
    ai_base_url: str = "https://factchat-cloud.mindlogic.ai/v1/gateway"
    ai_model: str = "claude-sonnet-5"  # 2026-08-06 스모크에서 비전까지 확인된 모델

    # ⚠️ 기본 UA로 호출하면 Cloudflare 가 403(1010)으로 막는다 (backend/CLAUDE.md)
    ai_user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
    )

    # 1이면 게이트웨이를 호출하지 않고 준비된 초안을 반환한다 (구현계획 §6 시연 폴백)
    demo_fallback: int = 0

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
