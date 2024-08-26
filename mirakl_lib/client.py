from dataclasses import dataclass
from enum import Enum
import json
import re
import time
from typing import Any, Callable, List, TypeVar, TypedDict, cast
import requests

from mirakl_lib.offer import OF21QueryParams, OF21Response, OF24Request
from mirakl_lib.public_input import OfferUpdateInput
from mirakl_lib.shipping import CarrierNotFound, OR23RequestBody, ShippingCarrier

from .order import MiraklOrder
from .response import OR11Response

F = TypeVar("F", bound=Callable[..., Any])


@dataclass
class GetOrdersResult:
    orders: List[MiraklOrder]
    has_more: bool
    next_order_start_offset: int


class ShippingConfirmationResult(Enum):
    CONFIRMED = "CONFIRMED"
    PREVIOUSLY_CONFIRMED = "PREVIOUSLY_CONFIRMED"


def round_up_to_nearest_nine(number: float) -> float:
    number = round(number, 2)
    base = int(number)
    mantissa = round((number - base) * 100)
    dist_to_next_nine = abs((mantissa % 10) - 9) * 0.01
    rounded_number = number + dist_to_next_nine
    return rounded_number


class CarrierConfig(TypedDict):
    shipping_carrier: ShippingCarrier
    marketplace_carrier_code: str


def generate_custom_tracking_url(carrier: ShippingCarrier, tracking_number: str) -> str:
    match (carrier):
        case ShippingCarrier.UPS:
            raise NotImplementedError
        case ShippingCarrier.USPS:
            raise NotImplementedError
        case ShippingCarrier.FEDEX:
            raise NotImplementedError
        case ShippingCarrier.DHL:
            return f"https://www.dhl.com/us-en/home/tracking.html?tracking-id={tracking_number}"
        case ShippingCarrier.CUSTOM:
            raise NotImplementedError


def determine_carrier(
    tracking_number: str, marketpace_order_number: str | None = None
) -> ShippingCarrier:
    if tracking_number.startswith("1Z"):
        return ShippingCarrier.UPS
    else:
        raise CarrierNotFound


def retry_wrapper(request_func: F) -> F:
    def wrapper(instance: "MiraklClient", *args, **kwargs):
        retry_count = 0
        max_retries = 10

        while retry_count < max_retries:

            try:
                request_func(instance, *args, **kwargs)
                break
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:
                    retry_after = int(e.response.headers.get("Retry-After", 2))
                    time.sleep(retry_after)
                    retry_count += 1
                else:
                    raise e

        if retry_count >= max_retries:
            raise Exception("Max retries exceeded")

    return cast(F, wrapper)


class MiraklClient:

    def __init__(
        self,
        marketplace: str,
        base_url: str | None = None,
        api_key: str | None = None,
        carrier_configurations: list[CarrierConfig] = [],
        tracking_url_generation_func: Callable[
            [ShippingCarrier, str], str
        ] = generate_custom_tracking_url,
        carrier_determination_func: Callable[
            [str, str | None], ShippingCarrier
        ] = determine_carrier,
    ):
        self.marketplace = marketplace
        self.base_url = base_url
        self.api_key = api_key
        self.carrier_configurations: dict[ShippingCarrier, CarrierConfig] = {
            config["shipping_carrier"]: config for config in carrier_configurations
        }
        self.tracking_url_generation_func = tracking_url_generation_func
        self.carrier_determination_func = carrier_determination_func

    def _default_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"{self.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    ##################################
    # ORDER MANAGEMENT #
    ##################################

    def get_orders(
        self,
        offset: int,
        size: int,
        status: str | None = None,
        order_ids: List[str] = [],
    ) -> GetOrdersResult:
        url = f"{self.base_url}/api/orders"

        params: dict[str, str | int] = {"offset": offset, "max": size}

        if order_ids:
            params["order_ids"] = ",".join(order_ids)  # type: ignore

        if status is not None:
            params["order_state_codes"] = status

        params_str = "&".join([f"{k}={v}" for k, v in params.items()])

        response = requests.get(url, params=params_str, headers=self._default_headers())

        if not response.ok:
            response.raise_for_status()

        response_json = response.json()

        # Deserialize the response JSON into an OR11Response object
        or11_response = OR11Response(
            orders=[
                MiraklOrder.model_validate(order) for order in response_json["orders"]
            ],
            total_count=response_json["total_count"],
        )

        has_more = or11_response.total_count > offset + size

        # Return the result
        return GetOrdersResult(
            orders=or11_response.orders,
            has_more=has_more,
            next_order_start_offset=offset + size,
        )

    def accept_order(self, order_id: str, order_line_ids: List[str]):
        url = f"{self.base_url}/api/orders/{order_id}/accept"

        headers = {
            "Authorization": f"{self.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        payload = {
            "order_lines": [{"accepted": True, "id": id} for id in order_line_ids]
        }

        response = requests.put(url, headers=headers, json=payload)

        if not response.ok:
            response.raise_for_status()

    ##################################
    # OFFER MANAGEMENT #
    ##################################

    def update_offers(self, input: list[OfferUpdateInput]) -> int:

        url = f"{self.base_url}/api/offers"

        request_model = OF24Request(offers=[])

        for offer_input in input:

            offer_request_model = OF24Request.Offer(
                price=round_up_to_nearest_nine(offer_input["base_price"]),
                shop_sku=offer_input["offer_sku"],
                product_id=offer_input["product_id"],
                quantity=offer_input["quantity"],
            )

            if "discount_price" in offer_input:

                start_date = offer_input.get("discount_start_date")
                end_date = offer_input.get("discount_end_date")

                offer_request_model.discount = OF24Request.Offer.Discount(
                    price=offer_input["discount_price"],
                )

                if start_date is not None:
                    offer_request_model.discount.start_date = start_date
                if end_date is not None:
                    offer_request_model.discount.end_date = end_date

            request_model.offers.append(offer_request_model)

        request_json_payload = request_model.validate_all_offers().model_dump()

        response = requests.post(
            url, headers=self._default_headers(), json=request_json_payload
        )

        if not response.ok:
            response.raise_for_status()

        return response.json().get("import_id", 0)

    def get_all_offers(self) -> list[OF21Response.Offer]:

        limit = 100
        current_offset = 0

        first_page = self.get_offers(OF21QueryParams(offset=current_offset, max=limit))

        offers = [offer for offer in first_page.offers]

        total_count = first_page.total_count

        while current_offset < total_count:
            current_offset += limit
            next_page = self.get_offers(
                OF21QueryParams(offset=current_offset, max=limit)
            )
            offers.extend(next_page.offers)

        return offers

    def get_offers(self, params: OF21QueryParams) -> OF21Response:

        url = f"{self.base_url}/api/offers"

        retry_count = 0
        max_retries = 10

        while retry_count < max_retries:

            response = requests.get(
                url, params=params.to_dict(), headers=self._default_headers()
            )

            retry_count += 1

            if response.ok:
                response_json = response.json()

                of21_response = OF21Response(
                    offers=[
                        OF21Response.Offer.model_validate(offer)
                        for offer in response_json["offers"]
                    ],
                    total_count=response_json["total_count"],
                )

                return of21_response

            elif response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 2))
                time.sleep(retry_after)
            else:
                response.raise_for_status()

        raise Exception("This code should be unreachable")

    ##################################
    # SHIPPING/TRACKING MANAGEMENT #
    ##################################

    @retry_wrapper
    def put_tracking(
        self,
        order_id: str | int,
        tracking_number: str,
        carrier: ShippingCarrier | None = None,
    ) -> None:

        if type(order_id) is int:
            order_id = str(order_id)

        url = f"{self.base_url}/api/orders/{order_id}/tracking"

        if carrier is None:
            carrier = self.carrier_determination_func(tracking_number, tracking_number)

        request_payload: OR23RequestBody | None = None

        if carrier in self.carrier_configurations:
            marketplace_carrier_code = self.carrier_configurations[carrier][
                "marketplace_carrier_code"
            ]
            request_payload = OR23RequestBody(
                carrier_code=marketplace_carrier_code,
                tracking_number=tracking_number,
            )
        else:
            request_payload = OR23RequestBody(
                carrier_name=carrier.value,
                carrier_url=self.tracking_url_generation_func(carrier, tracking_number),
                tracking_number=tracking_number,
            )

        request_payload_json = request_payload.validate_for_mirakl().model_dump(
            exclude_none=True
        )

        response = requests.put(
            url, headers=self._default_headers(), json=request_payload_json
        )

        if not response.ok:
            response.raise_for_status()

    @retry_wrapper
    def put_ship_confirmation(self, order_id: str | int) -> ShippingConfirmationResult:
        if type(order_id) is int:
            order_id = str(order_id)

        url = f"{self.base_url}/api/orders/{order_id}/ship"

        response = requests.put(url, headers=self._default_headers())

        if response.ok:
            return ShippingConfirmationResult.CONFIRMED

        message = json.loads(response.content).get("message")
        pattern = r"Current status is"
        match = re.search(pattern, message)
        if match:
            return ShippingConfirmationResult.PREVIOUSLY_CONFIRMED

        response.raise_for_status()

        raise Exception("This code should be unreachable, here to make mypy happy.")


class MarketplaceConfig(TypedDict):
    base_url: str
    api_key: str


CustomTrackingUrlFunc = Callable[[ShippingCarrier, str], str]
CustomCarrierDeterminationFunc = Callable[[str, str | None], ShippingCarrier]


class MiraklClientProvider:
    def __init__(
        self,
        marketplace_names: List[str],
        marketplace_config: dict[str, MarketplaceConfig],
        configured_carriers_config: dict[str, list[CarrierConfig]] = {},
        custom_tracking_url_generation_config: dict[str, CustomTrackingUrlFunc] = {},
        custom_carrier_determination_config: dict[
            str, CustomCarrierDeterminationFunc
        ] = {},
    ):
        self.clients: dict[str, MiraklClient] = {}

        for marketplace in marketplace_names:
            config = marketplace_config[marketplace]
            base_url, api_key = (config["base_url"], config["api_key"])
            self.clients[marketplace] = MiraklClient(
                marketplace,
                base_url=base_url,
                api_key=api_key,
                carrier_configurations=configured_carriers_config.get(marketplace, []),
            )
            if marketplace in custom_tracking_url_generation_config:
                self.clients[marketplace].tracking_url_generation_func = (
                    custom_tracking_url_generation_config[marketplace]
                )
            if marketplace in custom_carrier_determination_config:
                self.clients[marketplace].carrier_determination_func = (
                    custom_carrier_determination_config[marketplace]
                )

    def get_client(self, marketplace: str) -> MiraklClient | None:
        return self.clients.get(marketplace)
