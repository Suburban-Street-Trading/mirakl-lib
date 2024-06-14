from typing import List, Optional
from pydantic import BaseModel

class ShippingAddress(BaseModel):
    city: str
    country: str
    country_iso_code: str | None
    firstname: str
    lastname: str
    phone: Optional[str]
    state: str
    street_1: str
    street_2: Optional[str]
    zipcode: str
    
class Customer(BaseModel):
    firstname: str
    lastname: str
    email: str | None
    shipping_address: ShippingAddress | None

class MiraklOrderLine(BaseModel):
    created_date: str
    offer_id: int
    offer_sku: str
    product_title: str
    order_line_id: str
    order_line_state: str
    price: float
    quantity: int
    total_price: float

class MiraklOrder(BaseModel):
    order_id: str
    order_state: str
    created_date: str
    customer: Customer
    order_lines: List[MiraklOrderLine]


    