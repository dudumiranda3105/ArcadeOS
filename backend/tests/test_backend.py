import json
from datetime import timedelta
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings
from app.ingestion import Ingestor
from app.main import create_app
from app.models import Telemetry, reading_is_fresh, thermal_status, utcnow


class FakeRepository:
    def __init__(self):
        self.rows = []
        self.fail = False

    def write(self, telemetry, received_at):
        if self.fail:
            raise RuntimeError("private upstream error")
        self.rows.append({"time": received_at.isoformat(), "temperature": telemetry.temperature, "humidity": telemetry.humidity, "source": telemetry.source})

    def latest(self):
        if self.fail:
            raise RuntimeError("private upstream error")
        return self.rows[-1] if self.rows else None

    def history(self, period):
        if self.fail:
            raise RuntimeError("private upstream error")
        return {"period": period, "readings": self.rows}


@pytest.fixture
def settings():
    return Settings(_env_file=None, device_id="arcade-01")


@pytest.fixture
def payload():
    return {"device_id": "arcade-01", "temperature": 28.5, "humidity": 47.0, "source": "esp32-wokwi"}


@pytest.mark.parametrize("field,value", [("temperature", 81), ("temperature", -41), ("temperature", float("nan")), ("humidity", 101), ("humidity", -1), ("temperature", "28.5"), ("source", "fake-device")])
def test_rejects_invalid_sensor_data(payload, field, value):
    payload[field] = value
    with pytest.raises(ValidationError):
        Telemetry.model_validate(payload)


def test_rejects_wrong_device_topic_and_retained_data(settings, payload):
    worker = Ingestor(settings, FakeRepository())
    encoded = json.dumps(payload).encode()
    with pytest.raises(ValueError):
        worker.validate("arcadeos/another/telemetry", encoded)
    with pytest.raises(ValueError):
        worker.validate(settings.topic, encoded, retained=True)
    payload["device_id"] = "another"
    with pytest.raises(ValueError):
        worker.validate(settings.topic, json.dumps(payload).encode())


def test_malformed_mqtt_does_not_crash_callback(settings):
    worker = Ingestor(settings, FakeRepository())
    worker._on_message(None, None, SimpleNamespace(topic=settings.topic, payload=b"not json", retain=False))
    assert worker.snapshot()["rejected"] == 1
    assert worker.pending.empty()


def test_failed_write_is_not_reported_as_persisted(settings, payload):
    repo = FakeRepository()
    repo.fail = True
    worker = Ingestor(settings, repo)
    worker.persist(Telemetry.model_validate(payload), utcnow())
    assert worker.snapshot()["received"] == 0
    assert worker.snapshot()["write_failures"] == 1
    assert repo.rows == []
    repo.fail = False
    worker.persist(Telemetry.model_validate(payload), utcnow())
    assert worker.snapshot()["received"] == 1
    assert worker.snapshot()["last_error"] is None


def test_offline_after_timeout_and_rejects_future_reading():
    now = utcnow()
    assert reading_is_fresh({"time": (now - timedelta(seconds=29)).isoformat()}, 30, now)
    assert not reading_is_fresh({"time": (now - timedelta(seconds=31)).isoformat()}, 30, now)
    assert not reading_is_fresh({"time": (now + timedelta(seconds=1)).isoformat()}, 30, now)
    assert not reading_is_fresh(None, 30, now)


@pytest.mark.parametrize("temperature,expected", [(34.9, "normal"), (35, "warning"), (39.9, "warning"), (40, "critical")])
def test_threshold_boundaries(temperature, expected):
    assert thermal_status(temperature, 35, 40) == expected


def test_invalid_limits_rejected():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, warning_temperature=40, critical_temperature=35)


def test_api_uses_repository_and_handles_outages(settings, payload):
    repo = FakeRepository()
    repo.write(Telemetry.model_validate(payload), utcnow())
    with TestClient(create_app(settings, repo, start_mqtt=False)) as client:
        state = client.get("/api/status").json()
        assert state["online"] is True
        assert state["latest"]["temperature"] == 28.5
        assert state["influx_connected"] is True
        assert client.get("/api/history?period=24h").json()["readings"] == repo.rows
        assert client.get("/api/history?period=unsafe").status_code == 422
        repo.fail = True
        assert client.get("/api/history").status_code == 503
        state = client.get("/api/status").json()
        assert state["online"] is False
        assert state["influx_connected"] is False
        assert "private upstream error" not in json.dumps(state)


def test_empty_database_is_not_fabricated(settings):
    with TestClient(create_app(settings, FakeRepository(), start_mqtt=False)) as client:
        state = client.get("/api/status").json()
        assert state["latest"] is None
        assert state["online"] is False
