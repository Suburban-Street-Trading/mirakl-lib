from typing import List
from pydantic import BaseModel

from mirakl_lib.order import MiraklOrder
from mirakl_lib.offer import MiraklOffer


class OR11Response(BaseModel):
    orders: List[MiraklOrder]
    total_count: int


class OfferListResponse(BaseModel):
    offers: List[MiraklOffer]
    total_count: int    