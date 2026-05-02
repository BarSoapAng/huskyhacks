from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exception_handlers import http_exception_handler
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.routers import check_url, create_session, health, session_visualization

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


@app.exception_handler(HTTPException)
async def handle_create_session_auth_error(
    request: Request,
    exc: HTTPException,
) -> JSONResponse:
    if (
        request.url.path in {"/api/create-session", "/api/session-visualization"}
        and exc.status_code == status.HTTP_401_UNAUTHORIZED
    ):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "error": "UNAUTHORIZED",
                "message": "No active Supabase session found.",
            },
        )

    return await http_exception_handler(request, exc)


app.include_router(health.router)
app.include_router(check_url.router)
app.include_router(create_session.router)
app.include_router(session_visualization.router)
