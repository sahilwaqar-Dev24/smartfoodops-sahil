from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.user import UserResponse

router = APIRouter(prefix="/riders", tags=["Riders"])


@router.get("/available", response_model=List[UserResponse])
def get_available_riders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "restaurant_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only restaurant admins can view available riders",
        )
    return db.query(User).filter(
        User.role == "rider",
        User.is_active == True,
        User.is_available == True,
    ).all()


@router.patch("/me/availability", response_model=UserResponse)
def toggle_my_availability(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "rider":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only riders can toggle their availability",
        )
    current_user.is_available = not current_user.is_available
    db.commit()
    db.refresh(current_user)
    return current_user