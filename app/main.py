from fastapi import FastAPI

from app.domains.auth.router import router as auth_router
from app.domains.practice.router import router as practice_router
from app.domains.report.router import router as report_router

app = FastAPI(title="jjo")

app.include_router(auth_router)
app.include_router(practice_router)
app.include_router(report_router)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
