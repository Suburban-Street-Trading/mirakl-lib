from typing import NotRequired, TypedDict


class OfferUpdateInput(TypedDict):
    offer_sku: str
    product_id: str
    base_price: float
    discount_price: NotRequired[float]
    discount_start_date: NotRequired[str]
    discount_end_date: NotRequired[str]
    quantity: int
