from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user

from app.models.user import User
from app.models.auction import Auction, AuctionStatus
from app.models.bid import Bid
from app.models.escrow import (
    Escrow,
    EscrowMilestone,
    EscrowStatus,
    MilestoneStatus
)

from app.schemas.escrow import EscrowCreate, EscrowResponse


router = APIRouter(
    prefix="/escrows",
    tags=["Escrows"]
)
# GET ESCROWS VISIBLE TO THE AUTHENTICATED USER
@router.get("/", response_model=list[EscrowResponse])
def get_escrows(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Escrow)

    # Admins may view all escrow records.
    if current_user.role.value == "admin":
        return query.order_by(Escrow.id.desc()).all()

    # Buyers and farmers may only view escrow records they belong to.
    return (
        query.filter(
            (Escrow.buyer_id == current_user.id)
            | (Escrow.farmer_id == current_user.id)
        )
        .order_by(Escrow.id.desc())
        .all()
    )

# =========================================================
# CREATE ESCROW
# =========================================================

@router.post("/", response_model=EscrowResponse)
def create_escrow(
    escrow_data: EscrowCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # -----------------------------------------------------
    # Only buyers can create escrow contracts
    # -----------------------------------------------------

    if current_user.role.value != "buyer":
        raise HTTPException(
            status_code=403,
            detail="Only buyers can create escrow contracts"
        )

    # -----------------------------------------------------
    # Find auction
    # -----------------------------------------------------

    auction = (
        db.query(Auction)
        .filter(Auction.id == escrow_data.auction_id)
        .first()
    )

    if not auction:
        raise HTTPException(
            status_code=404,
            detail="Auction not found"
        )

    # Auction must have ended before escrow creation
    if auction.status != AuctionStatus.ENDED:
        raise HTTPException(
            status_code=400,
            detail="Auction has not ended yet"
        )

    # Find the winning bid
    winning_bid = (
        db.query(Bid)
        .filter(Bid.auction_id == auction.id)
        .order_by(
            Bid.amount.desc(),
            Bid.created_at.asc()
        )
        .first()
    )

    if not winning_bid:
        raise HTTPException(
            status_code=400,
            detail="Cannot create escrow because the auction has no bids"
        )

    # Only the winning buyer can create escrow
    if winning_bid.buyer_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Only the winning buyer can create escrow for this auction"
        )

    # -----------------------------------------------------
    # Check existing escrow
    # -----------------------------------------------------

    existing_escrow = (
        db.query(Escrow)
        .filter(Escrow.auction_id == escrow_data.auction_id)
        .first()
    )

    if existing_escrow:
        raise HTTPException(
            status_code=400,
            detail="Escrow already exists for this auction"
        )

    # -----------------------------------------------------
    # Validate buyer
    # -----------------------------------------------------

    if escrow_data.buyer_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Buyer ID does not match authenticated user"
        )

    # -----------------------------------------------------
    # Validate total amount
    # -----------------------------------------------------

    if escrow_data.total_amount <= 0:
        raise HTTPException(
            status_code=400,
            detail="Total amount must be greater than 0"
        )

    # -----------------------------------------------------
    # Validate milestone amounts
    # -----------------------------------------------------

    milestone_total = sum(
        milestone.amount
        for milestone in escrow_data.milestones
    )

    if abs(milestone_total - escrow_data.total_amount) > 0.01:
        raise HTTPException(
            status_code=400,
            detail="Milestone amounts must equal total escrow amount"
        )

    # -----------------------------------------------------
    # Create escrow
    # -----------------------------------------------------

    escrow = Escrow(
        auction_id=auction.id,
        farmer_id=auction.farmer_id,
        buyer_id=current_user.id,
        total_amount=escrow_data.total_amount,
        released_amount=0.0,
        remaining_amount=escrow_data.total_amount
    )

    db.add(escrow)
    db.flush()

    # -----------------------------------------------------
    # Create milestones
    # -----------------------------------------------------

    for milestone_data in escrow_data.milestones:

        milestone = EscrowMilestone(
            escrow_id=escrow.id,
            name=milestone_data.name,
            description=milestone_data.description,
            amount=milestone_data.amount
        )

        db.add(milestone)

    # -----------------------------------------------------
    # Save
    # -----------------------------------------------------

    db.commit()
    db.refresh(escrow)

    return escrow


# =========================================================
# GET SINGLE ESCROW
# =========================================================

@router.get("/{escrow_id}", response_model=EscrowResponse)
def get_escrow(
    escrow_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # -----------------------------------------------------
    # Find escrow
    # -----------------------------------------------------

    escrow = (
        db.query(Escrow)
        .filter(Escrow.id == escrow_id)
        .first()
    )

    if not escrow:
        raise HTTPException(
            status_code=404,
            detail="Escrow not found"
        )

    # -----------------------------------------------------
    # Access control
    # -----------------------------------------------------

    if (
        current_user.id != escrow.buyer_id
        and current_user.id != escrow.farmer_id
        and current_user.role.value != "admin"
    ):
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to view this escrow"
        )

    # -----------------------------------------------------
    # Return escrow with milestones
    # -----------------------------------------------------

    return escrow


# =========================================================
# FUND ESCROW
# =========================================================

@router.post("/{escrow_id}/fund", response_model=EscrowResponse)
def fund_escrow(
    escrow_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # -----------------------------------------------------
    # Find escrow
    # -----------------------------------------------------

    escrow = (
        db.query(Escrow)
        .filter(Escrow.id == escrow_id)
        .first()
    )

    if not escrow:
        raise HTTPException(
            status_code=404,
            detail="Escrow not found"
        )

    # -----------------------------------------------------
    # Only the buyer can fund the escrow
    # -----------------------------------------------------

    if current_user.id != escrow.buyer_id:
        raise HTTPException(
            status_code=403,
            detail="Only the buyer can fund this escrow"
        )

    # -----------------------------------------------------
    # Escrow must be pending
    # -----------------------------------------------------

    if escrow.status != EscrowStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"Escrow cannot be funded from status: {escrow.status.value}"
        )

    # -----------------------------------------------------
    # Simulated funding
    # -----------------------------------------------------

    escrow.status = EscrowStatus.FUNDED

    db.commit()
    db.refresh(escrow)

    return escrow
# =========================================================
# COMPLETE ESCROW MILESTONE
# =========================================================

@router.post(
    "/{escrow_id}/milestones/{milestone_id}/complete",
    response_model=EscrowResponse
)
def complete_milestone(
    escrow_id: int,
    milestone_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # -----------------------------------------------------
    # Find escrow
    # -----------------------------------------------------

    escrow = (
        db.query(Escrow)
        .filter(Escrow.id == escrow_id)
        .first()
    )

    if not escrow:
        raise HTTPException(
            status_code=404,
            detail="Escrow not found"
        )

    # -----------------------------------------------------
    # Only the farmer can complete the milestone
    # -----------------------------------------------------

    if current_user.id != escrow.farmer_id:
        raise HTTPException(
            status_code=403,
            detail="Only the farmer can complete this milestone"
        )

    # -----------------------------------------------------
    # Escrow must be funded or active
    # -----------------------------------------------------

    if escrow.status not in [
        EscrowStatus.FUNDED,
        EscrowStatus.ACTIVE
    ]:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Milestone cannot be completed "
                f"while escrow status is: {escrow.status.value}"
            )
        )

    # -----------------------------------------------------
    # Find milestone
    # -----------------------------------------------------

    milestone = (
        db.query(EscrowMilestone)
        .filter(
            EscrowMilestone.id == milestone_id,
            EscrowMilestone.escrow_id == escrow_id
        )
        .first()
    )

    if not milestone:
        raise HTTPException(
            status_code=404,
            detail="Milestone not found"
        )

    # -----------------------------------------------------
    # Check if milestone is already completed
    # -----------------------------------------------------

    if milestone.completed:
        raise HTTPException(
            status_code=400,
            detail="Milestone is already completed"
        )

    # -----------------------------------------------------
    # Complete milestone
    # -----------------------------------------------------

    milestone.completed = True

    db.commit()
    db.refresh(escrow)

    return escrow
# =========================================================
# RELEASE ESCROW MILESTONE PAYMENT
# =========================================================

@router.post(
    "/{escrow_id}/milestones/{milestone_id}/release",
    response_model=EscrowResponse
)
def release_milestone_payment(
    escrow_id: int,
    milestone_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # -----------------------------------------------------
    # Find escrow
    # -----------------------------------------------------

    escrow = (
        db.query(Escrow)
        .filter(Escrow.id == escrow_id)
        .first()
    )

    if not escrow:
        raise HTTPException(
            status_code=404,
            detail="Escrow not found"
        )

    # -----------------------------------------------------
    # Only the buyer can release milestone payment
    # -----------------------------------------------------

    if current_user.id != escrow.buyer_id:
        raise HTTPException(
            status_code=403,
            detail="Only the buyer can release this milestone payment"
        )

    # -----------------------------------------------------
    # Escrow must be funded or active
    # -----------------------------------------------------

    if escrow.status not in [
        EscrowStatus.FUNDED,
        EscrowStatus.ACTIVE
    ]:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Payment cannot be released "
                f"while escrow status is: {escrow.status.value}"
            )
        )

    # -----------------------------------------------------
    # Find milestone
    # -----------------------------------------------------

    milestone = (
        db.query(EscrowMilestone)
        .filter(
            EscrowMilestone.id == milestone_id,
            EscrowMilestone.escrow_id == escrow_id
        )
        .first()
    )

    if not milestone:
        raise HTTPException(
            status_code=404,
            detail="Milestone not found"
        )

    # -----------------------------------------------------
    # Milestone must be completed first
    # -----------------------------------------------------

    if not milestone.completed:
        raise HTTPException(
            status_code=400,
            detail="Milestone must be completed before payment release"
        )

    # -----------------------------------------------------
    # Check if payment was already released
    # -----------------------------------------------------

    if milestone.status == MilestoneStatus.RELEASED:
        raise HTTPException(
            status_code=400,
            detail="Milestone payment has already been released"
        )

    # -----------------------------------------------------
    # Release milestone payment
    # -----------------------------------------------------

    milestone.status = MilestoneStatus.RELEASED

    escrow.released_amount += milestone.amount
    escrow.remaining_amount -= milestone.amount

    # -----------------------------------------------------
    # Update escrow status
    # -----------------------------------------------------

    all_milestones = (
        db.query(EscrowMilestone)
        .filter(EscrowMilestone.escrow_id == escrow.id)
        .all()
    )

    all_released = all(
        m.status == MilestoneStatus.RELEASED
        for m in all_milestones
    )

    if all_released:
        escrow.status = EscrowStatus.COMPLETED
    else:
        escrow.status = EscrowStatus.ACTIVE

    # -----------------------------------------------------
    # Save changes
    # -----------------------------------------------------

    db.commit()
    db.refresh(escrow)

    return escrow