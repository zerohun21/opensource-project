"""2단계 찾기: 정규식으로 주민등록번호·전화번호·이메일 후보를 찾는다."""

import re

from core.models import Candidate, Kind, Page

_RULES: list[tuple[Kind, re.Pattern[str]]] = [
    # 생년월일(YYMMDD) + 뒷자리 첫 글자 1~4, 하이픈 선택
    (Kind.RRN, re.compile(r"(?<!\d)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])-?[1-4]\d{6}(?!\d)")),
    (Kind.PHONE, re.compile(r"(?<!\d)01[016789][-.]?\d{3,4}[-.]?\d{4}(?!\d)")),
    # 지역번호: 02, 031~064
    (Kind.PHONE, re.compile(r"(?<!\d)0(?:2|[3-6][1-5])[-.)]?\d{3,4}[-.]?\d{4}(?!\d)")),
    (Kind.EMAIL, re.compile(r"[\w.+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")),
]


def find(page: Page) -> list[Candidate]:
    text = page.text
    out: list[Candidate] = []
    for kind, rx in _RULES:
        for m in rx.finditer(text):
            if box := page.bbox_of(m.start(), m.end()):
                out.append(Candidate(page.index, kind, box, 1.0, "regex"))
    return out
