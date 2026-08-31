#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <DHT.h>
#include "config.h"

// DHT22: VCC -> 3V3, DATA -> GPIO4, GND -> GND.
// Hardware físico: resistor de pull-up de 10k entre DATA e 3V3.
DHT dht(4, DHT22);
#if MQTT_USE_TLS
WiFiClientSecure network;
#else
WiFiClient network;
#endif
PubSubClient mqtt(network);
unsigned long lastReading = 0;
unsigned long lastAttempt = 0;
String topic = String("arcadeos/") + DEVICE_ID + "/telemetry";
String clientId;

void setup() {
  Serial.begin(115200);
  dht.begin();
  pinMode(2, OUTPUT);
  clientId = String("arcadeos-") + DEVICE_ID + "-" + String((uint32_t)ESP.getEfuseMac(), HEX);
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
#if MQTT_USE_TLS
  // Nunca use setInsecure(): configure a CA que assina o broker.
  network.setCACert(MQTT_ROOT_CA);
  configTime(0, 0, "pool.ntp.org", "time.nist.gov");
#endif
  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  mqtt.setKeepAlive(30);
  mqtt.setSocketTimeout(3);
  mqtt.setBufferSize(512);
  Serial.println("ArcadeOS iniciando. Aguardando Wi-Fi e Mosquitto...");
}

void loop() {
  const unsigned long now = millis();
  if (WiFi.status() != WL_CONNECTED) {
    digitalWrite(2, LOW);
    delay(20);
    return;
  }
  if (!mqtt.connected()) {
    digitalWrite(2, LOW);
    if (now - lastAttempt >= 3000) {
      lastAttempt = now;
      bool connected = strlen(MQTT_USERNAME) > 0
        ? mqtt.connect(clientId.c_str(), MQTT_USERNAME, MQTT_PASSWORD)
        : mqtt.connect(clientId.c_str());
      if (connected) Serial.println("Conectado ao Mosquitto.");
      else Serial.printf("Falha MQTT: %d. Nova tentativa em 3s.\n", mqtt.state());
    }
    delay(10);
    return;
  }
  mqtt.loop();
  if (now - lastReading >= 5000) {
    lastReading = now;
    const float temperature = dht.readTemperature();
    const float humidity = dht.readHumidity();
    if (isnan(temperature) || isnan(humidity)) {
      Serial.println("Leitura inválida do DHT22. Nenhum dado foi enviado.");
      return;
    }
    char payload[220];
    snprintf(payload, sizeof(payload),
      "{\"device_id\":\"%s\",\"temperature\":%.1f,\"humidity\":%.1f,\"source\":\"%s\"}",
      DEVICE_ID, temperature, humidity, TELEMETRY_SOURCE);
    // PubSubClient publica em QoS 0. retain=false evita marcar leituras antigas como novas.
    bool sent = mqtt.publish(topic.c_str(), payload, false);
    digitalWrite(2, sent ? HIGH : LOW);
    Serial.printf("%s %s\n", sent ? "Enviado:" : "Falha ao enviar:", payload);
  }
  delay(10);
}
