"""화면이 고르기만 하면 되는 참조 데이터 — 명세: docs/api.md §1"""

from fastapi import APIRouter

from ..depts import dept_names

router = APIRouter(tags=["meta"])


@router.get("/depts")
def list_depts():
    """학과 목록. crawl_depts.py 가 만든 파일이 원본이라 학교 서버를 타지 않는다."""
    return {"items": list(dept_names())}
