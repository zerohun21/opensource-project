"""2단계 찾기: '학번' 항목 문맥·표 열 위치로 학번 후보를 찾는다(숫자만으로는 찾지 않는다)."""

import re

from core.models import Candidate, Kind, Page

_LABEL = re.compile(r"학번\s*:?\s*(\d{8,10})(?!\d)")
_DIGITS = re.compile(r"\d{8,10}")


def find(page: Page) -> list[Candidate]:
    out: list[Candidate] = []
    for m in _LABEL.finditer(page.text):
        if box := page.bbox_of(m.start(1), m.end(1)):
            out.append(Candidate(page.index, Kind.STUDENT_ID, box, 0.9, "label"))
    # 표: '학번' 헤더와 x 범위가 겹치고 그보다 아래 있는 숫자 단어
    headers = [w.bbox for w in page.words if w.text.rstrip(":") == "학번"]
    for w in page.words:
        b = w.bbox
        if _DIGITS.fullmatch(w.text) and any(h.x0 < b.x1 and b.x0 < h.x1 and b.y0 >= h.y1 for h in headers):
            out.append(Candidate(page.index, Kind.STUDENT_ID, b, 0.9, "table"))
    return list(dict.fromkeys(out))
