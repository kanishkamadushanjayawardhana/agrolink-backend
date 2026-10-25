
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User, UserRole
from app.models.product import Product
from app.schemas.product import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
)

router = APIRouter(
    prefix="/products",
    tags=["Products"],
)


# =========================================================
# CREATE PRODUCT
# =========================================================

@router.post("/", response_model=ProductResponse)
def create_product(
    product_data: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.FARMER:
        raise HTTPException(
            status_code=403,
            detail="Only farmers can create product listings",
        )

    new_product = Product(
        farmer_id=current_user.id,
        product_name=product_data.product_name,
        category=product_data.category,
        quantity=product_data.quantity,
        unit=product_data.unit,
        expected_price=product_data.expected_price,
        location=product_data.location,
        harvest_date=product_data.harvest_date,
        description=product_data.description,
        image_url=product_data.image_url,
    )

    db.add(new_product)
    db.commit()
    db.refresh(new_product)

    return new_product


# =========================================================
# GET ALL PRODUCTS
# =========================================================

@router.get("/", response_model=list[ProductResponse])
def get_products(
    db: Session = Depends(get_db),
):
    return db.query(Product).all()


# =========================================================
# GET SINGLE PRODUCT
# =========================================================

@router.get("/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
):
    product = db.query(Product).filter(
        Product.id == product_id
    ).first()

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    return product


# =========================================================
# UPDATE PRODUCT
# =========================================================

@router.patch("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    product_data: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.FARMER:
        raise HTTPException(
            status_code=403,
            detail="Only farmers can update product listings",
        )

    product = db.query(Product).filter(
        Product.id == product_id
    ).first()

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    if product.farmer_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You can only update your own products",
        )

    updates = product_data.model_dump(exclude_unset=True)

    if not updates:
        raise HTTPException(
            status_code=400,
            detail="No product fields provided",
        )

    required_fields = {
        "product_name",
        "category",
        "quantity",
        "unit",
        "expected_price",
        "location",
        "harvest_date",
    }

    for field, value in updates.items():
        if field in required_fields and value is None:
            raise HTTPException(
                status_code=422,
                detail=f"{field} cannot be null",
            )

        setattr(product, field, value)

    db.commit()
    db.refresh(product)

    return product


# =========================================================
# DELETE PRODUCT
# =========================================================

@router.delete("/{product_id}")
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.FARMER:
        raise HTTPException(
            status_code=403,
            detail="Only farmers can delete product listings",
        )

    product = db.query(Product).filter(
        Product.id == product_id
    ).first()

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    if product.farmer_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You can only delete your own products",
        )

    db.delete(product)
    db.commit()

    return {
        "message": "Product deleted successfully",
        "product_id": product_id,
    }
