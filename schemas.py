"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Literal

# Example schemas (you can keep or ignore in your app)
class User(BaseModel):
    """
    Users collection schema
    Collection name: "user" (lowercase of class name)
    """
    name: str = Field(..., description="Full name")
    email: str = Field(..., description="Email address")
    address: str = Field(..., description="Address")
    age: Optional[int] = Field(None, ge=0, le=120, description="Age in years")
    is_active: bool = Field(True, description="Whether user is active")

class Product(BaseModel):
    """
    Products collection schema
    Collection name: "product" (lowercase of class name)
    """
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., ge=0, description="Price in dollars")
    category: str = Field(..., description="Product category")
    in_stock: bool = Field(True, description="Whether product is in stock")

# Plumbing app schemas

class Service(BaseModel):
    """
    Plumbing services
    Collection name: "service"
    """
    name: str = Field(..., description="Service name, e.g. Pipe Installation")
    description: Optional[str] = Field(None, description="What the service includes")
    unit: Literal["sqm", "fixture", "flat"] = Field(..., description="Pricing unit")
    rate: float = Field(..., ge=0, description="Base rate per unit in USD")
    category: Optional[str] = Field(None, description="Category such as Installation, Repair, Inspection")

class QuoteItem(BaseModel):
    service_id: str
    service_name: str
    unit: Literal["sqm", "fixture", "flat"]
    quantity: float
    rate: float
    cost: float

class Quote(BaseModel):
    """
    Quotes produced by the estimator
    Collection name: "quote"
    """
    project_name: str
    area_sqm: float = Field(0, ge=0)
    fixtures: int = Field(0, ge=0)
    selected_service_ids: List[str] = []
    location_factor: float = Field(1.0, ge=0.5, le=2.0, description="Multiplier to account for regional pricing")

    # computed fields saved
    items: List[QuoteItem] = []
    subtotal: float = 0
    overhead: float = 0
    tax: float = 0
    total: float = 0
