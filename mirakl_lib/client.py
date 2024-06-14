from dataclasses import dataclass
from typing import Callable, List, Tuple, Optional
import requests
import time
import logging

from .order import Customer, MiraklOrder, MiraklOrderLine, ShippingAddress
from .offer import MiraklOffer, MiraklOfferUpdate
from .response import OR11Response, OfferListResponse

logger = logging.getLogger(__name__)

@dataclass
class GetWaitingOrdersResult:
    orders: List[MiraklOrder]
    has_more: bool
    next_order_start_offset: int

class RateLimitException(Exception):
    def __init__(self, message: str, retry_after_seconds: Optional[int] = None):
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds

class MiraklClient:
    
    def __init__(self, marketplace: str, base_url: str=None, api_key: str=None):
        self.marketplace = marketplace
        self.base_url = base_url
        self.api_key = api_key
    
    def _order_line(self, order_line: dict) -> MiraklOrderLine:
        return MiraklOrderLine(
            created_date=order_line['created_date'],
            offer_id=order_line['offer_id'],
            offer_sku=order_line['offer_sku'],
            order_line_id=order_line['order_line_id'],
            order_line_state=order_line['order_line_state'],
            price=order_line['price'],
            quantity=order_line['quantity'],
            total_price=order_line['total_price']
        )
    
    def _shipping_address(self, shipping_address: dict) -> ShippingAddress:
        return ShippingAddress(
            city=shipping_address['city'],
            country=shipping_address['country'],
            country_iso_code=shipping_address['country_iso_code'],
            firstname=shipping_address['firstname'],
            lastname=shipping_address['lastname'],
            phone=shipping_address['phone'],
            state=shipping_address['state'],
            street_1=shipping_address['street_1'],
            street_2=shipping_address['street_2'],
            zipcode=shipping_address['zip_code']
        )
        
    def _customer(self, customer: dict) -> Customer:
        shipping_address_json = customer.get('shipping_address', None)
        shipping_address = self._shipping_address(shipping_address_json) if shipping_address_json else None
        
        return Customer(
            firstname=customer['firstname'],
            lastname=customer['lastname'],
            email=customer.get('email', None),
            shipping_address=shipping_address
        )
        
    def _mirakl_order(self, order: dict) -> MiraklOrder:
        return MiraklOrder(
            order_id=order['order_id'],
            order_state=order['order_state'],
            created_date=order['created_date'],
            customer=self._customer(order['customer']),
            order_lines=[self._order_line(line) for line in order['order_lines']]
        )

    def get_bulk_order_ids(self, order_ids: List[str]) -> GetWaitingOrdersResult:
        order_id_chunks = [order_ids[i:i+100] for i in range(0, len(order_ids), 100)]
        all_orders = []

        for chunk in order_id_chunks:
            result = self.get_orders(offset=0, size=100, order_ids=chunk)
            all_orders.extend(result.orders)

        return GetWaitingOrdersResult(
            orders=all_orders,
            has_more=False,
            next_order_start_offset=0
        )

    def get_orders(self, offset: int, size: int, status: str=None, order_ids: List[str]=None) -> GetWaitingOrdersResult:
        url = f"{self.base_url}/api/orders"
        params = {"offset": offset, "max": size}
        
        if order_ids:
            params['order_ids'] = ','.join(order_ids)
            
        if status is not None:
            params['order_state_codes'] = status
        
        headers = {
            "Authorization": f"{self.api_key}",
            "Accept": "application/json"
        }
        
        response = requests.get(url, params=params, headers=headers)
        
        if response.ok:
            response_json = response.json()
            or11_response = OR11Response(
                orders=[self._mirakl_order(order) for order in response_json['orders']],
                total_count=response_json['total_count']
            )
            has_more = or11_response.total_count > offset + size
            return GetWaitingOrdersResult(
                orders=or11_response.orders,
                has_more=has_more,
                next_order_start_offset=offset + size
            )
        else:
            response.raise_for_status()
            
    def accept_order(self, order_id: str, order_line_ids: List[str]):
        url = f"{self.base_url}/api/orders/{order_id}/accept"
        headers = {
            "Authorization": f"{self.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        payload = {"order_lines": [{"accepted": True, "id": id} for id in order_line_ids]} 
        
        response = requests.put(url, headers=headers, json=payload)
        
        if not response.ok:
            response.raise_for_status()

    def _mirakl_offer(self, offer: dict) -> MiraklOffer:
        return MiraklOffer(
            active=offer['active'],
            all_prices=[AllPrice(**price) for price in offer['all_prices']],
            applicable_pricing=ApplicablePricing(**offer['applicable_pricing']),
            category_code=offer['category_code'],
            category_label=offer['category_label'],
            description=offer.get('description'),
            discount=Discount(**offer['discount']) if offer.get('discount') else None,
            inactivity_reasons=offer.get('inactivity_reasons'),
            leadtime_to_ship=offer['leadtime_to_ship'],
            offer_id=offer['offer_id'],
            product_brand=offer.get('product_brand'),
            product_description=offer['product_description'],
            product_sku=offer['product_sku'],
            product_title=offer['product_title'],
            quantity=offer['quantity'],
            shop_sku=offer['shop_sku'],
            state_code=offer['state_code'],
            total_price=offer['total_price']
        )
    
    def get_all_offers(self) -> List[MiraklOffer]:
        rate_limiter = RateLimiter(0.5)
        endpoint = "/api/offers"
        limit_value = 100
        offset_value = 0
        total_offers = 0

        def get_next_offer_page():
            nonlocal offset_value
            return self._get_resource_page(endpoint, limit_value, offset_value, rate_limiter)
        
        offers = []
        while True:
            response = get_next_offer_page()
            if not response.ok:
                response.raise_for_status()
            response_json = response.json()
            total_offers = response_json['total_count']
            offers.extend(response_json['offers'])
            offset_value += limit_value
            if offset_value >= total_offers:
                break
        
        return [self._mirakl_offer(offer) for offer in offers]

    def update_offers(self, offers: List[MiraklOfferUpdate]):
        url = f"{self.base_url}/api/offers"
        headers = {
            "Authorization": f"{self.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        payload = {"offers": [offer.dict() for offer in offers]}
        
        response = requests.post(url, headers=headers, json=payload)
        
        if not response.ok:
            response.raise_for_status()
    
    def _get_resource_page(self, endpoint: str, limit: int, offset: int, rate_limiter):
        url = f"{self.base_url}{endpoint}"
        params = {"max": limit, "offset": offset}
        headers = {
            "Authorization": f"{self.api_key}",
            "Accept": "application/json"
        }

        rate_limiter.acquire()
        response = requests.get(url, params=params, headers=headers)
        
        if response.status_code == 429:  # Too Many Requests
            retry_after = int(response.headers.get("Retry-After", 1))
            logger.warning(f"Rate limit exceeded, retrying after {retry_after} seconds.")
            time.sleep(retry_after)
            return self._get_resource_page(endpoint, limit, offset, rate_limiter)
        
        return response

class RateLimiter:
    def __init__(self, rate):
        self.rate = rate
        self.min_interval = 1 / rate
        self.last_call = time.time()

    def acquire(self):
        elapsed = time.time() - self.last_call
        wait_time = self.min_interval - elapsed
        if wait_time > 0:
            time.sleep(wait_time)
        self.last_call = time.time()

class MiraklClientProvider:
    def __init__(self, marketplace_names: List[str], credential_callback: Callable[[str], Tuple[str, str]]):
        self.clients = {}
        for marketplace in marketplace_names:
            base_url, api_key = credential_callback(marketplace)
            self.clients[marketplace] = MiraklClient(marketplace, base_url=base_url, api_key=api_key)
    
    def get_client(self, marketplace: str) -> MiraklClient:
        return self.clients.get(marketplace)
