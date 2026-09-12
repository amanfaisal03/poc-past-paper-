from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routes import router


app = FastAPI(title="Past Paper POC", version="0.1.0")
app.include_router(router)
app.mount("/", StaticFiles(directory="app/static", html=True), name="frontend")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
