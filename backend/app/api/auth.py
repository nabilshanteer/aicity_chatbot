from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User

router = APIRouter(prefix="/api/auth", tags=["auth"])


class SyncUserRequest(BaseModel):
    email: str
    name: str | None = None
    google_id: str | None = None


@router.post("/sync")
def sync_user(payload: SyncUserRequest, db: Session = Depends(get_db)):
    """
    Called by the frontend after a successful Google login.
    Creates the user if they don't exist, otherwise returns the existing record.
    """
    user = db.query(User).filter(User.email == payload.email).first()

    if not user:
        user = User(
            email=payload.email,
            name=payload.name,
            google_id=payload.google_id,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role,
    }
