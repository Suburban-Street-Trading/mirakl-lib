from typing import List
from pydantic import BaseModel

from mirakl_lib.order import MiraklOrder


class OR11Response(BaseModel):
    orders: List[MiraklOrder]
    total_count: int