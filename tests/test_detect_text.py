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
    cands = detect_text([make_page(["이순신 장군이 확인했습니다."])])  # 문맥 단서 없이 Kiwi만
    assert any(c.kind == Kind.NAME and c.source == "kiwi" for c in cands)


def test_label_does_not_cross_into_next_label() -> None:
    cands = detect_text([make_page(["성명:", "학번: 20261234"])])
    assert [c for c in cands if c.kind == Kind.NAME] == []
    cands = detect_text([make_page(["이름 학번", "홍길동 20261234"])])  # 표 헤더도 이름으로 잡지 않음
    assert all(c.bbox.y0 > 0 for c in cands if c.kind == Kind.NAME)


def names(lines: list[str]) -> list[tuple[str, float]]:
    """이름 후보를 (source, score)로."""
    return [(c.source, c.score) for c in detect_text([make_page(lines)]) if c.kind == Kind.NAME]


def test_name_table_column() -> None:
    page = make_page(["번호 이름 학과", "1 김가상 수학", "2 이테스 경영학"])
    cands = [c for c in detect_text([page]) if c.kind == Kind.NAME]
    assert len(cands) == 2 and all(c.bbox.x0 == 2 * CW for c in cands)  # '이름' 열만
    assert {c.score for c in cands} >= {0.8}


def test_name_after_list_label() -> None:
    assert [s for s, _ in names(["참석: 이테스, 윤모의, 장연습"])].count("list") == 3


def test_name_before_title() -> None:
    got = names(["참가 신청은 김가상 조교에게, 담당 교수 확인 후 홍길순님께 전달"])
    assert sorted(got) == [("title", 0.7), ("title", 0.7)]  # '담당'은 빼고 두 이름만


def test_header_words_not_names() -> None:
    assert names(["학번 성명 연락처 비고 소속 주소"]) == []


def test_kiwi_place_words_dropped() -> None:
    assert names(["장소: 공학관 301호, 우편번호 03187"]) == []


def test_spaced_phone_and_traps() -> None:
    cands = detect_text([make_page(["연락은 010 1234 5678 또는 02 123 4567 로"])])
    assert [c.kind for c in cands].count(Kind.PHONE) == 2
    traps = ["문서번호 2026-0412 주문번호 20261112 우편번호 03187", "고객센터 1588-0000 계좌 110-123-456789",
             "합계 12,345,678원 결제일 2026.11.12 ISBN 979-11-1234-567-8 습득일 2026. 10. 30."]
    # 숫자 함정은 번호 종류로 잡히면 안 된다(이름 오탐은 Kiwi 몫이라 평가에서 따로 센다)
    assert [c for c in detect_text([make_page(traps)]) if c.kind != Kind.NAME] == []


def test_form_label_is_not_table_header() -> None:
    assert names(["이름 박샘플", "휴대폰 01098765432", "신청 금액 1,250,000원"]) == [("label", 0.9)]


def test_noun_with_particle_before_title() -> None:
    assert names(["참가 신청은 조교에게 보내 주세요."]) == []
