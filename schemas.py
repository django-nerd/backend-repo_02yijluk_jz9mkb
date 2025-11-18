"""
Database Schemas for the Digital Services Platform

Each Pydantic model maps to a MongoDB collection using the lowercase of the class name
(e.g., User -> "user"). These are used for validation and for the helper
functions in database.py.
"""
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime

class User(BaseModel):
    name: str = Field(..., description="Full name")
    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., description="Hashed password or demo secret")
    role: Literal['buyer','reseller','admin','owner'] = Field('buyer', description="Role for RBAC")
    is_active: bool = Field(True)

class Product(BaseModel):
    sku: str = Field(...)
    title: str = Field(...)
    description: Optional[str] = None
    price: float = Field(..., ge=0)
    category: Literal['vps','domain','panel','addon'] = Field('vps')
    stock: int = Field(100, ge=0)

class OrderItem(BaseModel):
    sku: str
    title: str
    qty: int = Field(1, ge=1)
    unit_price: float = Field(..., ge=0)

class Order(BaseModel):
    user_email: EmailStr
    items: List[OrderItem]
    subtotal: float
    discount: float = 0
    tax: float = 0
    total: float
    status: Literal['pending','paid','failed','refunded'] = 'pending'
    payment_method: Optional[Literal['paypal','robux','manual']] = None

class Payment(BaseModel):
    order_id: str
    amount: float
    method: Literal['paypal','robux','manual']
    status: Literal['success','failed','pending'] = 'pending'

class Withdrawal(BaseModel):
    actor_email: EmailStr
    amount: float
    status: Literal['requested','approved','rejected','paid'] = 'requested'
    note: Optional[str] = None

class Log(BaseModel):
    timestamp: datetime
    category: Literal['order','payment','auth','withdrawal','system']
    actor: Optional[str] = None
    description: str
    related_id: Optional[str] = None

