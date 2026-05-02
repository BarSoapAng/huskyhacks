from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import check_url, debug, health

app = FastAPI(
    title="HuskyHacks API",
    description="Backend API for focus-analysis and AI assistant workflows.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_origin_regex=r"chrome-extension://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(check_url.router)
app.include_router(debug.router)
