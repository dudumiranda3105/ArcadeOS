"""Simulador auxiliar MQTT. Não substitui o ESP32/Wokwi exigido na avaliação."""
import argparse
import json
import math
import time

import paho.mqtt.client as mqtt

from app.config import Settings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=["normal", "warning", "critical", "cycle"], default="cycle")
    parser.add_argument("--count", type=int, default=0, help="0 = até Ctrl+C")
    parser.add_argument("--interval", type=float, default=5)
    args = parser.parse_args()
    if args.interval < 0.2 or args.count < 0:
        parser.error("Use intervalo >= 0.2s e count >= 0")
    settings = Settings()
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"arcadeos-test-{time.time_ns()}")
    if settings.mqtt_username:
        client.username_pw_set(settings.mqtt_username, settings.mqtt_password)
    if settings.mqtt_tls:
        client.tls_set(ca_certs=settings.mqtt_ca_cert or None)
    client.connect(settings.mqtt_host, settings.mqtt_port, 30)
    client.loop_start()
    index = 0
    print("SIMULADOR AUXILIAR: origem mqtt-simulator. Não é um ESP32.")
    try:
        while args.count == 0 or index < args.count:
            base = {"normal": 28.5, "warning": 36.5, "critical": 42.0}.get(args.scenario)
            temperature = (base if base is not None else 34.5 + math.sin(index / 5) * 8) + math.sin(index / 2) * 0.5
            payload = {"device_id": settings.device_id, "temperature": round(temperature, 1), "humidity": round(47 + math.sin(index / 4) * 3, 1), "source": "mqtt-simulator"}
            info = client.publish(settings.topic, json.dumps(payload), qos=1, retain=False)
            info.wait_for_publish(timeout=5)
            if not info.is_published():
                raise RuntimeError("Publicação MQTT não confirmada")
            print(json.dumps(payload))
            index += 1
            if args.count == 0 or index < args.count:
                time.sleep(args.interval)
    except KeyboardInterrupt:
        print("Simulação encerrada.")
    finally:
        client.disconnect()
        client.loop_stop()


if __name__ == "__main__":
    main()
