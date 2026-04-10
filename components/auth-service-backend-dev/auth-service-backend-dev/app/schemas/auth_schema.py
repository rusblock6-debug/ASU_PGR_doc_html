from pydantic import BaseModel
from typing import Optional

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class Login(BaseModel):
    username: str
    password: str

class SignUp(BaseModel):
    username: str
    password: str
