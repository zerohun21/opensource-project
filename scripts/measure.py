"""사전 측정: 한글 OCR 전처리 조건별 정확도와 YuNet 얼굴 탐지 수·속도를 재서 마크다운 표로 출력한다.

실행(tesseract 필요 → Docker): python -m scripts.measure
"""

from __future__ import annotations

import difflib
import re
import time
from pathlib import Path

import cv2
import numpy as np
import pypdfium2 as pdfium
import pytesseract

from samples.make_sample import LINES

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = ROOT / "samples" / "sample_fake.pdf"
MODEL = ROOT / "models" / "face_detection_yunet_2023mar.onnx"
FACE_IMG = ROOT / "samples" / "private" / "astronaut.png"
PII = {"이름": "홍길동", "학번": "20261234", "주민번호": "900101-1234567", "전화": "010-1234-5678",
       "이메일": "gildong.hong@example.com"}


def render(dpi: int) -> np.ndarray:
    """샘플 1쪽을 BGR 이미지로."""
    pil = pdfium.PdfDocument(str(SAMPLE))[0].render(scale=dpi / 72).to_pil()
    return cv2.cvtColor(np.array(pil.convert("RGB")), cv2.COLOR_RGB2BGR)


def binarize(bgr: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    return cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]


def rotate(img: np.ndarray, deg: float) -> np.ndarray:
    """중심 기준 반시계 deg도 회전, 빈 곳은 흰색."""
    h, w = img.shape[:2]
    m = cv2.getRotationMatrix2D((w / 2, h / 2), deg, 1.0)
    return cv2.warpAffine(img, m, (w, h), flags=cv2.INTER_LINEAR, borderValue=(255, 255, 255))


def skew_angle(binary: np.ndarray) -> float:
    """잉크 픽셀을 감싸는 최소 회전 사각형으로 기울기(도) 추정. rotate(img, -angle)로 바로 세운다."""
    ys, xs = np.where(binary < 128)
    if len(xs) == 0:
        return 0.0
    (_, _), (w, h), a = cv2.minAreaRect(np.column_stack([xs, ys]).astype(np.float32))
    if w < h:  # 긴 변 기준으로 맞춘다
        a -= 90
    if a < -45:
        a += 90
    return -a  # 이미지 y가 아래로 커서 부호 반전


def deskew(binary: np.ndarray) -> tuple[np.ndarray, float]:
    angle = skew_angle(binary)
    return rotate(binary, -angle), angle


def norm(s: str) -> str:
    return re.sub(r"\s+", "", s)


def ocr_row(name: str, img: np.ndarray, psm: int) -> str:
    t = time.perf_counter()
    text = pytesseract.image_to_string(img, lang="kor+eng", config=f"--psm {psm}")
    sec = time.perf_counter() - t
    truth = norm("\n".join(LINES))
    acc = difflib.SequenceMatcher(None, truth, norm(text)).ratio() * 100
    marks = " | ".join("O" if norm(v) in norm(text) else "X" for v in PII.values())
    return f"| {name} | {psm} | {acc:.1f}% | {marks} | {sec:.1f}s |"


def measure_ocr() -> list[str]:
    rows = ["| 조건 | psm | 글자 정확도 | " + " | ".join(PII) + " | 시간 |", "|---" * (len(PII) + 4) + "|"]
    img300 = render(300)
    c, ang300 = deskew(binarize(rotate(img300, 3)))
    d, ang150 = deskew(binarize(rotate(render(150), 3)))
    cases = {"(a) 원본 300dpi": img300, "(b) 그레이+Otsu": binarize(img300),
             f"(c) 3° 회전→보정(추정 {ang300:.2f}°)": c, f"(d) (c)를 150dpi(추정 {ang150:.2f}°)": d}
    for psm in (3, 4):  # 3=Tesseract 기본(자동 구획), 4=단일 열
        rows += [ocr_row(name, img, psm) for name, img in cases.items()]
    return rows


def faces(img: np.ndarray, runs: int = 20) -> tuple[int, float]:
    """탐지 수와 평균 ms."""
    h, w = img.shape[:2]
    det = cv2.FaceDetectorYN.create(str(MODEL), "", (w, h))
    t = time.perf_counter()
    for _ in range(runs):
        _, found = det.detect(img)
    ms = (time.perf_counter() - t) / runs * 1000
    return (0 if found is None else len(found)), ms


def measure_faces() -> list[str]:
    rows = ["| 이미지 | 크기(px) | 탐지 수 | 평균 시간 |", "|---|---|---|---|"]
    if not FACE_IMG.exists():
        return rows + ["| 정면·측면·작은 얼굴 | - | 미측정 | 미측정 |"]
    face = cv2.imread(str(FACE_IMG))
    small = np.full((1024, 1024, 3), 255, np.uint8)
    small[400:496, 400:496] = cv2.resize(face, (96, 96))  # 얼굴 폭 약 20px
    page = np.full((3508, 2480, 3), 255, np.uint8)  # A4 300dpi 페이지 속 증명사진
    page[300:812, 1700:2212] = face
    cases = {"정면(원본)": face, "작은 얼굴(~20px)": small, "A4 300dpi 페이지 속 사진": page}
    for name, img in cases.items():
        n, ms = faces(img)
        rows.append(f"| {name} | {img.shape[1]}×{img.shape[0]} | {n} | {ms:.0f}ms |")
    rows.append("| 측면 | - | 미측정(공개 라이선스 측면 사진 미확보) | - |")
    return rows


if __name__ == "__main__":
    print("\n".join(["## OCR", *measure_ocr(), "", "## YuNet", *measure_faces()]))
