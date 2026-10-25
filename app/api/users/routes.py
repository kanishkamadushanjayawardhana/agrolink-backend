
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user

from app.models.user import User
from app.models.bid import Bid

from app.schemas.user import UserResponse, UserProfileUpdate
from app.schemas.bid import BidResponse


router = APIRouter(
    prefix="/users",
    tags=["Users"]
)


# =========================================================
# GET MY PROFILE
# =========================================================

@router.get("/me", response_model=UserResponse)
def get_my_profile(
    current_user: User = Depends(get_current_user)
):
    return current_user


# =========================================================
# UPDATE MY PROFILE
# =========================================================

@router.patch("/me", response_model=UserResponse)
def update_my_profile(
    profile_data: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    updates = profile_data.model_dump(exclude_unset=True)

    if not updates:
        raise HTTPException(
            status_code=400,
            detail="No profile fields provided"
        )

    if "full_name" in updates:
        if not updates["full_name"] or not updates["full_name"].strip():
            raise HTTPException(
                status_code=422,
                detail="Full name cannot be empty"
            )
        updates["full_name"] = updates["full_name"].strip()

    # Keep farmer and buyer profile fields separate.
    if current_user.role.value == "farmer":
        updates.pop("company_name", None)
    elif current_user.role.value == "buyer":
        updates.pop("farm_name", None)

    # Only fields declared in UserProfileUpdate can be changed.
    for field, value in updates.items():
        setattr(current_user, field, value)

    db.add(current_user)
    db.commit()
    db.refresh(current_user)

    return current_user


# =========================================================
# GET MY BIDS
# =========================================================

@router.get(
    "/me/bids",
    response_model=list[BidResponse]
)
def get_my_bids(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Only buyers can view their bids.
    if current_user.role.value != "buyer":
        raise HTTPException(
            status_code=403,
            detail="Only buyers can view their bids"
        )

    bids = (
        db.query(Bid)
        .filter(Bid.buyer_id == current_user.id)
        .order_by(Bid.created_at.desc())
        .all()
    )

    return bids
