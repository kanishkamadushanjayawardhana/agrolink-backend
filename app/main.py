from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Depends, File, HTTPException, UploadFile, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.core.database import Base, engine
from app.core.security import get_current_user
from app.models.user import User, UserRole
from app.models.auction import Auction
from app.models.product import Product
from app.models.escrow import Escrow, EscrowMilestone

from app.api.auth.routes import router as auth_router
from app.api.users.routes import router as users_router
from app.api.auctions.routes import router as auctions_router
from app.api.products import router as products_router
from app.routes.escrow_routes import router as escrow_router
from app.routes.auction_websocket import router as auction_websocket_router


Base.metadata.create_all(bind=engine)

app = FastAPI(title="AgroLink API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Uploaded product photos are stored in backend/uploads and served at /uploads/<filename>.
UPLOAD_DIR = Path(__file__).resolve().parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
MAX_IMAGE_SIZE = 8 * 1024 * 1024  # 8 MB


@app.post("/upload-image")
async def upload_product_image(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.FARMER:
        raise HTTPException(status_code=403, detail="Only farmers can upload product photos")

    extension = ALLOWED_IMAGE_TYPES.get(file.content_type or "")
    if not extension:
        raise HTTPException(status_code=415, detail="Upload a JPG, PNG, or WEBP image")

    contents = await file.read(MAX_IMAGE_SIZE + 1)
    if not contents:
        raise HTTPException(status_code=400, detail="The uploaded image is empty")
    if len(contents) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=413, detail="Image must be 8 MB or smaller")

    filename = f"{uuid4().hex}{extension}"
    destination = UPLOAD_DIR / filename
    destination.write_bytes(contents)
    await file.close()

    image_url = f"{str(request.base_url).rstrip('/')}/uploads/{filename}"
    return {"image_url": image_url}


app.include_router(auth_router)
app.include_router(auctions_router)
app.include_router(users_router)
app.include_router(products_router)
app.include_router(escrow_router)
app.include_router(auction_websocket_router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "agrolink-api"}
