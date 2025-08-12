from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List
from database import (
    get_db, verify_admin_token, authorize_admin_controls,
    fetch_managed_users, count_managed_users, create_elderly_user,
    fetch_user_by_id
)
from admin_models import (
    ElderlyUser, ElderlyListResponse, CreateElderlyRequest, AdminActionResponse
)

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/elderly", response_model=ElderlyListResponse)
def list_managed_elderly(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    admin_id: str = Depends(verify_admin_token),
    db: Session = Depends(get_db)
):
    """List elderly users managed by the admin"""
    skip = (page - 1) * limit
    elderly_users = fetch_managed_users(admin_id, db, skip=skip, limit=limit)
    total = count_managed_users(admin_id, db)
    
    return ElderlyListResponse(
        elderly=elderly_users,
        total=total,
        page=page,
        limit=limit
    )

@router.post("/elderly", response_model=AdminActionResponse)
def create_elderly(
    elderly_data: CreateElderlyRequest,
    admin_id: str = Depends(verify_admin_token),
    db: Session = Depends(get_db)
):
    """Create a new elderly user under admin management"""
    try:
        new_elderly = create_elderly_user(admin_id, elderly_data.dict(), db)
        return AdminActionResponse(
            message="Elderly user created successfully",
            elderly_id=new_elderly.userId,
            action="create"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create elderly user: {str(e)}"
        )

@router.get("/elderly/{elderly_id}", response_model=ElderlyUser)
def get_elderly_details(
    elderly_id: str,
    admin_id: str = Depends(verify_admin_token),
    db: Session = Depends(get_db)
):
    """Get details of a specific elderly user"""
    authorize_admin_controls(admin_id, elderly_id, db)
    
    elderly = fetch_user_by_id(elderly_id, db)
    if not elderly:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Elderly user not found"
        )
    
    return elderly

@router.delete("/elderly/{elderly_id}", response_model=AdminActionResponse)
def remove_elderly(
    elderly_id: str,
    admin_id: str = Depends(verify_admin_token),
    db: Session = Depends(get_db)
):
    """Remove elderly user from admin management (sets adminId to NULL)"""
    authorize_admin_controls(admin_id, elderly_id, db)
    
    elderly = fetch_user_by_id(elderly_id, db)
    if not elderly:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Elderly user not found"
        )
    
    # Remove admin relationship (don't delete user, just unmanage)
    elderly.adminId = None
    db.commit()
    
    return AdminActionResponse(
        message="Elderly user removed from management",
        elderly_id=elderly_id,
        action="remove"
    )
