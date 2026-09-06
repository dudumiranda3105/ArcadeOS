from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[1] / ".env",
        env_file_encoding="utf-8", extra="ignore",
    )
    mqtt_host: str = "127.0.0.1"
    mqtt_port: int = Field(default=1883, ge=1, le=65535)
    mqtt_username: str = ""
    mqtt_password: str = ""
    mqtt_tls: bool = False
    mqtt_ca_cert: str = ""
    mqtt_client_id: str = "arcadeos-backend"
    mqtt_topic: str = Field(default="", max_length=160, pattern=r"^[A-Za-z0-9_/-]*$")
    influx_url: str = "http://127.0.0.1:8086"
    influx_token: str = ""
    influx_org: str = "arcadeos"
    influx_bucket: str = "telemetry"
    device_id: str = Field(default="arcade-01", pattern=r"^[a-z0-9][a-z0-9_-]{0,39}$")
    device_name: str = "Player One"
    device_location: str = "Gabinete principal"
    warning_temperature: float = Field(default=35, ge=-40, le=80, allow_inf_nan=False)
    critical_temperature: float = Field(default=40, ge=-40, le=80, allow_inf_nan=False)
    stale_after_seconds: int = Field(default=30, ge=10, le=3600)
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    @model_validator(mode="after")
    def valid_limits(self):
        if self.warning_temperature >= self.critical_temperature:
            raise ValueError("O limite de atenção deve ser menor que o limite crítico.")
        if self.mqtt_password and not self.mqtt_username:
            raise ValueError("MQTT_PASSWORD exige MQTT_USERNAME.")
        return self

    @property
    def topic(self) -> str:
        return self.mqtt_topic or f"arcadeos/{self.device_id}/telemetry"

    def public_device(self) -> dict:
        return {
            "id": self.device_id, "name": self.device_name,
            "location": self.device_location, "sensor": "ESP32 + DHT22",
            "warning_temperature": self.warning_temperature,
            "critical_temperature": self.critical_temperature,
            "stale_after_seconds": self.stale_after_seconds,
        }
