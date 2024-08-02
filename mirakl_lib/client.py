from dataclasses import dataclass
import time
from typing import Callable, List, Tuple, TypedDict
import requests

from mirakl_lib.offer import OF21QueryParams, OF21Response
from mirakl_lib.shipping import CarrierNotFound, OR23RequestBody, ShippingCarrier

from .order import MiraklOrder
from .response import OR11Response


@dataclass
class GetWaitingOrdersResult:
    orders: List[MiraklOrder]
    has_more: bool
    next_order_start_offset: int


def round_up_to_nearest_nine(number: float) -> float:
    number = round(number, 2)
    base = int(number)
    mantissa = round((number - base) * 100)
    dist_to_next_nine = abs((mantissa % 10) - 9) * 0.01
    rounded_number = number + dist_to_next_nine
    return rounded_number


class CarrierConfiguration(TypedDict):
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


def determine_carrier(tracking_number: str) -> ShippingCarrier:
    if tracking_number.startswith("1Z"):
        return ShippingCarrier.UPS
    else:
        raise CarrierNotFound


class MiraklClient:

    def __init__(
        self,
        marketplace: str,
        base_url: str | None = None,
        api_key: str | None = None,
        carrier_configurations: list[CarrierConfiguration] = [],
        tracking_url_generation_func: Callable[
            [ShippingCarrier, str], str
        ] = generate_custom_tracking_url,
        carrier_determination_func: Callable[
            [str], ShippingCarrier
        ] = determine_carrier,
    ):
        self.marketplace = marketplace
        self.base_url = base_url
        self.api_key = api_key
        self.carrier_configurations: dict[ShippingCarrier, CarrierConfiguration] = {
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
    ) -> GetWaitingOrdersResult:
        url = f"{self.base_url}/api/orders"

        params: dict[str, str | int] = {"offset": offset, "max": size}

        if order_ids:
            params["order_ids"] = ",".join(order_ids)  # type: ignore

        if status is not None:
            params["order_state_codes"] = status

        params_str = "&".join([f"{k}={v}" for k, v in params.items()])

        response = requests.get(url, params=params_str, headers=self._default_headers())

        if response.ok:
            response_json = response.json()

            # Deserialize the response JSON into an OR11Response object
            or11_response = OR11Response(
                orders=[
                    MiraklOrder.model_validate(order)
                    for order in response_json["orders"]
                ],
                total_count=response_json["total_count"],
            )

            has_more = or11_response.total_count > offset + size

            # Return the result
            return GetWaitingOrdersResult(
                orders=or11_response.orders,
                has_more=has_more,
                next_order_start_offset=offset + size,
            )
        else:
            response.raise_for_status()

        raise Exception("This code should be unreachable")

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

    def update_offers(self):
        raise NotImplementedError

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

    def put_tracking(self, order_id: str | int, tracking_number: str) -> None:

        if type(order_id) is int:
            order_id = str(order_id)

        url = f"{self.base_url}/api/orders/{order_id}/tracking"

        carrier = self.carrier_determination_func(tracking_number)

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


class ConfiguredCarriersConfig(TypedDict):
    marketplace: str
    carriers: list[CarrierConfiguration]


class CustomTrackingUrlGenerationConfig(TypedDict):
    marketplace: str
    tracking_url_generation_func: Callable[[ShippingCarrier, str], str]


class CustomCarrierDeterminationConfig(TypedDict):
    marketplace: str
    carrier_determination_func: Callable[[str], ShippingCarrier]


class MiraklClientProvider:
    def __init__(
        self,
        marketplace_names: List[str],
        credential_callback: Callable[[str], Tuple[str, str]],
        configured_carriers_config: list[ConfiguredCarriersConfig] = [],
        custom_tracking_url_generation_config: list[
            CustomTrackingUrlGenerationConfig
        ] = [],
        custom_carrier_determination_config: list[
            CustomCarrierDeterminationConfig
        ] = [],
    ):
        self.clients: dict[str, MiraklClient] = {}

        carriers_config_lookup = {
            config["marketplace"]: config["carriers"]
            for config in configured_carriers_config
        }

        tracking_url_generation_lookup = {
            config["marketplace"]: config["tracking_url_generation_func"]
            for config in custom_tracking_url_generation_config
        }

        carrier_determination_lookup = {
            config["marketplace"]: config["carrier_determination_func"]
            for config in custom_carrier_determination_config
        }

        for marketplace in marketplace_names:
            base_url, api_key = credential_callback(marketplace)
            self.clients[marketplace] = MiraklClient(
                marketplace,
                base_url=base_url,
                api_key=api_key,
                carrier_configurations=carriers_config_lookup.get(marketplace, []),
            )
            if marketplace in tracking_url_generation_lookup:
                self.clients[marketplace].tracking_url_generation_func = (
                    tracking_url_generation_lookup[marketplace]
                )
            if marketplace in carrier_determination_lookup:
                self.clients[marketplace].carrier_determination_func = (
                    carrier_determination_lookup[marketplace]
                )

    def get_client(self, marketplace: str) -> MiraklClient | None:
        return self.clients.get(marketplace)
