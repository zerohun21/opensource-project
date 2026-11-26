"""2단계 찾기: 항목 이름·표 열·목록·호칭 문맥과 Kiwi 형태소 분석으로 사람 이름 후보를 찾는다."""

import re

from kiwipiepy import Kiwi

from core.models import BBox, Candidate, Kind, Page

_KIWI = Kiwi()  # 생성 비용이 커서 모듈에서 한 번만
# 이름이 아닌 항목·표 헤더 단어
_LABEL_WORDS = {
    "성명", "이름", "작성자", "담당자", "학번", "주민등록번호", "전화번호", "이메일",
    "연락처", "비고", "학과", "소속", "번호", "주소", "날짜", "일자", "직위", "직급", "학년", "구분", "서명",
}
# 호칭 앞에 자주 오는 이름 아닌 말
_NOT_NAME = _LABEL_WORDS | {"담당", "지도", "전임", "명예", "객원", "겸임", "초빙", "교수", "조교", "선생", "고객", "회원", "학생", "여러분"}
_HANGUL_2_4 = re.compile(r"[가-힣]{2,4}")
_NAME = r"([가-힣]{2,4})(?![가-힣])"
_LABEL = re.compile(r"(?:성명|이름|작성자|담당자)\s*:?\s*([가-힣]{2,4})(?![가-힣:])")
_LIST = re.compile(r"(?:참석자|참석|작성|담당)\s*:\s*([가-힣]{2,4}(?:\s*,\s*[가-힣]{2,4})*)(?![가-힣:])")
_TITLE = re.compile(r"(?<![가-힣])([가-힣]{2,4})(?:\s(?:조교|교수|선생|씨)|\s?님)")
_TABLE_HEADERS = {"이름", "성명"}
_PLACE_SUFFIX = ("관", "실", "번호")  # '동'은 홍길동 같은 이름과 겹쳐 뺐다


def _below(header: BBox, b: BBox) -> bool:
    """b가 header와 x 범위가 겹치고 그보다 아래 있는가(표 열)."""
    return header.x0 < b.x1 and b.x0 < header.x1 and b.y0 >= header.y1


def _noun_with_particle(word: str) -> bool:
    """'신청은'처럼 일반 명사 + 은·는·이·가·을·를 인가(호칭 앞 오탐 방지)."""
    toks = _KIWI.tokenize(word)
    return len(toks) == 2 and toks[0].tag == "NNG" and toks[1].tag in ("JX", "JKS", "JKO")


def _is_table_header(page: Page, header: BBox) -> bool:
    """같은 줄에 다른 헤더 단어가 있어야 표로 본다('이름 박샘플' 같은 양식 줄 제외)."""
    return any(w.text.rstrip(":") in _LABEL_WORDS and w.bbox != header and w.bbox.y0 < header.y1 and header.y0 < w.bbox.y1
               for w in page.words)


def _spans(page: Page) -> list[tuple[int, int, float, str]]:
    """문맥 규칙으로 찾은 (시작, 끝, score, source). 우선순위 순."""
    text = page.text
    out = [(*m.span(1), 0.9, "label") for m in _LABEL.finditer(text)]
    for m in _LIST.finditer(text):
        out += [(m.start(1) + n.start(1), m.start(1) + n.end(1), 0.8, "list") for n in re.finditer(_NAME, m.group(1))]
    out += [(*m.span(1), 0.7, "title") for m in _TITLE.finditer(text) if not _noun_with_particle(m.group(1))]
    return [s for s in out if text[s[0]:s[1]] not in _NOT_NAME]


def find(page: Page) -> list[Candidate]:
    found: list[tuple[BBox, float, str]] = []
    for s, e, score, src in _spans(page):
        if box := page.bbox_of(s, e):
            found.append((box, score, src))
    # ponytail: 헤더 아래 전체를 열로 본다. 표 끝 판정은 오탐이 보이면 추가
    headers = [w.bbox for w in page.words if w.text.rstrip(":") in _TABLE_HEADERS and _is_table_header(page, w.bbox)]
    for w in page.words:
        if _HANGUL_2_4.fullmatch(w.text) and w.text not in _NOT_NAME and any(_below(h, w.bbox) for h in headers):
            found.append((w.bbox, 0.8, "table"))
    for t in _KIWI.tokenize(page.text):
        f = t.form
        if t.tag == "NNP" and _HANGUL_2_4.fullmatch(f) and f not in _NOT_NAME and not f.endswith(_PLACE_SUFFIX):
            if box := page.bbox_of(t.start, t.start + t.len):
                found.append((box, 0.4, "kiwi"))
    # 같은 자리는 점수 높은 근거 하나만
    out: list[Candidate] = []
    for box, score, src in sorted(found, key=lambda f: -f[1]):
        if not any(box.intersects(c.bbox) for c in out):
            out.append(Candidate(page.index, Kind.NAME, box, score, src))
    return out
