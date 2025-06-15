from fastapi import Depends, APIRouter
import backend.models.sql_models as db_models
from backend.models.models import UserOut
from backend.core.security import get_current_user


router = APIRouter()


@router.get("/me", response_model=UserOut, tags=["Oauth2scheme"])
async def get_me(current_user: db_models.User = Depends(get_current_user)):
    return current_user
