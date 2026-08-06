"""에러 응답을 docs/api.md §0.1 의 단일 형태로 강제한다.

    {"detail": {"code": "...", "message": "..."}}

라우터에서는 `raise ApiError(409, "ALREADY_MEMBER", "이미 가입된 동아리입니다.")`
처럼 쓴다. `HTTPException(detail="문자열")` 을 직접 쓰지 말 것 — 프론트가 분기하지 못한다.
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class ApiError(HTTPException):
    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(status_code=status_code, detail={"code": code, "message": message})


def unauthorized() -> ApiError:
    return ApiError(401, "UNAUTHORIZED", "로그인이 필요합니다.")


def forbidden(message: str = "권한이 없습니다.") -> ApiError:
    return ApiError(403, "FORBIDDEN", message)


def not_found(message: str = "찾을 수 없습니다.") -> ApiError:
    return ApiError(404, "NOT_FOUND", message)


def todo(task: str) -> ApiError:
    """T0 뼈대의 미구현 자리. 담당자가 구현하면서 지운다."""
    return ApiError(501, "NOT_IMPLEMENTED", f"{task} 미구현입니다.")


def install_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def _http(_: Request, exc: HTTPException):
        detail = exc.detail
        if not isinstance(detail, dict):
            detail = {"code": "ERROR", "message": str(detail)}
        return JSONResponse(status_code=exc.status_code, content={"detail": detail})

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        first = exc.errors()[0] if exc.errors() else {}
        field = ".".join(str(p) for p in first.get("loc", [])[1:]) or "입력값"
        return JSONResponse(
            status_code=400,
            content={"detail": {"code": "INVALID_INPUT", "message": f"{field} 값이 올바르지 않습니다."}},
        )
