"""2단계 찾기: 항목 이름(성명 등) 문맥과 Kiwi 형태소 분석으로 사람 이름 후보를 찾는다."""

import re

from kiwipiepy import Kiwi

from core.models import Candidate, Kind, Page

_KIWI = Kiwi()  # 생성 비용이 커서 모듈에서 한 번만
_LABEL = re.compile(r"(?:성명|이름|작성자|담당자)\s*:?\s*([가-힣]{2,4})(?![가-힣])")
_HANGUL_2_4 = re.compile(r"[가-힣]{2,4}")


def find(page: Page) -> list[Candidate]:
    text = page.text
    out: list[Candidate] = []
    taken: list[tuple[int, int]] = []
    for m in _LABEL.finditer(text):
        if box := page.bbox_of(m.start(1), m.end(1)):
            out.append(Candidate(page.index, Kind.NAME, box, 0.9, "label"))
            taken.append(m.span(1))
    for t in _KIWI.tokenize(text):
        s, e = t.start, t.start + t.len
        if t.tag != "NNP" or not _HANGUL_2_4.fullmatch(t.form):
            continue
        if any(s < te and ts < e for ts, te in taken):
            continue
        if box := page.bbox_of(s, e):
            out.append(Candidate(page.index, Kind.NAME, box, 0.4, "kiwi"))
    return out
