"""High School Management System API.

This API now supports simple token-based authentication and role-based access
for core operations.
"""

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from typing import Any, Literal
import hashlib
import os
from pathlib import Path
import secrets

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}

# ---- Authentication and user management ----

Role = Literal["student", "instructor", "coordinator", "admin"]
STAFF_ROLES = {"instructor", "coordinator", "admin"}


class SignupRequest(BaseModel):
    email: str
    password: str = Field(min_length=8)
    role: Role = "student"
    name: str
    department: str
    phone: str
    registration_number: str


class LoginRequest(BaseModel):
    email: str
    password: str


class ProfileUpdateRequest(BaseModel):
    name: str | None = None
    department: str | None = None
    phone: str | None = None
    registration_number: str | None = None


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


def _validate_email(email: str) -> str:
    normalized = email.strip().lower()
    if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
        raise HTTPException(status_code=400, detail="Invalid email format")
    return normalized


def _hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), 150_000
    ).hex()


def _create_user(
    email: str,
    password: str,
    role: Role,
    name: str,
    department: str,
    phone: str,
    registration_number: str,
) -> dict[str, Any]:
    salt = secrets.token_hex(16)
    return {
        "email": email,
        "salt": salt,
        "password_hash": _hash_password(password, salt),
        "role": role,
        "name": name,
        "department": department,
        "phone": phone,
        "registration_number": registration_number,
    }


def _user_response(user: dict[str, Any]) -> dict[str, Any]:
    return {
        "email": user["email"],
        "role": user["role"],
        "name": user["name"],
        "department": user["department"],
        "phone": user["phone"],
        "registration_number": user["registration_number"],
    }


# In-memory users and token sessions.
users: dict[str, dict[str, Any]] = {
    "admin@mergington.edu": _create_user(
        email="admin@mergington.edu",
        password="AdminPass123",
        role="admin",
        name="System Admin",
        department="Administration",
        phone="000-000-0000",
        registration_number="ADM-0001",
    ),
    "coordinator@mergington.edu": _create_user(
        email="coordinator@mergington.edu",
        password="Coordinator123",
        role="coordinator",
        name="Activities Coordinator",
        department="Student Affairs",
        phone="000-000-0001",
        registration_number="COO-0001",
    ),
}

# token -> email
sessions: dict[str, str] = {}


def _seed_legacy_students() -> None:
    """Create student accounts for legacy participant emails to aid migration."""
    existing_emails = {
        participant_email.strip().lower()
        for activity in activities.values()
        for participant_email in activity["participants"]
    }
    for index, email in enumerate(sorted(existing_emails), start=1):
        if email in users:
            continue
        users[email] = _create_user(
            email=email,
            password="StudentPass123",
            role="student",
            name=email.split("@")[0].replace(".", " ").title(),
            department="General",
            phone="",
            registration_number=f"LEGACY-{index:04d}",
        )


_seed_legacy_students()


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    prefix = "Bearer "
    if not authorization.startswith(prefix):
        raise HTTPException(status_code=401, detail="Authorization must use Bearer token")
    token = authorization[len(prefix):].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing bearer token")
    return token


def get_current_user(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    token = _extract_bearer_token(authorization)
    email = sessions.get(token)
    if not email or email not in users:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return users[email]


def require_roles(*allowed_roles: Role):
    def _dependency(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
        if current_user["role"] not in allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient role permissions")
        return current_user

    return _dependency


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.post("/auth/signup")
def signup(payload: SignupRequest):
    email = _validate_email(payload.email)
    if email in users:
        raise HTTPException(status_code=400, detail="User already exists")

    users[email] = _create_user(
        email=email,
        password=payload.password,
        role=payload.role,
        name=payload.name,
        department=payload.department,
        phone=payload.phone,
        registration_number=payload.registration_number,
    )
    return {"message": "Account created", "user": _user_response(users[email])}


@app.post("/auth/login")
def login(payload: LoginRequest):
    email = _validate_email(payload.email)
    user = users.get(email)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    expected_hash = _hash_password(payload.password, user["salt"])
    if expected_hash != user["password_hash"]:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = secrets.token_urlsafe(32)
    sessions[token] = email
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": _user_response(user),
    }


@app.post("/auth/logout")
def logout(authorization: str | None = Header(default=None)):
    token = _extract_bearer_token(authorization)
    if token in sessions:
        sessions.pop(token)
    return {"message": "Logged out"}


@app.get("/auth/me")
def get_profile(current_user: dict[str, Any] = Depends(get_current_user)):
    return _user_response(current_user)


@app.patch("/auth/me")
def update_profile(
    payload: ProfileUpdateRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
):
    update_data = payload.model_dump(exclude_unset=True)
    for field_name, field_value in update_data.items():
        current_user[field_name] = field_value
    return {"message": "Profile updated", "user": _user_response(current_user)}


@app.post("/auth/change-password")
def change_password(
    payload: PasswordChangeRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
):
    if _hash_password(payload.current_password, current_user["salt"]) != current_user["password_hash"]:
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    new_salt = secrets.token_hex(16)
    current_user["salt"] = new_salt
    current_user["password_hash"] = _hash_password(payload.new_password, new_salt)
    return {"message": "Password changed"}


@app.get("/admin/users")
def list_users(
    _: dict[str, Any] = Depends(require_roles("admin")),
):
    return {"users": [_user_response(user) for user in users.values()]}


@app.get("/activities")
def get_activities():
    return activities


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(
    activity_name: str,
    email: str | None = None,
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Sign up the current user (or staff-specified user) for an activity."""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    target_email = _validate_email(email) if email else current_user["email"]
    if target_email != current_user["email"] and current_user["role"] not in STAFF_ROLES:
        raise HTTPException(
            status_code=403,
            detail="Only staff can sign up another user",
        )

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is not already signed up
    if target_email in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    if len(activity["participants"]) >= activity["max_participants"]:
        raise HTTPException(status_code=400, detail="Activity is full")

    # Add student
    activity["participants"].append(target_email)
    return {"message": f"Signed up {target_email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(
    activity_name: str,
    email: str | None = None,
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Unregister the current user (or staff-specified user) from an activity."""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    target_email = _validate_email(email) if email else current_user["email"]
    if target_email != current_user["email"] and current_user["role"] not in STAFF_ROLES:
        raise HTTPException(
            status_code=403,
            detail="Only staff can unregister another user",
        )

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is signed up
    if target_email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    # Remove student
    activity["participants"].remove(target_email)
    return {"message": f"Unregistered {target_email} from {activity_name}"}
