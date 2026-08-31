import logging
import queue
import threading

import paho.mqtt.client as mqtt
from pydantic import ValidationError

from .config import Settings
from .models import Telemetry, utcnow
from .storage import InfluxRepository

logger = logging.getLogger("arcadeos.ingestion")


class Ingestor:
    def __init__(self, settings: Settings, repository: InfluxRepository):
        self.settings = settings
        self.repository = repository
        self.lock = threading.Lock()
        self.state = {
            "mqtt_connected": False, "received": 0, "rejected": 0,
            "write_failures": 0, "last_error": None,
        }
        self.pending: queue.Queue = queue.Queue(maxsize=500)
        self.stopped = threading.Event()
        self.worker = threading.Thread(target=self._consume, daemon=True, name="influx-writer")
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=settings.mqtt_client_id)
        if settings.mqtt_username:
            self.client.username_pw_set(settings.mqtt_username, settings.mqtt_password)
        if settings.mqtt_tls:
            self.client.tls_set(ca_certs=settings.mqtt_ca_cert or None)
        self.client.reconnect_delay_set(min_delay=1, max_delay=30)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_connect_fail = self._on_connect_fail
        self.client.on_message = self._on_message

    def snapshot(self) -> dict:
        with self.lock:
            return dict(self.state)

    def _update(self, **values):
        with self.lock:
            self.state.update(values)

    def _increment(self, key: str):
        with self.lock:
            self.state[key] += 1

    def start(self):
        self.worker.start()
        self.client.connect_async(self.settings.mqtt_host, self.settings.mqtt_port, keepalive=30)
        self.client.loop_start()

    def stop(self):
        self.client.disconnect()
        self.client.loop_stop()
        self.stopped.set()
        self.worker.join(timeout=7)

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        connected = reason_code == 0
        self._update(mqtt_connected=connected)
        if connected:
            client.subscribe(self.settings.topic, qos=1)
            logger.info("MQTT conectado. Assinatura: %s", self.settings.topic)
        else:
            self._update(last_error="Mosquitto recusou a conexão. Confira usuário e senha.")

    def _on_disconnect(self, client, userdata, flags, reason_code, properties):
        self._update(mqtt_connected=False)

    def _on_connect_fail(self, client, userdata):
        self._update(mqtt_connected=False, last_error="Não foi possível conectar ao Mosquitto.")

    def validate(self, topic: str, payload: bytes, retained: bool = False) -> Telemetry:
        if retained:
            raise ValueError("Telemetria retida não representa uma leitura nova.")
        if topic != self.settings.topic or len(payload) > 2048:
            raise ValueError("Tópico ou tamanho de mensagem inválido.")
        telemetry = Telemetry.model_validate_json(payload)
        if telemetry.device_id != self.settings.device_id:
            raise ValueError("O dispositivo do payload não corresponde ao tópico.")
        return telemetry

    def _on_message(self, client, userdata, message):
        try:
            telemetry = self.validate(message.topic, message.payload, message.retain)
            self.pending.put_nowait((telemetry, utcnow()))
        except (ValueError, ValidationError, queue.Full):
            self._increment("rejected")
            logger.warning("Mensagem rejeitada: formato, dispositivo, retenção ou fila inválidos.")

    def persist(self, telemetry, received_at):
        try:
            self.repository.write(telemetry, received_at)
            self._increment("received")
            self._update(last_error=None)
            logger.info("Leitura persistida: %s %.1f °C / %.1f %%", telemetry.device_id, telemetry.temperature, telemetry.humidity)
        except Exception:
            # Never log a raw upstream exception: it could contain a token or URL.
            self._increment("write_failures")
            self._update(last_error="Falha ao gravar no InfluxDB. Esta leitura não foi persistida.")
            logger.error("InfluxDB indisponível ou sem permissão de escrita.")

    def _consume(self):
        while not self.stopped.is_set():
            try:
                telemetry, received_at = self.pending.get(timeout=0.2)
            except queue.Empty:
                continue
            try:
                self.persist(telemetry, received_at)
            finally:
                self.pending.task_done()
