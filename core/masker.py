"""4단계 가리기: 페이지를 이미지화해 OpenCV로 칠하고, 가리지 않은 글자만 ReportLab 투명 글자로 복원한 뒤 Pillow·pypdf로 새 PDF를 조립한다."""

from __future__ import annotations

import io
from pathlib import Path

import cv2
import numpy as np
import pypdfium2 as pdfium
from PIL import Image
from pypdf import PdfReader, PdfWriter
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen import canvas

from core.models import BBox, Candidate, Page, Word

FONT = "HYSMyeongJo-Medium"  # ReportLab 내장 한글 CID 폰트(파일 불필요)
PAD = 1.0  # target 상자 여유(포인트)
JPEG_QUALITY = 85


def _pad(b: BBox) -> BBox:
    return BBox(b.x0 - PAD, b.y0 - PAD, b.x1 + PAD, b.y1 + PAD)


def _render(doc: pdfium.PdfDocument, index: int, dpi: int) -> np.ndarray:
    # ponytail: 임시 렌더러. 병합 때 reader.render_page로 교체
    return np.array(doc[index].render(scale=dpi / 72).to_pil().convert("RGB"))


def _paint(img: np.ndarray, boxes: list[BBox], dpi: int) -> np.ndarray:
    s = dpi / 72
    for b in boxes:
        p0 = (int(np.floor(b.x0 * s)), int(np.floor(b.y0 * s)))
        p1 = (int(np.ceil(b.x1 * s)), int(np.ceil(b.y1 * s)))
        cv2.rectangle(img, p0, p1, (0, 0, 0), -1)
    return img


def _kept_runs(w: Word, boxes: list[BBox]) -> list[tuple[str, BBox]]:
    """단어에서 어떤 상자와도 겹치지 않는 연속 글자 묶음. 한 묶음으로 써야 추출 시 글자 사이 공백이 안 생긴다."""
    runs: list[tuple[str, BBox]] = []
    text, box = "", None
    for ch, cb in zip(w.text, w.chars):
        if ch.isspace() or any(cb.intersects(b) for b in boxes):  # 조금이라도 걸치면 버린다
            if text:
                runs.append((text, box))
            text, box = "", None
            continue
        text, box = text + ch, cb if box is None else box.union(cb)
    if text:
        runs.append((text, box))
    return runs


def _draw_page(c: canvas.Canvas, page: Page, img: np.ndarray, boxes: list[BBox]) -> None:
    c.setPageSize((page.width, page.height))
    buf = io.BytesIO()
    Image.fromarray(img).save(buf, "JPEG", quality=JPEG_QUALITY)
    buf.seek(0)
    c.drawImage(ImageReader(buf), 0, 0, page.width, page.height)

    t = c.beginText()
    t.setTextRenderMode(3)  # 투명: 보이지 않지만 검색·선택 가능
    for w in page.words:
        for run, rb in _kept_runs(w, boxes):
            size = max(rb.y1 - rb.y0, 1.0)
            width = pdfmetrics.stringWidth(run, FONT, size)
            t.setFont(FONT, size)
            t.setHorizScale(100 * (rb.x1 - rb.x0) / width if width else 100)
            t.setTextOrigin(rb.x0, page.height - rb.y1)  # 왼쪽 아래 원점으로 변환
            t.textOut(run)
    c.drawText(t)
    c.showPage()


def mask_pdf(src: Path, pages: list[Page], targets: list[Candidate], dst: Path, dpi: int = 200) -> Path:
    """src를 이미지화·칠해 dst에 쓴다. 원본 글자 레이어·주석·첨부·메타데이터는 옮기지 않는다."""
    if FONT not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(UnicodeCIDFont(FONT))

    tmp = io.BytesIO()
    c = canvas.Canvas(tmp, invariant=1)
    doc = pdfium.PdfDocument(str(src))
    try:
        for page in pages:
            boxes = [_pad(t.bbox) for t in targets if t.page == page.index]
            _draw_page(c, page, _paint(_render(doc, page.index, dpi), boxes, dpi), boxes)
    finally:
        doc.close()
    c.save()

    # ReportLab이 만든 새 페이지만 옮겨 담고 Info·XMP는 쓰지 않는다
    writer = PdfWriter()
    for p in PdfReader(tmp).pages:
        writer.add_page(p)
    writer.metadata = None
    with open(dst, "wb") as f:
        writer.write(f)
    return dst
