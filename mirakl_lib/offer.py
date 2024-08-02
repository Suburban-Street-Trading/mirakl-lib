from pydantic import BaseModel

from mirakl_lib.common import PaginationQueryParams


class OF21QueryParams(PaginationQueryParams):
    offer_state_codes: str | None = None
    sku: str | None = None
    product_id: str | None = None
    favorite: bool | None = None
    pricing_channel_code: str | None = None
    shop_id: int | None = None


class OF21Response(BaseModel):

    offers: list["Offer"]
    total_count: int

    class Offer(BaseModel):
        active: bool
        all_price: list["AllPrices"] | None = None
        allow_quote_requests: bool | None
        applicable_pricing: "ApplicablePricing"
        available_end_date: str | None = None
        available_start_date: str | None = None
        category_code: str
        category_label: str
        channels: list[str]
        currency_code: str | None = None
        description: str | None = None
        discount: "Discount | None"
        inactivity_reasons: list[str] | None
        internal_description: str | None = None
        leadtime_to_ship: int
        max_order_quantity: int | None = None
        min_order_quantity: int | None = None
        min_quantity_alert: int | None = None
        min_shipping_price: float
        min_shipping_price_additional: float
        offer_id: int
        package_quantity: int | None = None
        price: float
        product_brand: str | None
        product_description: str | None
        product_sku: str
        product_tax_code: str | None = None
        product_title: str
        quantity: int
        shipping_deadline: str | None
        shop_sku: str
        state_code: str
        total_price: float

        class AllPrices(BaseModel):
            channel_code: str | None
            context: dict | None
            discount_end_date: str | None
            discount_start_date: str | None
            price: float
            unit_discount_price: float | None
            unit_origin_price: float | None

        class ApplicablePricing(BaseModel):
            channel_code: str | None
            discount_end_date: str | None
            discount_start_date: str | None
            price: float
            unit_discount_price: float | None
            unit_origin_price: float

        class Discount(BaseModel):
            end_date: str | None
            start_date: str | None
            discount_price: float | None
            origin_price: float | None


class OF24Request(BaseModel):

    offers: list["Offer"]

    class Offer(BaseModel):

        allow_quote_requests: bool = False
        available_ended: str | None = None
        available_started: str | None = None
        description: str | None = None
        discount: "Discount | None" = None
        internal_description: str | None = None
        leadtime_to_ship: int | None = None
        logistic_class: str | None = None
        max_order_quanitty: int | None = None
        min_order_quantity: int | None = None
        min_quantity_alert: int | None = None
        package_quantity: int | None = None
        price: float
        pricing_unit: str | None = None
        product_id: str
        product_id_type: str
        product_tax_code: str = "P0000000"
        quantity: int = 0
        shop_sku: str
        state_code: str
        update_delete: str = "update"

        class AllPrices(BaseModel):
            channel_code: str | None = None
            discount_end_date: str | None = None
            discount_start_date: str | None = None
            unit_discount_price: float | None = None
            unit_origin_price: float | None = None

        class Discount(BaseModel):
            end_date: str | None = None
            start_date: str | None = None
            price: float | None = None
