from __future__ import annotations

from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.orm import Session
from sqlalchemy import select
from passlib.context import CryptContext

from app.db.models import Company, User
from apps.api.app_api.dependencies import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    get_current_user,
    get_db_session,
)

router = APIRouter(prefix="/auth", tags=["auth"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class CompanyRegisterRequest(BaseModel):
    company_name: str
    admin_email: EmailStr
    admin_password: str
    admin_full_name: str | None = None
    ai_enable_flag: bool = False
    total_enable_review: int = 100
    analyze_competitor_flag: bool = False

    @field_validator("admin_password")
    @classmethod
    def validate_bcrypt_password_length(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must be 72 bytes or fewer.")
        return value

class TokenResponse(BaseModel):
    access_token: str
    token_type: str

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str | None
    company_id: int
    company_name: str
    ai_enable_flag: bool
    total_enable_review: int
    analyze_competitor_flag: bool

@router.post("/register", response_model=UserResponse)
def register_company(payload: CompanyRegisterRequest, db: Session = Depends(get_db_session)):
    # Check if user exists
    existing_user = db.scalar(select(User).where(User.email == payload.admin_email))
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    company = Company(
        name=payload.company_name,
        ai_enable_flag=payload.ai_enable_flag,
        total_enable_review=payload.total_enable_review,
        analyze_competitor_flag=payload.analyze_competitor_flag,
    )
    db.add(company)
    db.flush()

    user = User(
        company_id=company.id,
        email=payload.admin_email,
        password_hash=pwd_context.hash(payload.admin_password),
        full_name=payload.admin_full_name,
    )
    db.add(user)
    db.commit()
    db.refresh(company)
    db.refresh(user)
    
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        company_id=company.id,
        company_name=company.name,
        ai_enable_flag=company.ai_enable_flag,
        total_enable_review=company.total_enable_review,
        analyze_competitor_flag=company.analyze_competitor_flag
    )

@router.post("/login", response_model=TokenResponse)
def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Session = Depends(get_db_session)
):
    user = db.scalar(select(User).where(User.email == form_data.username))
    if not user or not pwd_context.verify(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
def read_users_me(current_user: Annotated[User, Depends(get_current_user)]):
    company = current_user.company
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        company_id=company.id,
        company_name=company.name,
        ai_enable_flag=company.ai_enable_flag,
        total_enable_review=company.total_enable_review,
        analyze_competitor_flag=company.analyze_competitor_flag
    )
