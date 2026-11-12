# NOTICE

MaskMyInfo는 아래 오픈소스를 사용한다. (초안 — 의존성 확정 후 `pip-licenses`로 대조)

| # | 이름 | 역할 | 라이선스 |
|---|---|---|---|
| 1 | pypdfium2 | PDF 글자·좌표 추출, 페이지 이미지화 | Apache-2.0 / BSD-3-Clause |
| 2 | pypdf | 결과 PDF 조립 | BSD-3-Clause |
| 3 | ReportLab | 투명 글자 복원, 보고서 PDF 생성 | BSD-3-Clause |
| 4 | Pillow | 이미지 처리·변환 | MIT-CMU (HPND) |
| 5 | Tesseract OCR | 스캔본 글자 인식 엔진 | Apache-2.0 |
| 6 | pytesseract | Tesseract 파이썬 래퍼 | Apache-2.0 |
| 7 | kiwipiepy | 한국어 형태소 분석(이름 탐지) | Apache-2.0 |
| 8 | Noto Sans KR | 한글 투명 글자·보고서 폰트 | SIL OFL-1.1 |
| 9 | opencv-python-headless | 이미지 전처리, 영역 칠하기, 얼굴 탐지 실행 | Apache-2.0 (패키징 스크립트 MIT) |
| 10 | YuNet 모델 | 얼굴 탐지 모델 | MIT |
| 11 | FastAPI | 웹 서버 | MIT |
| 12 | Uvicorn | ASGI 서버 | BSD-3-Clause |
| 13 | pdf.js | 브라우저 PDF 미리보기 | Apache-2.0 |
| 14 | Docker | 실행 환경 | Apache-2.0 |
| 15 | pip-licenses | 의존성 라이선스 점검 | MIT |

## FFmpeg (OpenCV 포함 구성요소)
`opencv-python-headless` 패키지에는 FFmpeg이 포함되어 있으며, FFmpeg은 **LGPL-2.1** 라이선스를 따른다. MaskMyInfo는 FFmpeg을 수정하지 않고 **원본 그대로 동적 링크로 사용**한다.
