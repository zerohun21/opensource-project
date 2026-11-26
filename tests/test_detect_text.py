"""글자 기반 탐지(정규식·이름·학번) 테스트. 가상 데이터만 사용."""

from core.detect import detect_text, student_id
from core.models import BBox, Kind, Page, Word

CW, LH = 10.0, 20.0  # 글자 폭, 줄 높이

LINES = [
    "재학 증명 신청서 (문서번호 2026-0412)",
    "성명: 홍길동",
    "학번: 20261234",
    "주민등록번호: 900101-1234567",
    "전화번호: 010-1234-5678",
    "이메일: gildong.hong@example.com",
    "작성자: 김가상",
    "위 사람은 본교에 재학 중임을 증명합니다.",
]


def word(text: str, x: float, y: float) -> Word:
    chars = tuple(BBox(x + i * CW, y, x + (i + 1) * CW, y + LH) for i in range(len(text)))
    return Word(text, BBox(x, y, x + len(text) * CW, y + LH), chars)


def make_page(lines: list[str]) -> Page:
    """줄 목록 → Page. 단어 사이 한 칸, 글자 폭 균등."""
    words: list[Word] = []
    for row, line in enumerate(lines):
        x = 0.0
        for t in line.split():
            words.append(word(t, x, row * LH))
            x += (len(t) + 1) * CW
    return Page(0, 600, 800, words)


def in_line(c_y: float, row: int) -> bool:
    return c_y == row * LH


def test_five_kinds_found_without_labels_in_box() -> None:
    cands = detect_text([make_page(LINES)])
    for kind in (Kind.NAME, Kind.STUDENT_ID, Kind.RRN, Kind.PHONE, Kind.EMAIL):
        assert any(c.kind == kind for c in cands), kind
    # 항목 이름 줄(1~6행)의 후보 상자는 콜론 뒤에서 시작해야 한다
    for row in range(1, 7):
        colon_x = (LINES[row].index(":") + 1) * CW
        for c in (c for c in cands if in_line(c.bbox.y0, row)):
            assert c.bbox.x0 > colon_x, (row, c)
    labeled = {c.bbox.y0 for c in cands if c.kind == Kind.NAME and c.source == "label"}
    assert labeled == {1 * LH, 6 * LH}


def test_document_number_not_detected() -> None:
    cands = detect_text([make_page(LINES)])
    assert not [c for c in cands if in_line(c.bbox.y0, 0) and c.kind in (Kind.STUDENT_ID, Kind.PHONE)]


def test_no_hyphen() -> None:
    cands = detect_text([make_page(["9001011234567 01012345678 0212345678"])])
    assert sorted(c.kind for c in cands) == sorted([Kind.RRN, Kind.PHONE, Kind.PHONE])


def test_student_id_table_column() -> None:
    page = make_page(["이름 학번 문서번호", "홍길동 20261234 2026041200"])
    cands = student_id.find(page)
    assert len(cands) == 1
    assert cands[0].bbox.x0 == 4 * CW  # '학번' 헤더 아래 숫자만


def test_bare_number_not_student_id() -> None:
    assert student_id.find(make_page(["접수 20261234"])) == []


def test_kiwi_name() -> None:
    cands = detect_text([make_page(["담당 교수 이순신 님이 확인했습니다."])])
    assert any(c.kind == Kind.NAME and c.source == "kiwi" for c in cands)


def test_label_does_not_cross_into_next_label() -> None:
    cands = detect_text([make_page(["성명:", "학번: 20261234"])])
    assert [c for c in cands if c.kind == Kind.NAME] == []
    cands = detect_text([make_page(["이름 학번", "홍길동 20261234"])])  # 표 헤더도 이름으로 잡지 않음
    assert all(c.bbox.y0 > 0 for c in cands if c.kind == Kind.NAME)
