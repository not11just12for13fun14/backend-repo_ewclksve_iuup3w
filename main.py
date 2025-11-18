import os
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import List, Optional

app = FastAPI(title="GiftFlow Mock API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------
# Mock Data (temporary)
# ----------------------
# This is intentionally simple to support UI development.
MOCK_USERS = {
    "demo@giftflow.app": {
        "name": "Demo User",
        "email": "demo@giftflow.app",
        "password": "demo123",  # plain text for mock only
        "id": "u_demo_1",
    }
}

MOCK_TOKENS: dict[str, str] = {
    # token -> email
}

MOCK_EVENTS: List[dict] = [
    {
        "id": "evt_1",
        "name": "Holiday Gift Swap",
        "event_type": "Secret Santa",
        "date": "2025-12-15",
        "budget": 40,
        "participants": ["Alice", "Bob", "Charlie"],
        "ownerId": "u_demo_1",
        "status": "draft",
        "allow_wishlists": True,
        "collect_addresses": False,
        "custom_message": "Welcome to our annual swap!",
    }
]

# ----------------------
# Models
# ----------------------
class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class AuthResponse(BaseModel):
    token: str
    name: str
    email: EmailStr
    userId: str

class EventCreate(BaseModel):
    name: str
    date: str
    budget: Optional[float] = None
    participants: List[str] = []
    event_type: Optional[str] = "Secret Santa"
    allow_wishlists: Optional[bool] = True
    collect_addresses: Optional[bool] = False
    custom_message: Optional[str] = None

class Event(BaseModel):
    id: str
    name: str
    date: str
    budget: Optional[float] = None
    participants: List[str] = []
    ownerId: str
    status: str = "draft"
    event_type: Optional[str] = "Secret Santa"
    allow_wishlists: Optional[bool] = True
    collect_addresses: Optional[bool] = False
    custom_message: Optional[str] = None

# ----------------------
# Helpers
# ----------------------

def get_user_from_token(token: str) -> dict:
    email = MOCK_TOKENS.get(token)
    if not email:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = MOCK_USERS.get(email)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

async def current_user(authorization: Optional[str] = Header(default=None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    token = authorization.replace("Bearer ", "")
    return get_user_from_token(token)

# ----------------------
# Base routes
# ----------------------
@app.get("/")
def read_root():
    return {"message": "GiftFlow Mock API running"}

@app.get("/api/hello")
def hello():
    return {"message": "Hello from GiftFlow backend!"}

@app.get("/test")
def test_database():
    """Connectivity check (no DB required for mock)."""
    response = {
        "backend": "✅ Running",
        "database": "⏸️ Mock mode (no DB)",
        "database_url": "❌ Not Set",
        "database_name": "❌ Not Set",
        "connection_status": "Mock",
        "collections": []
    }
    return response

# ----------------------
# Auth (mock)
# ----------------------
@app.post("/api/auth/signup", response_model=AuthResponse)
def signup(payload: SignupRequest):
    if payload.email in MOCK_USERS:
        raise HTTPException(status_code=400, detail="Email already in use")
    user_id = f"u_{len(MOCK_USERS)+1}"
    MOCK_USERS[payload.email] = {
        "name": payload.name,
        "email": payload.email,
        "password": payload.password,
        "id": user_id,
    }
    token = f"mocktoken_{user_id}"
    MOCK_TOKENS[token] = payload.email
    return AuthResponse(token=token, name=payload.name, email=payload.email, userId=user_id)

@app.post("/api/auth/login", response_model=AuthResponse)
def login(payload: LoginRequest):
    user = MOCK_USERS.get(payload.email)
    if not user or user.get("password") != payload.password:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    # issue token (reuse if exists)
    existing_token = None
    for t, e in MOCK_TOKENS.items():
        if e == payload.email:
            existing_token = t
            break
    token = existing_token or f"mocktoken_{user['id']}"
    MOCK_TOKENS[token] = payload.email
    return AuthResponse(token=token, name=user["name"], email=user["email"], userId=user["id"]) 

@app.get("/api/me")
def me(user: dict = Depends(current_user)):
    return {"name": user["name"], "email": user["email"], "userId": user["id"]}

# ----------------------
# Events (mock)
# ----------------------
@app.get("/api/events", response_model=List[Event])
def list_events(user: dict = Depends(current_user)):
    owned = [Event(**e) for e in MOCK_EVENTS if e.get("ownerId") == user["id"]]
    return owned

@app.post("/api/events", response_model=Event)
def create_event(payload: EventCreate, user: dict = Depends(current_user)):
    new_id = f"evt_{len(MOCK_EVENTS)+1}"
    event = Event(
        id=new_id,
        name=payload.name,
        date=payload.date,
        budget=payload.budget,
        participants=payload.participants or [],
        ownerId=user["id"],
        status="draft",
        event_type=payload.event_type or "Secret Santa",
        allow_wishlists=payload.allow_wishlists if payload.allow_wishlists is not None else True,
        collect_addresses=payload.collect_addresses if payload.collect_addresses is not None else False,
        custom_message=payload.custom_message,
    )
    MOCK_EVENTS.append(event.model_dump())
    return event

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
