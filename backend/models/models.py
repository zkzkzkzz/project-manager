from pydantic import BaseModel, ConfigDict, Field, field_validator
from datetime import datetime
import re
from typing import Optional


class ProjectCreate(BaseModel):
    name: str
    description: str
    model_config = ConfigDict(extra="forbid")


class ProjectOut(ProjectCreate):
    id: int
    owner_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserBase(BaseModel):
    login: str = Field(
        ..., min_length=3, max_length=50, description="Username (3-50characters)"
    )


class UserCreate(UserBase):
    password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="Password(8-100 characters, requires A-Z, a-z, 0-9)",
    )

    @classmethod
    @field_validator("password")
    def password_validator(cls, value):
        if not re.search(r"[a-z]", value):
            raise ValueError("Password must contain a lowercase letter")
        if not re.search(r"[A-Z]", value):
            raise ValueError("Password must contain an uppercase letter")
        if not re.search(r"\d", value):
            raise ValueError("Password must contain a digit")

        return value

    model_config = ConfigDict(extra="forbid")


class UserLogin(BaseModel):
    username: str
    password: str
    model_config = ConfigDict(extra="forbid")


class UserOut(UserBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    subject: str | None = None


class DocumentBase(BaseModel):
    file_name: str
    file_type: Optional[str]


class DocumentOut(DocumentBase):
    id: int
    project_id: int
    s3_key: str

    uploader_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class DocumentList(DocumentBase):
    id: int
    created_at: datetime
    download_url: str


# No from attributes=True because of download_url that is computed here
