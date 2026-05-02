from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/debug", tags=["debug"])

# Store mock response globally
mock_response = None

class MockCheckUrlResponse(BaseModel):
    action: str = "allow"  # allow, soft_alert, hard_block
    procrastinationScore: int | None = None
    reason: str | None = None
    confidence: float | None = None
    source: str = "debug_mock"

@router.post("/set-mock-action")
def set_mock_action(response: MockCheckUrlResponse):
    """Set the mock action to be returned by check-url endpoint"""
    global mock_response
    mock_response = response.model_dump()
    return {"success": True, "mock_response": mock_response}

@router.get("/get-mock-action")
def get_mock_action():
    """Get the current mock action"""
    global mock_response
    return {"mock_response": mock_response}

@router.post("/reset-mock-action")
def reset_mock_action():
    """Reset mock action to None"""
    global mock_response
    mock_response = None
    return {"success": True, "message": "Mock action reset"}
