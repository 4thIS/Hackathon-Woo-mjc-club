"""에러 응답을 docs/api.md §0.1 의 단일 형태로 강제한다.

    {"detail": {"code": "...", "message": "..."}}

라우터에서는 `raise ApiError(409, "ALREADY_MEMBER", "이미 가입된 동아리입니다.")`
처럼 쓴다. `HTTPException(detail="문자열")` 을 직접 쓰지 말 것 — 프론트가 분기하지 못한다.
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class ApiError(HTTPException):
    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(status_code=status_code, detail={"code": code, "message": message})


def unauthorized() -> ApiError:
    return ApiError(401, "UNAUTHORIZED", "로그인이 필요합니다.")


def forbidden(message: str = "권한이 없습니다.") -> ApiError:
    return ApiError(403, "FORBIDDEN", message)


def not_found(message: str = "찾을 수 없습니다.") -> ApiError:
    return ApiError(404, "NOT_FOUND", message)


#  프레임워크가 detail 을 문자열로 올릴 때 붙일 code (api.md §0.1)
_CODES = {
    400: "INVALID_INPUT",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
}


def todo(task: str) -> ApiError:
    """아직 구현하지 않은 자리. 구현하면서 지운다."""
    return ApiError(501, "NOT_IMPLEMENTED", f"{task} 미구현입니다.")


def install_handlers(app: FastAPI) -> None:
    # ★ Starlette 쪽 HTTPException 에 걸어야 한다. FastAPI 의 HTTPException 은 이 클래스의
    #   자식이라 함께 잡히지만, 반대로 걸면 라우팅 404·405 와 본문 파싱 실패(전부 Starlette 가
    #   부모 클래스로 raise 한다)가 새어나가 {"detail": "문자열"} 로 응답된다 — §0.1 위반.
    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: HTTPException):
        detail = exc.detail
        if not isinstance(detail, dict):
            # 프레임워크가 문자열로 올린 것들(404 Not Found, 405 Method Not Allowed,
            # 본문 파싱 실패). 프론트가 분기할 수 있도록 상태코드에 맞는 code 를 붙인다.
            detail = {"code": _CODES.get(exc.status_code, "ERROR"), "message": str(detail)}
        return JSONResponse(status_code=exc.status_code, content={"detail": detail})

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        first = exc.errors()[0] if exc.errors() else {}
        field = ".".join(str(p) for p in first.get("loc", [])[1:]) or "입력값"
        return JSONResponse(
            status_code=400,
            content={"detail": {"code": "INVALID_INPUT", "message": f"{field} 값이 올바르지 않습니다."}},
        )
