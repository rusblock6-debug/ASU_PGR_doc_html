from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from jwt import decode, PyJWTError

from app.database import get_db
from app.models.user_model import User
from app.models.role_model import Role
from app.schemas.auth_schema import TokenData
from app.config import get_settings
from . import redis_client
from .permission_util import has_permission


settings = get_settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

async def get_current_user_mock(
    db: AsyncSession = Depends(get_db)
) -> User:
    """Заглушка для MVP - возвращает любого пользователя без проверки токена"""
    result = await db.execute(
        select(User)
        .options(selectinload(User.role).selectinload(Role.permissions))
        .filter(User.is_active == True)
        .order_by(User.id)
    )
    user = result.scalars().first()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No active users found in database"
        )
    
    return user

async def get_admin_user_mock(
    db: AsyncSession = Depends(get_db)
) -> User:
    """Заглушка для MVP - возвращает админа-пользователя без проверки токена"""
    result = await db.execute(
        select(User)
        .options(selectinload(User.role).selectinload(Role.permissions))
        .filter(User.username == "admin")
    )
    user = result.scalars().first()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Mock user not found"
        )
    
    return user



async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    """Получение текущего пользователя по JWT токену с подгрузкой роли и permissions."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if await redis_client.is_token_blacklisted(token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token blacklisted")
    try:
        payload = decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except PyJWTError:
        raise credentials_exception

    result = await db.execute(
        select(User)
        .options(
            selectinload(User.role).selectinload(Role.permissions)
        )
        .filter(User.username == token_data.username)
    )
    user = result.scalars().first()
    if user is None:
        raise credentials_exception
    # if not user.is_active:
    #     raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user_mock)
) -> User:
    """Проверка, что пользователь активен."""
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user


async def admin_required(
    current_user: User = Depends(get_current_user)
    # current_user
) -> User:
    """Проверка, что пользователь имеет admin-права."""
    if not await has_permission(current_user, "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin permission required")
    return current_user
