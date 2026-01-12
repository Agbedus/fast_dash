from typing import Optional
from sqlmodel import SQLModel, Field

class Account(SQLModel, table=True):
    __tablename__ = "account"
    userId: str = Field(foreign_key="users.id", primary_key=True)
    type: str = Field(nullable=False)
    provider: str = Field(primary_key=True)
    providerAccountId: str = Field(primary_key=True)
    refresh_token: Optional[str] = None
    access_token: Optional[str] = None
    expires_at: Optional[int] = None
    token_type: Optional[str] = None
    scope: Optional[str] = None
    id_token: Optional[str] = None
    session_state: Optional[str] = None

class Session(SQLModel, table=True):
    __tablename__ = "session"
    sessionToken: str = Field(primary_key=True)
    userId: str = Field(foreign_key="users.id")
    expires: int = Field(nullable=False) # timestamp_ms
