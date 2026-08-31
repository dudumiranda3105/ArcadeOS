"""Teste opt-in com MQTT e InfluxDB REAIS. Publica 3 leituras mqtt-simulator."""
import json
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
import paho.mqtt.client as mqtt
from app.config import Settings


def get(path):
    with urllib.request.urlopen("http://127.0.0.1:8000/api" + path, timeout=10) as response:
        return json.load(response)


def main():
    settings = Settings()
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"arcadeos-integration-{time.time_ns()}")
    if settings.mqtt_username:
        client.username_pw_set(settings.mqtt_username, settings.mqtt_password)
    if settings.mqtt_tls:
        client.tls_set(ca_certs=settings.mqtt_ca_cert or None)
    client.connect(settings.mqtt_host, settings.mqtt_port, 30)
    client.loop_start()
    try:
        for temperature, expected in [(28.5, "normal"), (37.0, "warning"), (42.0, "critical")]:
            message = json.dumps({"device_id": settings.device_id, "temperature": temperature, "humidity": 47.0, "source": "mqtt-simulator"})
            published = client.publish(settings.topic, message, qos=1, retain=False)
            published.wait_for_publish(timeout=5)
            assert published.is_published(), "Broker não confirmou publicação"
            deadline = time.monotonic() + 12
            while time.monotonic() < deadline:
                state = get("/status")
                if state["latest"] and state["latest"]["temperature"] == temperature:
                    break
                time.sleep(0.25)
            else:
                raise AssertionError(f"Leitura {temperature} não chegou ao banco/API")
            assert state["thermal_status"] == expected
            assert state["influx_connected"] and state["mqtt_connected"] and state["online"]
            print(f"PASS MQTT -> Mosquitto -> Python -> InfluxDB -> API: {temperature} C / {expected}")
        for period in ["1h", "6h", "24h", "7d"]:
            data = get(f"/history?period={period}")
            assert data["statistics"]["count"] >= 3
            assert data["statistics"]["maximum"] >= 42
            assert data["readings"]
            print(f"PASS histórico {period}: {data['statistics']['count']} leituras brutas, {len(data['readings'])} amostras")
    finally:
        client.disconnect()
        client.loop_stop()


if __name__ == "__main__":
    main()
