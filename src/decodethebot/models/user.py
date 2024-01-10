from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    token: str
    email: str
    last_active: datetime = Field(default_factory=datetime.now)
