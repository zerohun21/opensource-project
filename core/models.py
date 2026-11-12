"""파이프라인 전 단계가 공유하는 데이터 구조(페이지, 글자·좌표, 개인정보 후보)를 정의한다.

좌표 규칙 (모든 단계 공통):
- 단위는 PDF 포인트(1/72인치), 원점은 페이지 **왼쪽 위**, y는 아래로 증가한다.
- 이미지 픽셀로 바꿀 땐 `x * dpi / 72` 만 곱하면 된다.
- pypdfium2·ReportLab(원점 왼쪽 아래)과 주고받을 때는 각 모듈이 `y' = page.height - y`로 변환한다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


@dataclass(frozen=True)
class BBox:
    x0: float
    y0: float
    x1: float
    y1: float

    def union(self, other: BBox) -> BBox:
        return BBox(min(self.x0, other.x0), min(self.y0, other.y0), max(self.x1, other.x1), max(self.y1, other.y1))

    def intersects(self, other: BBox) -> bool:
        return self.x0 < other.x1 and other.x0 < self.x1 and self.y0 < other.y1 and other.y0 < self.y1


@dataclass(frozen=True)
class Word:
    """공백으로 나뉜 글자 묶음. chars는 글자 하나하나의 상자(len(chars) == len(text))."""

    text: str
    bbox: BBox
    chars: tuple[BBox, ...]


@dataclass
class Page:
    index: int  # 0부터
    width: float  # 포인트
    height: float
    words: list[Word] = field(default_factory=list)
    source: str = "text"  # "text"(글자 레이어) | "ocr"(스캔본)

    @property
    def text(self) -> str:
        """탐지기가 검색할 페이지 문자열. 단어 사이는 공백 하나."""
        return " ".join(w.text for w in self.words)

    def bbox_of(self, start: int, end: int) -> BBox | None:
        """page.text[start:end] 범위 글자들을 감싸는 상자. 공백만 있으면 None."""
        box: BBox | None = None
        pos = 0
        for w in self.words:
            for i, cb in enumerate(w.chars):
                if start <= pos + i < end:
                    box = cb if box is None else box.union(cb)
            pos += len(w.text) + 1
        return box


class Kind(StrEnum):
    NAME = "name"
    STUDENT_ID = "student_id"
    RRN = "rrn"  # 주민등록번호
    PHONE = "phone"
    EMAIL = "email"
    FACE = "face"
    MANUAL = "manual"  # 사용자가 3단계에서 직접 그린 상자


@dataclass(frozen=True)
class Candidate:
    """개인정보 후보. 원문 글자는 담지 않는다(로그 유출 방지) — 위치와 종류만."""

    page: int
    kind: Kind
    bbox: BBox
    score: float = 1.0
    source: str = ""  # 예: "regex", "label", "kiwi", "yunet"
