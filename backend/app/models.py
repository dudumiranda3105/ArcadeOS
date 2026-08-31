from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Telemetry(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    device_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{0,39}$")
    temperature: float = Field(ge=-40, le=80, allow_inf_nan=False)
    humidity: float = Field(ge=0, le=100, allow_inf_nan=False)
    source: Literal["esp32-wokwi", "esp32-physical", "mqtt-simulator"]


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def thermal_status(temperature: float, warning: float, critical: float) -> str:
    if temperature >= critical:
        return "critical"
    if temperature >= warning:
        return "warning"
    return "normal"


def reading_is_fresh(reading: dict | None, seconds: int, now: datetime | None = None) -> bool:
    if not reading:
        return False
    age = ((now or utcnow()) - datetime.fromisoformat(reading["time"])).total_seconds()
    return 0 <= age <= seconds
