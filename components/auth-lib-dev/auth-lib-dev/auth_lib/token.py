import jwt
from fastapi import HTTPException
from pydantic import ValidationError

from auth_lib.schemas import UserPayload


def decode_token(token: str) -> UserPayload:
    """Decode a JWT token and return a validated UserPayload.

    Does not verify the token signature. Validates expiration and payload structure.

    Raises:
        HTTPException(401): If token is expired, malformed, or has invalid payload.
    """
    try:
        payload = jwt.decode(
            token,
            algorithms=["HS256"],
            options={"verify_signature": False, "verify_exp": True},
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.DecodeError:
        raise HTTPException(status_code=401, detail="Invalid token")

    try:
        return UserPayload.model_validate(payload)
    except ValidationError:
        raise HTTPException(status_code=401, detail="Invalid token payload")
