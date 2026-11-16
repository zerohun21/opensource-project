"""1단계 읽기: pypdfium2로 글자·좌표와 페이지 이미지를 얻고, 스캔본은 OpenCV 전처리 후 Tesseract OCR로 읽는다."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pypdfium2 as pdfium
import pypdfium2.raw as pdfium_c

from core.models import BBox, Page, Word


def _page_words(page: pdfium.PdfPage, height: float) -> list[Word]:
    """글자 상자를 공백·줄바꿈 기준으로 Word로 묶는다. y는 왼쪽 위 원점으로 뒤집는다."""
    tp = page.get_textpage()
    words: list[Word] = []
    text: list[str] = []
    boxes: list[BBox] = []

    def flush() -> None:
        if text:
            bbox = boxes[0]
            for b in boxes[1:]:
                bbox = bbox.union(b)
            words.append(Word("".join(text), bbox, tuple(boxes)))
            text.clear()
            boxes.clear()

    try:
        for i in range(tp.count_chars()):
            ch = chr(pdfium_c.FPDFText_GetUnicode(tp, i))
            if not ch.strip() or ch == "\x00":
                flush()
                continue
            left, bottom, right, top = tp.get_charbox(i)
            text.append(ch)
            boxes.append(BBox(left, height - top, right, height - bottom))
        flush()
    finally:
        tp.close()
    return words


def read_pdf(path: Path) -> list[Page]:
    """PDF 각 쪽의 단어·좌표를 읽는다. 글자 레이어가 없는 쪽은 source="ocr", words=[]로 둔다."""
    doc = pdfium.PdfDocument(str(path))
    try:
        pages: list[Page] = []
        for index in range(len(doc)):
            page = doc[index]
            width, height = page.get_size()
            words = _page_words(page, height)
            pages.append(Page(index, width, height, words, "text" if words else "ocr"))
            page.close()
        return pages
    finally:
        doc.close()


def render_page(path: Path, index: int, dpi: int = 300) -> np.ndarray:
    """index 쪽을 OpenCV용 BGR 3채널 uint8 배열로 렌더링한다."""
    doc = pdfium.PdfDocument(str(path))
    try:
        page = doc[index]
        width, height = page.get_size()
        bitmap = page.render(scale=dpi / 72, rev_byteorder=False)  # 기본 BGR(x)
        # pdfium은 크기를 올림하므로 반올림 크기로 잘라 좌표 규칙(x * dpi / 72)과 맞춘다(최대 1px).
        h, w = round(height * dpi / 72), round(width * dpi / 72)
        arr = np.ascontiguousarray(bitmap.to_numpy()[:h, :w, :3])
        bitmap.close()
        page.close()
        return arr
    finally:
        doc.close()
