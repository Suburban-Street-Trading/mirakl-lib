from typing import List, Optional
from pydantic import BaseModel

class AllPrice(BaseModel):
    channel_code: Optional[str]
    discount_end_date: Optional[str]
    discount_start_date: Optional[str]
    price: float

class AllPriceUpdate(BaseModel):
    discount_end_date: Optional[str] = None
    discount_start_date: Optional[str] = None
    unit_discount_price: Optional[float] = None
    unit_origin_price: Optional[float] = None

class ApplicablePricing(BaseModel):
    channel_code: Optional[str]
    discount_start_date: Optional[str]
    discount_end_date: Optional[str]
    price: float

class Discount(BaseModel):
    discount_price: float
    end_date: Optional[str]
    origin_price: float
    start_date: Optional[str]

class DiscountUpdate(BaseModel):
    discount_price: float
    end_date: Optional[str] = None
    start_date: Optional[str] = None

class MiraklOffer(BaseModel):
    active: bool
    all_prices: List[AllPrice]
    applicable_pricing: ApplicablePricing
    category_code: str
    category_label: str
    description: Optional[str]
    discount: Optional[Discount]
    inactivity_reasons: Optional[List[str]]
    leadtime_to_ship: int
    offer_id: int
    product_brand: Optional[str]
    product_description: str
    product_sku: str
    product_title: str
    quantity: int
    shop_sku: str
    state_code: str
    total_price: float

class MiraklOfferUpdate(BaseModel):
    all_prices: Optional[AllPriceUpdate] = None
    discount: DiscountUpdate
    price: float
    quantity: Optional[int] = 0
    shop_sku: str
    state_code: str
    update_delete: Optional[str] = "update"
