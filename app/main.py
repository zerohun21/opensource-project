"""FastAPI 서버 진입점. 업로드·검토 화면(3단계 사용자 확인)과 처리 API를 제공한다."""

from fastapi import FastAPI

app = FastAPI(title="MaskMyInfo")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
