"""User and Profile Schema"""

from pydantic import BaseModel, EmailStr, Field
from datetime import datetime, timezone
from myprofile.utils import get_cat_fact


class User(BaseModel):
    email: EmailStr
    name: str
    stack: str


class Profile(BaseModel):
    status: str
    user: User
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    fact: str


def get_profile():
    try:
        user = User(
            email="merytpeters@gmail.com",
            name="Akpevweoghene Merit Edafe",
            stack="Python(FastAPI, Djanjo, Flask), MERN, PERN, CSS, Figma",
        )
        fact = get_cat_fact()
        if isinstance(fact, dict):
            fact = fact.get("fact") or fact.get("text") or str(fact)
        elif fact is None:
            fact = ""
        profile = Profile(
            status="success", user=user, timestamp=datetime.now(), fact=fact
        )
        return profile
    except Exception:
        user = None
        profile = None
        return profile
