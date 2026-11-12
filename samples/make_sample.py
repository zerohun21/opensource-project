"""가상 인물 샘플 PDF 생성기. 실제 인물 정보 없음. 실행: python samples/make_sample.py"""

from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen import canvas

FONT = "HYSMyeongJo-Medium"  # ReportLab 내장 한글 CID 폰트(파일 불필요)

LINES = [
    "재학 증명 신청서 (문서번호 2026-0412)",
    "성명: 홍길동",
    "학번: 20261234",
    "주민등록번호: 900101-1234567",
    "전화번호: 010-1234-5678",
    "이메일: gildong.hong@example.com",
    "작성자: 김가상",
    "위 사람은 본교에 재학 중임을 증명합니다.",
]


def make(path: Path) -> Path:
    pdfmetrics.registerFont(UnicodeCIDFont(FONT))
    c = canvas.Canvas(str(path), pagesize=A4)
    c.setTitle("가상 문서")
    c.setAuthor("가상 작성자")
    c.setFont(FONT, 14)
    y = A4[1] - 80
    for line in LINES:
        c.drawString(60, y, line)
        y -= 30
    c.save()
    return path


if __name__ == "__main__":
    print(make(Path(__file__).with_name("sample_fake.pdf")))
