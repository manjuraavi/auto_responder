from fastapi import APIRouter, Depends, BackgroundTasks
from app.auth.gmail_auth import GmailAuthService
from app.services.gmail_service import GmailService
from app.services.vector_service import VectorService
import json, os
from pydantic import BaseModel


router = APIRouter()
TOGGLE_FILE = "toggle_state.json"
INGESTION_STATUS = {}

class ToggleRequest(BaseModel):
    enabled: bool

def get_toggle_state(user_email):
    if os.path.exists(TOGGLE_FILE):
        with open(TOGGLE_FILE) as f:
            data = json.load(f)
        return data.get(user_email, False)
    return False

def set_toggle_state(user_email, state):
    data = {}
    if os.path.exists(TOGGLE_FILE):
        with open(TOGGLE_FILE) as f:
            data = json.load(f)
    data[user_email] = state
    with open(TOGGLE_FILE, "w") as f:
        json.dump(data, f)

@router.get("/ingest-toggle")
async def get_ingest_toggle(current_user: dict = Depends(GmailAuthService.get_current_user)):
    email = current_user.get("email")
    return {"enabled": get_toggle_state(email)}

@router.post("/ingest-toggle")
async def set_ingest_toggle(
    request: ToggleRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(GmailAuthService.get_current_user)
):
    email = current_user.get("email")
    enabled = request.enabled
    set_toggle_state(email, enabled)

    if enabled:
        if INGESTION_STATUS.get(email) == "in_progress":
            return {"enabled": True, "message": "Ingestion already in progress"}
        INGESTION_STATUS[email] = "in_progress"
        background_tasks.add_task(start_ingestion, email)
    else:
        if INGESTION_STATUS.get(email) == "in_progress":
            return {"enabled": True, "message": "Cannot stop ingestion while in progress"}
        vector_service = VectorService()
        vector_service.delete_emails(user_email=email)
        INGESTION_STATUS[email] = "idle"

@router.get("/ingestion-status")
async def get_ingestion_status(current_user: dict = Depends(GmailAuthService.get_current_user)):
    email = current_user.get("email")
    return {"status": INGESTION_STATUS.get(email, "idle")}

async def start_ingestion(email):
    try:
        gmail_service = GmailService(user_email=email)
        gmail_service.load_all_to_vectordb()
        INGESTION_STATUS[email] = "completed"
    except Exception as e:
        INGESTION_STATUS[email] = "failed"
        raise e