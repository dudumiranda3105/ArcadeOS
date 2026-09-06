import pytest
from pydantic import ValidationError

from app.config import Settings


def test_custom_mqtt_topic():
    settings = Settings(_env_file=None, mqtt_topic="arcadeos/a9f4c2d1/telemetry")
    assert settings.topic == "arcadeos/a9f4c2d1/telemetry"


@pytest.mark.parametrize("topic", ["arcadeos/+/telemetry", "arcadeos/#", " espaço "])
def test_subscription_wildcards_and_spaces_are_rejected(topic):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, mqtt_topic=topic)
