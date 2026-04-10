from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from jwt import decode, PyJWTError
import logging
from app.database import get_db
from app.models.user_model import User
from app.schemas.auth_schema import Login, Token, SignUp
from app.schemas.permission_schema import PermissionCheck
from app.utils import settings, redis_client
from app.utils.user_util import get_current_user
from app.utils.token_util import create_access_token, create_refresh_token
from app.services.users import get_user_roles_and_permissions

router = APIRouter(tags=["auth"])
logger = logging.getLogger(__name__)

@router.post("/signup", response_model=Token)
async def signup(form_data: SignUp, db: AsyncSession = Depends(get_db)):
    """Register a new user and issue JWT tokens."""
    logger.info("Attempting to register user: %s", form_data.username)
    result = await db.execute(
        select(User).filter((User.username == form_data.username))
    )
    existing_user = result.scalar_one_or_none()
    if existing_user:
        logger.warning("Registration failed: User with username %s already exists", form_data.username)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User with this username already exists")

    new_user = User(
        username=form_data.username,
        is_active=True
    )
    new_user.set_password(form_data.password)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    logger.info("User %s registered successfully", form_data.username)
    token_data = await get_user_roles_and_permissions(db, new_user.id)
    token_data["sub"] = new_user.username
    access_token = create_access_token(data=token_data)
    refresh_token = create_refresh_token(data={"sub": new_user.username})
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

@router.post("/login", response_model=Token)
async def login(form_data: Login, db: AsyncSession = Depends(get_db)):
    """Authenticate a user and issue JWT tokens."""
    logger.info("Attempting login for user: %s", form_data.username)
    result = await db.execute(select(User).filter(User.username == form_data.username))
    user = result.scalar_one_or_none()
    if not user or not user.verify_password(form_data.password):
        logger.warning("Login failed for user %s: Incorrect username or password", form_data.username)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect username or password")
    # if not user.is_active:
    #     logger.warning("Login failed for user %s: Inactive user", form_data.username)
    #     raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    token_data = await get_user_roles_and_permissions(db, user.id)
    token_data["sub"] = user.username
    access_token = create_access_token(data=token_data)
    refresh_token = create_refresh_token(data={"sub": user.username})
    logger.info("User %s logged in successfully", form_data.username)
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

@router.post("/refresh", response_model=Token)
async def refresh(refresh_token: str, db: AsyncSession = Depends(get_db)):
    """Refresh JWT tokens using a valid refresh token."""
    logger.info("Attempting to refresh token")
    if await redis_client.is_token_blacklisted(refresh_token):
        logger.warning("Refresh failed: Token blacklisted")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token blacklisted")
    try:
        payload = decode(refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            logger.warning("Refresh failed: Invalid refresh token (no username)")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    except PyJWTError:
        logger.warning("Refresh failed: Invalid refresh token (JWT error)")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    
    result = await db.execute(select(User).filter(User.username == username))
    user = result.scalar_one_or_none()
    # if user is None or not user.is_active:
    if user is None:
        logger.warning("Refresh failed for user %s: Invalid or inactive user", username)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")

    token_data = await get_user_roles_and_permissions(db, user.id)
    token_data["sub"] = user.username
    access_token = create_access_token(data=token_data)
    new_refresh_token = create_refresh_token(data={"sub": user.username})
    logger.info("Token refreshed successfully for user %s", username)
    return {"access_token": access_token, "refresh_token": new_refresh_token, "token_type": "bearer"}

@router.post("/logout")
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    refresh_token: str = None
):
    """Log out a user and blacklist both access and refresh tokens."""
    logger.info("Logging out user: %s", current_user.username)

    auth_header = request.headers.get("Authorization")
    if auth_header:
        access_token = auth_header.replace("bearer ", "")

        await redis_client.add_to_blacklist(access_token)

        logger.info("Access token blacklisted for user %s", current_user.username)

    if refresh_token:
        await redis_client.add_to_blacklist(refresh_token)
        logger.info("Refresh token blacklisted for user %s", current_user.username)

    return {"message": "Logged out"}

@router.post("/verify")
async def get_role(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    user_data = await get_user_roles_and_permissions(db, current_user.id)
    result = {
        "valid": True,
        **user_data
    }
    return result
