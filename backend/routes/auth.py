from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.models.models import UserCreate, UserOut, Token
import backend.models.sql_models as db_models
from backend.db.apply_schema import get_db
from backend.core.security import hash_password, verify_password, create_access_token
from fastapi.security import OAuth2PasswordRequestForm

router = APIRouter()


@router.post(
    "/auth",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    tags=["Authentication"],
)
async def register_user(user_in: UserCreate, db: Session = Depends(get_db)) -> UserOut:

    db_user = db.query(db_models.User).filter_by(login=user_in.login).first()

    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="User already registered"
        )

    hashed_password = hash_password(user_in.password)

    db_user = db_models.User(login=user_in.login, hashed_password=hashed_password)

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user


@router.post(
    "/login", response_model=Token, status_code=status.HTTP_200_OK, tags=["Login"]
)
async def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):

    db_user = db.query(db_models.User).filter_by(login=form_data.username).first()

    if not db_user or not verify_password(form_data.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    access_token = create_access_token(subject=db_user.login)
    return {"access_token": access_token, "token_type": "bearer"}
