import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import errors
from .config import settings
from .db import create_all
from .routers import admin, ai, auth, clubs, members, meta, posts

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI):
    create_all()
    os.makedirs(settings.upload_dir, exist_ok=True)
    yield


app = FastAPI(
    title="MJC Club Archive",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,  # 세션 쿠키를 쓰므로 필수
    allow_methods=["*"],
    allow_headers=["*"],
)

errors.install_handlers(app)


@app.get("/api/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok"}


for r in (auth.router, clubs.router, members.router, admin.router, posts.router,
          ai.router, meta.router):
    app.include_router(r, prefix="/api")

# 업로드된 사진은 로컬 저장 원본 그대로 서빙한다 (리사이징·CDN 없음)
app.mount("/uploads", StaticFiles(directory=settings.upload_dir, check_dir=False), name="uploads")
