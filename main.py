from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.phase1.api import router as phase1_router
from src.phase2.api import router as phase2_router
from src.phase3.api import router as phase3_router
from src.phase4.api import router as phase4_router

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(
    title="GROWW App Review Analyser",
    description="Weekly pulse from App Store & Play Store reviews for GROWW",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(phase1_router)
app.include_router(phase2_router)
app.include_router(phase3_router)
app.include_router(phase4_router)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def serve_frontend():
    return FileResponse(str(STATIC_DIR / "index.html"))
