from datetime import datetime
from pydantic import BaseModel, EmailStr
from typing import Optional


class UserCreateSchema(BaseModel):
    name: str
    google_sub: Optional[str]
    email: EmailStr


class UserCreateOut(BaseModel):
    name: str
    email: EmailStr
    token: str


class GoogleIDTokenSchema(BaseModel):
    sub: Optional[str]
    email: EmailStr
    email_verified: bool
    name: str
    aud: str
    exp: datetime
    iss: str
