from pydantic import BaseModel
from typing import Optional, List
from datetime import date

class BookBase(BaseModel):
    title: str
    author: str
    genre: str
    description: Optional[str] = None
    total_copies: int = 1
    cover_image_url: Optional[str] = None

class BookCreate(BookBase):
    pass

class Book(BookBase):
    id: int
    available_copies: int

    class Config:
        from_attributes = True

class UserBase(BaseModel):
    username: str
    email: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    role: str

    class Config:
        from_attributes = True
