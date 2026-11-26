"""2단계 찾기: 개인정보 6종 후보 탐지 모듈 묶음."""

from core.detect import names, patterns, student_id
from core.models import Candidate, Page


def detect_text(pages: list[Page]) -> list[Candidate]:
    """글자 기반 5종(이름·학번·주민번호·전화·이메일) 후보를 모은다."""
    return [c for p in pages for mod in (patterns, names, student_id) for c in mod.find(p)]
