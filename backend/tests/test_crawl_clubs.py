"""크롤러 파싱 — 네트워크를 타지 않는다. 학교 페이지 구조만 고정한다."""

import pytest

from crawl_clubs import parse_clubs

# 실제 페이지 구조를 줄인 것. 분야 칸이 rowspan 으로 묶이고 '(N개)' 가 붙는다.
SAMPLE = (
    '<table class="tbl_type01">\n'
    "  <caption>동아리 종류 정보표</caption>\n"
    "  <thead><tr><th>분야</th><th>동아리명</th><th>창립년도</th>"
    "<th>목적</th><th>주요사업</th></tr></thead>\n"
    "  <tbody>\n"
    '    <tr><th rowspan="2">봉사(2개)</th><td>T.M.I.M</td><td>2011</td>'
    "<td>찬양 공연 및 봉사 활동</td><td>각종 행사 공연</td></tr>\n"
    "    <tr><td>C.F.M</td><td>2018</td>"
    "<td>공연을 통한 수화의 보편화</td><td>다양한 봉사, 각종 공연</td></tr>\n"
    '    <tr><th rowspan="1">학술(1개)</th><td>고리사진부</td><td>1979</td>'
    "<td>사진촬영, 작품연구</td><td>작품전시회 개최</td></tr>\n"
    '    <tr><th rowspan="1">종교(1개)</th><td>C.C.C.</td><td>1984</td>'
    "<td>캠퍼스 복음화</td><td>교내전도, 전도훈련</td></tr>\n"
    "  </tbody>\n"
    "</table>\n"
)


def test_parses_every_row():
    assert len(parse_clubs(SAMPLE)) == 4


def test_carries_field_across_rowspan():
    """분야 칸은 rowspan 으로 묶여 있어 다음 행에는 없다. 직전 값을 이어야 한다."""
    rows = parse_clubs(SAMPLE)
    assert rows[0]["source_category"] == "봉사"
    assert rows[1]["source_category"] == "봉사"


def test_strips_count_suffix():
    assert all("(" not in r["source_category"] for r in parse_clubs(SAMPLE))


def test_maps_to_our_categories():
    by_name = {r["name"]: r for r in parse_clubs(SAMPLE)}
    assert by_name["고리사진부"]["category"] == "학술·전공"
    assert by_name["T.M.I.M"]["category"] == "봉사"
    assert by_name["C.C.C."]["category"] == "종교"


def test_year_is_int_and_text_kept():
    row = parse_clubs(SAMPLE)[0]
    assert row["founded_year"] == 2011
    assert row["purpose"] == "찬양 공연 및 봉사 활동"
    assert row["main_activities"] == "각종 행사 공연"


def test_raises_when_table_missing():
    with pytest.raises(RuntimeError, match="표를 찾지 못했습니다"):
        parse_clubs("<html><body><p>개편되었습니다</p></body></html>")


def test_raises_on_unexpected_headers():
    bad = SAMPLE.replace("<th>동아리명</th>", "<th>단체명</th>")
    with pytest.raises(RuntimeError, match="컬럼 구성이 다릅니다"):
        parse_clubs(bad)


def test_raises_when_data_row_precedes_category():
    """분야 th 없이 데이터 행으로 시작하면, 그 행을 조용히 버리지 않고 즉시 올린다."""
    broken = (
        '<table class="tbl_type01">\n'
        "  <thead><tr><th>분야</th><th>동아리명</th><th>창립년도</th>"
        "<th>목적</th><th>주요사업</th></tr></thead>\n"
        "  <tbody>\n"
        "    <tr><td>T.M.I.M</td><td>2011</td>"
        "<td>찬양 공연 및 봉사 활동</td><td>각종 행사 공연</td></tr>\n"
        '    <tr><th rowspan="1">학술(1개)</th><td>고리사진부</td><td>1979</td>'
        "<td>사진촬영, 작품연구</td><td>작품전시회 개최</td></tr>\n"
        "  </tbody>\n"
        "</table>\n"
    )
    with pytest.raises(RuntimeError, match="분야 칸을 만나기 전에 데이터 행이 나왔습니다"):
        parse_clubs(broken)


def test_raises_on_unknown_category():
    unknown = SAMPLE.replace("학술(1개)", "환경(1개)")
    with pytest.raises(RuntimeError, match="매핑에 없는 분야입니다"):
        parse_clubs(unknown)


def test_raises_on_non_numeric_founded_year_with_club_name():
    bad_year = SAMPLE.replace(
        "<td>고리사진부</td><td>1979</td>", "<td>고리사진부</td><td>미상</td>"
    )
    with pytest.raises(RuntimeError, match="고리사진부"):
        parse_clubs(bad_year)
