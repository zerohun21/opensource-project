"""core/masker.py 테스트: 가린 글자는 결과 PDF에서 사라지고, 나머지는 검색 가능하며, 메타데이터가 없어야 한다."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pypdfium2 as pdfium
import pytest
from pypdf import PdfReader

from core.masker import mask_pdf
from core.models import BBox, Candidate, Kind, Page, Word

SAMPLE = Path(__file__).parent.parent / "samples" / "sample_fake.pdf"


def _pages(path: Path) -> list[Page]:
    """reader가 생기기 전 임시 헬퍼: pypdfium2 글자 상자로 Page를 만든다."""
    doc = pdfium.PdfDocument(str(path))
    out = []
    for i, pg in enumerate(doc):
        w, h = pg.get_size()
        tp = pg.get_textpage()
        words: list[Word] = []
        text, boxes = "", []

        def flush() -> None:
            nonlocal text, boxes
            if text:
                bb = boxes[0]
                for b in boxes[1:]:
                    bb = bb.union(b)
                words.append(Word(text, bb, tuple(boxes)))
            text, boxes = "", []

        for k in range(tp.count_chars()):
            ch = tp.get_text_range(k, 1)
            if not ch or ch.isspace():
                flush()
                continue
            l, b, r, t = tp.get_charbox(k)
            text += ch
            boxes.append(BBox(l, h - t, r, h - b))
        flush()
        out.append(Page(i, w, h, words))
    doc.close()
    return out


def _target(page: Page, s: str, kind: Kind) -> Candidate:
    start = page.text.index(s)
    box = page.bbox_of(start, start + len(s))
    assert box is not None
    return Candidate(page.index, kind, box)


def _text(path: Path) -> str:
    doc = pdfium.PdfDocument(str(path))
    try:
        return "".join(pg.get_textpage().get_text_range() for pg in doc)
    finally:
        doc.close()


@pytest.fixture(scope="module")
def masked(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Page, list[Candidate]]:
    page = _pages(SAMPLE)[0]
    targets = [_target(page, "010-1234-5678", Kind.PHONE), _target(page, "900101-1234567", Kind.RRN)]
    # "작" 오른쪽 절반만 덮는 상자: 일부만 걸친 글자도 복원되면 안 된다
    ja = _target(page, "작성자", Kind.MANUAL).bbox
    cw = (ja.x1 - ja.x0) / 3
    targets.append(Candidate(0, Kind.MANUAL, BBox(ja.x0 + cw * 0.6, ja.y0, ja.x0 + cw * 0.9, ja.y1)))
    dst = mask_pdf(SAMPLE, [page], targets, tmp_path_factory.mktemp("m") / "out.pdf")
    return dst, page, targets


def test_targets_removed_from_text(masked: tuple[Path, Page, list[Candidate]]) -> None:
    text = _text(masked[0])
    for s in ("010-1234-5678", "1234567", "900101"):
        assert s not in text


def test_other_text_searchable(masked: tuple[Path, Page, list[Candidate]]) -> None:
    text = _text(masked[0])
    assert "재학" in text and "증명" in text


def test_partially_covered_char_not_restored(masked: tuple[Path, Page, list[Candidate]]) -> None:
    text = _text(masked[0])
    assert "작성자" not in text
    assert "성자" in text


def test_metadata_removed(masked: tuple[Path, Page, list[Candidate]]) -> None:
    meta = PdfReader(masked[0]).metadata
    assert not meta or ("/Author" not in meta and "/Title" not in meta)
    raw = masked[0].read_bytes()
    for enc in ("utf-8", "utf-16-be"):
        assert "가상 작성자".encode(enc) not in raw
    assert b"/Metadata" not in raw and b"/Annots" not in raw and b"/EmbeddedFiles" not in raw


def test_target_pixels_black(masked: tuple[Path, Page, list[Candidate]]) -> None:
    dst, page, targets = masked
    dpi = 100
    doc = pdfium.PdfDocument(str(dst))
    img = np.array(doc[0].render(scale=dpi / 72).to_pil().convert("L"))
    doc.close()
    s = dpi / 72
    for t in targets[:2]:
        b = t.bbox
        region = img[int(b.y0 * s) + 1 : int(b.y1 * s) - 1, int(b.x0 * s) + 1 : int(b.x1 * s) - 1]
        assert region.size and region.max() < 40
