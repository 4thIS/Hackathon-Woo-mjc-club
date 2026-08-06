"""활동 결과보고서 PDF → 텍스트.

게이트웨이에 파일 업로드 엔드포인트가 없으므로 **우리 서버가 먼저 글자를 뽑는다**
(기획서 §7.1). 스캔본은 글자가 안 나온다 — 그건 실패가 아니라 예상된 경우다.
"""

import io

from pypdf import PdfReader

MIN_CHARS = 30  # 이보다 적으면 스캔본으로 본다


def extract(data: bytes, max_chars: int = 6000) -> str | None:
    """읽어낸 텍스트. 스캔본 등으로 못 읽으면 None (→ 422 PDF_UNREADABLE)."""
    try:
        reader = PdfReader(io.BytesIO(data))
        text = "\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception:  # noqa: BLE001 — 깨진 PDF도 그냥 못 읽은 것으로 처리
        return None

    text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    if len(text) < MIN_CHARS:
        return None
    return text[:max_chars]
