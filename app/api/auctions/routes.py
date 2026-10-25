from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user

from app.models.user import User
from app.models.auction import Auction, AuctionStatus
from app.models.bid import Bid
from app.models.product import Product

from app.schemas.bid import BidCreate, BidResponse

from app.routes.auction_websocket import manager


router = APIRouter(
    prefix="/auctions",
    tags=["Auctions"]
)


# =========================================================
# HELPER FUNCTION
# UPDATE AUCTION STATUS AUTOMATICALLY
# =========================================================

def update_auction_status(auction: Auction) -> Auction:
    """
    Automatically update auction status according to
    Sri Lanka local time.
    """

    # Sri Lanka Time = UTC + 05:30
    sri_lanka_timezone = timezone(
        timedelta(hours=5, minutes=30)
    )

    # Get current Sri Lanka time
    # Convert to naive datetime because the database
    # auction start/end values are stored as naive datetime.
    now = datetime.now(
        sri_lanka_timezone
    ).replace(tzinfo=None)

    # Auction has finished
    if now >= auction.end_time:
        auction.status = AuctionStatus.ENDED

    # Auction is currently running
    elif now >= auction.start_time:
        auction.status = AuctionStatus.LIVE

    # Auction has not started yet
    else:
        auction.status = AuctionStatus.UPCOMING

    return auction


# =========================================================
# GET ALL AUCTIONS
# =========================================================

@router.get("/")
def get_auctions(
    db: Session = Depends(get_db)
):
    auctions = (
        db.query(Auction)
        .order_by(Auction.id.desc())
        .all()
    )

    # Update status of every auction
    changed = False

    for auction in auctions:

        old_status = auction.status

        update_auction_status(auction)

        if old_status != auction.status:
            changed = True

    # Save status changes
    if changed:
        db.commit()

    return auctions


# =========================================================
# GET LIVE AUCTIONS
# =========================================================

@router.get("/live")
def get_live_auctions(
    db: Session = Depends(get_db)
):
    """
    Return all auctions that are currently LIVE.

    Auction status is recalculated using
    Sri Lanka local time before returning.
    """

    auctions = (
        db.query(Auction)
        .order_by(Auction.id.desc())
        .all()
    )

    live_auctions = []

    changed = False

    for auction in auctions:

        old_status = auction.status

        update_auction_status(auction)

        if old_status != auction.status:
            changed = True

        if auction.status == AuctionStatus.LIVE:
            live_auctions.append(auction)

    # Save updated statuses
    if changed:
        db.commit()

    return live_auctions


# =========================================================
# GET SINGLE AUCTION
# =========================================================

@router.get("/{auction_id}")
def get_auction(
    auction_id: int,
    db: Session = Depends(get_db)
):
    auction = (
        db.query(Auction)
        .filter(
            Auction.id == auction_id
        )
        .first()
    )

    if not auction:
        raise HTTPException(
            status_code=404,
            detail="Auction not found"
        )

   
# =========================================================
 # Automatically update auction status
    old_status = auction.status

    update_auction_status(auction)

    if old_status != auction.status:

        db.commit()

        db.refresh(auction)

    return auction


# =========================================================
# CREATE AUCTION
@router.post("/")
def create_auction(
    auction_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # -----------------------------------------------------
    # Only farmers can create auctions
    # -----------------------------------------------------

    if current_user.role.value != "farmer":
        raise HTTPException(
            status_code=403,
            detail="Only farmers can create auctions"
        )

    # -----------------------------------------------------
    # Get request data
    # -----------------------------------------------------

    product_id = auction_data.get(
        "product_id"
    )

    starting_price = auction_data.get(
        "starting_price"
    )

    start_time = auction_data.get(
        "start_time"
    )

    end_time = auction_data.get(
        "end_time"
    )

    # -----------------------------------------------------
    # Validate product ID
    # -----------------------------------------------------

    if product_id is None:
        raise HTTPException(
            status_code=400,
            detail="product_id is required"
        )

    # -----------------------------------------------------
    # Verify product exists and belongs to this farmer
    # -----------------------------------------------------

    try:
        product_id = int(product_id)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=400,
            detail="product_id must be a valid integer"
        )

    product = (
        db.query(Product)
        .filter(Product.id == product_id)
        .first()
    )

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    if product.farmer_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You can only create auctions for your own products"
        )

    # -----------------------------------------------------
    # Validate starting price
    # -----------------------------------------------------

    if starting_price is None:
        raise HTTPException(
            status_code=400,
            detail="starting_price is required"
        )

    if starting_price <= 0:
        raise HTTPException(
            status_code=400,
            detail="starting_price must be greater than 0"
        )

    # -----------------------------------------------------
    # Validate start time
    # -----------------------------------------------------

    if start_time is None:
        raise HTTPException(
            status_code=400,
            detail="start_time is required"
        )

    # -----------------------------------------------------
    # Validate end time
    # -----------------------------------------------------

    if end_time is None:
        raise HTTPException(
            status_code=400,
            detail="end_time is required"
        )

    # -----------------------------------------------------
    # Convert datetime strings
    # -----------------------------------------------------

    try:

        parsed_start_time = datetime.fromisoformat(
            start_time
        )

        parsed_end_time = datetime.fromisoformat(
            end_time
        )

    except ValueError:

        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid datetime format. "
                "Use format: YYYY-MM-DDTHH:MM:SS"
            )
        )

    # -----------------------------------------------------
    # Validate time range
    # -----------------------------------------------------

    if parsed_end_time <= parsed_start_time:

        raise HTTPException(
            status_code=400,
            detail="end_time must be after start_time"
        )

    # -----------------------------------------------------
    # Create auction
    # -----------------------------------------------------

    auction = Auction(
        product_id=product_id,
        farmer_id=current_user.id,
        starting_price=starting_price,
        current_price=starting_price,
        start_time=parsed_start_time,
        end_time=parsed_end_time
    )

    # -----------------------------------------------------
    # Set initial status
    # -----------------------------------------------------

    update_auction_status(
        auction
    )

    # -----------------------------------------------------
    # Save auction
    # -----------------------------------------------------

    db.add(auction)

    db.commit()

    db.refresh(auction)

    return auction


# =========================================================
# PLACE BID + WEBSOCKET BROADCAST
# =========================================================

@router.post(
    "/{auction_id}/bids",
    response_model=BidResponse
)
async def place_bid(
    auction_id: int,
    bid_data: BidCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # -----------------------------------------------------
    # Only buyers can place bids
    # -----------------------------------------------------

    if current_user.role.value != "buyer":

        raise HTTPException(
            status_code=403,
            detail="Only buyers can place bids"
        )

    # -----------------------------------------------------
    # Find auction
    # -----------------------------------------------------

    auction = (
        db.query(Auction)
        .filter(
            Auction.id == auction_id
        )
        .first()
    )

    if not auction:

        raise HTTPException(
            status_code=404,
            detail="Auction not found"
        )

    # -----------------------------------------------------
    # Update auction status
    # -----------------------------------------------------

    update_auction_status(
        auction
    )

    # -----------------------------------------------------
    # Check whether auction has started
    # -----------------------------------------------------

    if auction.status == AuctionStatus.UPCOMING:

        db.commit()

        raise HTTPException(
            status_code=400,
            detail="Auction has not started yet"
        )

    # -----------------------------------------------------
    # Check whether auction has ended
    # -----------------------------------------------------

    if auction.status == AuctionStatus.ENDED:

        db.commit()

        raise HTTPException(
            status_code=400,
            detail="Auction has ended"
        )

    # -----------------------------------------------------
    # Only LIVE auctions accept bids
    # -----------------------------------------------------

    if auction.status != AuctionStatus.LIVE:

        db.commit()

        raise HTTPException(
            status_code=400,
            detail="Auction is not currently live"
        )

    # -----------------------------------------------------
    # Validate bid amount
    # -----------------------------------------------------

    if bid_data.amount <= 0:

        raise HTTPException(
            status_code=400,
            detail="Bid amount must be greater than 0"
        )

    # -----------------------------------------------------
    # Bid must be higher than current price
    # -----------------------------------------------------

    if bid_data.amount <= auction.current_price:

        raise HTTPException(
            status_code=400,
            detail=(
                f"Bid must be higher than current price "
                f"({auction.current_price})"
            )
        )

    # -----------------------------------------------------
    # Create new bid
    # -----------------------------------------------------

    bid = Bid(
        auction_id=auction.id,
        buyer_id=current_user.id,
        amount=bid_data.amount
    )

    # -----------------------------------------------------
    # Update current auction price
    # -----------------------------------------------------

    auction.current_price = bid_data.amount

    auction.status = AuctionStatus.LIVE

    # -----------------------------------------------------
    # Save bid and auction
    # -----------------------------------------------------

    db.add(bid)

    db.commit()

    db.refresh(bid)

    # -----------------------------------------------------
    # BROADCAST NEW BID THROUGH WEBSOCKET
    # -----------------------------------------------------

    await manager.broadcast(
        auction.id,
        {
            "type": "new_bid",
            "auction_id": auction.id,
            "bid_id": bid.id,
            "buyer_id": bid.buyer_id,
            "amount": float(
                bid.amount
            ),
            "current_price": float(
                auction.current_price
            ),
            "message": "New bid placed"
        }
    )

    return bid


# =========================================================
# GET BID HISTORY
# =========================================================

@router.get(
    "/{auction_id}/bids",
    response_model=list[BidResponse]
)
def get_bid_history(
    auction_id: int,
    db: Session = Depends(get_db)
):
    # -----------------------------------------------------
    # Check auction exists
    # -----------------------------------------------------

    auction = (
        db.query(Auction)
        .filter(
            Auction.id == auction_id
        )
        .first()
    )

    if not auction:

        raise HTTPException(
            status_code=404,
            detail="Auction not found"
        )

    # -----------------------------------------------------
    # Update auction status
    # -----------------------------------------------------

    old_status = auction.status

    update_auction_status(
        auction
    )

    if old_status != auction.status:

        db.commit()

    # -----------------------------------------------------
    # Get bid history
    # Highest bid first
    # -----------------------------------------------------

    bids = (
        db.query(Bid)
        .filter(
            Bid.auction_id == auction_id
        )
        .order_by(
            Bid.amount.desc()
        )
        .all()
    )

    return bids


# =========================================================
# GET AUCTION WINNER
# =========================================================

@router.get(
    "/{auction_id}/winner"
)
def get_auction_winner(
    auction_id: int,
    db: Session = Depends(get_db)
):
    # -----------------------------------------------------
    # Find auction
    # -----------------------------------------------------

    auction = (
        db.query(Auction)
        .filter(
            Auction.id == auction_id
        )
        .first()
    )

    if not auction:

        raise HTTPException(
            status_code=404,
            detail="Auction not found"
        )

    # -----------------------------------------------------
    # Automatically update auction status
    # -----------------------------------------------------

    old_status = auction.status

    update_auction_status(
        auction
    )

    # Save status if changed
    if old_status != auction.status:

        db.commit()

        db.refresh(auction)

    # -----------------------------------------------------
    # Auction must be ended
    # -----------------------------------------------------

    if auction.status != AuctionStatus.ENDED:

        raise HTTPException(
            status_code=400,
            detail="Auction has not ended yet"
        )

    # -----------------------------------------------------
    # Find highest bid
    # -----------------------------------------------------

    winning_bid = (
        db.query(Bid)
        .filter(
            Bid.auction_id == auction_id
        )
        .order_by(
            Bid.amount.desc(),
            Bid.created_at.asc()
        )
        .first()
    )

    # -----------------------------------------------------
    # No bids
    # -----------------------------------------------------

    if not winning_bid:

        return {
            "auction_id": auction.id,
            "winner": None,
            "message": "No bids were placed"
        }

    # -----------------------------------------------------
    # Return winner
    # -----------------------------------------------------

    return {
        "auction_id": auction.id,
        "winner": {
            "buyer_id": winning_bid.buyer_id,
            "winning_bid": winning_bid.amount,
            "bid_id": winning_bid.id,
            "won_at": winning_bid.created_at
        }
    }