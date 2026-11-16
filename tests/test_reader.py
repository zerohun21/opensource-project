from pathlib import Path

from reportlab.pdfgen import canvas

from core.reader import read_pdf, render_page

SAMPLE = Path(__file__).parent.parent / "samples" / "sample_fake.pdf"


def _span(page_text: str, s: str) -> tuple[int, int]:
    start = page_text.index(s)
    return start, start + len(s)


def test_read_text_and_boxes() -> None:
    page = read_pdf(SAMPLE)[0]
    assert page.source == "text"
    assert "010-1234-5678" in page.text
    assert "900101-1234567" in page.text
    for w in page.words:
        assert len(w.chars) == len(w.text)

    phone = page.bbox_of(*_span(page.text, "010-1234-5678"))
    assert phone is not None
    assert 0 <= phone.x0 < phone.x1 <= page.width
    assert 0 <= phone.y0 < phone.y1 <= page.height

    row1 = page.bbox_of(*_span(page.text, "재학"))
    row2 = page.bbox_of(*_span(page.text, "홍길동"))
    assert row1 is not None and row2 is not None
    assert row1.y0 < row2.y0  # 위쪽 줄일수록 y가 작다


def test_blank_page_is_ocr(tmp_path: Path) -> None:
    pdf = tmp_path / "blank.pdf"
    c = canvas.Canvas(str(pdf))
    c.rect(100, 100, 50, 50, fill=1)
    c.showPage()
    c.save()
    pages = read_pdf(pdf)
    assert len(pages) == 1
    assert pages[0].source == "ocr" and pages[0].words == []


def test_render_page_shape() -> None:
    page = read_pdf(SAMPLE)[0]
    img = render_page(SAMPLE, 0)
    assert img.shape == (round(page.height * 300 / 72), round(page.width * 300 / 72), 3)
    assert img.dtype.name == "uint8"
