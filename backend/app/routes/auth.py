import email

from app.core.deps import get_current_user
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse 
from app.schemas.auth import LoginRequest
from app.core.jwt import create_access_token

router=APIRouter(prefix="/auth",tags=["Authentication"])

@router.post("/signup",response_model=UserResponse)
def signup(user_data: UserCreate, db:Session=Depends(get_db)):
    existing_user=db.query(User).filter(User.email==user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_pw=hash_password(user_data.password)
    
    new_user=User(
        name=user_data.name,
        email=user_data.email,
        hashed_password=hashed_pw
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user

@router.post("/login")
def login(login_data: LoginRequest, db: Session=Depends(get_db)):
    user=db.query(User).filter(User.email==login_data.email).first()
    
    if not user:
        raise HTTPException(status_code=401,detail="Invalid email or password")
    
    if not verify_password(login_data.password,user.hashed_password):
        raise HTTPException(status_code=401,detail="Invalid email or password")

    access_token=create_access_token(user_id=user.id)
    
    return{
        "access_token":access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "name": user.name
    }
    
@router.get("/me", response_model=UserResponse)
def get_me(current_user: User=Depends(get_current_user)):
    return current_user