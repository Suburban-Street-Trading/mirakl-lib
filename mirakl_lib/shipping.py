from enum import Enum

from pydantic import BaseModel
import validators  # type: ignore


class ShippingCarrier(Enum):
    UPS = "ups"
    USPS = "usps"
    FEDEX = "fedex"
    DHL = "dhl"
    CUSTOM = "custom"

    @classmethod
    def from_str(cls, value: str) -> "ShippingCarrier":
        match (value):
            case "ups":
                return cls.UPS
            case "usps":
                return cls.USPS
            case "fedex":
                return cls.FEDEX
            case "dhl":
                return cls.DHL
            case _:
                return cls.CUSTOM


class CarrierNotFound(Exception):
    pass


class OR23RequestBody(BaseModel):
    carrier_code: str | None = None
    carrier_name: str | None = None
    carrier_url: str | None = None
    tracking_number: str

    def validate_for_mirakl(self) -> "OR23RequestBody":
        if (
            self.carrier_code is None
            and self.carrier_name is None
            or self.carrier_url is None
        ):
            raise ValueError(
                "If carrier code is not provided, the BOTH carrier name and carrier url must be provided"
            )
        elif self.carrier_code is None:
            if not validators.url(self.carrier_url):
                raise ValueError("Invalid carrier URL")

        return self
