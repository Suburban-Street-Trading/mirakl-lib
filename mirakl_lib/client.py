from dataclasses import dataclass
from typing import Callable, List, Tuple
import requests

from .order import Customer, MiraklOrder, MiraklOrderLine, ShippingAddress
from .response import OR11Response
    
@dataclass
class GetWaitingOrdersResult:
    orders: List[MiraklOrder]
    has_more: bool
    next_order_start_offset: int
    
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
            order_lines=order['order_lines']
        )

    def get_bulk_order_ids(self, order_ids: List[str]) -> List[str]:
        # Chunk up the order ids into sub lists of size 100
        order_id_chunks = [order_ids[i:i+100] for i in range(0, len(order_ids), 100)]
        
        # Initialize an empty list to store the results
        all_orders = []
        
        # Iterate over the order id chunks
        for chunk in order_id_chunks:
            # Call get_orders with the chunk and size=100
            result = self.get_orders(offset=0, size=100, order_ids=chunk)
            
            # Append the orders from the result to the all_orders list
            [all_orders.append(order) for order in result.orders]
            
        # Create a single GetWaitingOrdersResult with all the orders
        return GetWaitingOrdersResult(
            orders=all_orders,
            has_more=False,
            next_order_start_offset=0
        )

    def get_orders(self, offset: int, size: int, status: str=None, order_ids: List[str]=None) -> GetWaitingOrdersResult:
        url = f"{self.base_url}/api/orders"
        
        params = {
            "offset": offset,
            "max": size
        }
        
        if order_ids:
            params['order_ids'] = ','.join(order_ids)
            
        if status is not None:
            params['order_state_codes'] = status
        
        headers = {
            "Authorization": f"{self.api_key}",
            "Accept": "application/json"
        }
        
        params_str = '&'.join([f"{k}={v}" for k, v in params.items()])

        response = requests.get(url, params=params_str, headers=headers)
        
        if response.ok:
            response_json = response.json()

            # Deserialize the response JSON into an OR11Response object
            or11_response = OR11Response(
                orders=[self._mirakl_order(order) for order in response_json['orders']],
                total_count=response_json['total_count'],
            )

            has_more = or11_response.total_count > offset + size

            # Return the result
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
        
        response = requests.put(
            url, 
            headers=headers,     
            json=payload
        )
        
        if not response.ok:
            response.raise_for_status()
    
    
    
class MiraklClientProvider:
    def __init__(self, marketplace_names: List[str], credential_callback: Callable[[str], Tuple[str, str]]):
        self.clients = {}
        for marketplace in marketplace_names:
            base_url, api_key = credential_callback(marketplace)
            self.clients[marketplace] = MiraklClient(marketplace, base_url=base_url, api_key=api_key)
    
    def get_client(self, marketplace: str) -> MiraklClient:
        return self.clients.get(marketplace)