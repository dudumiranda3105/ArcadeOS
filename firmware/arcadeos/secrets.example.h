#pragma once

// Exemplo para um Mosquitto remoto protegido. Não contém credenciais reais.
#define MQTT_HOST "mqtt.seu-dominio.example"
#define MQTT_PORT 8883
#define MQTT_USERNAME "arcade-device"
#define MQTT_PASSWORD "substitua-por-uma-senha-temporaria"
#define MQTT_USE_TLS 1
#define MQTT_TOPIC "arcadeos/seu-topico-exclusivo/telemetry"
// Cole o certificado PEM real da autoridade certificadora do seu broker.
#define MQTT_ROOT_CA "-----BEGIN CERTIFICATE-----\nSUBSTITUA\n-----END CERTIFICATE-----\n"

// Para ESP32 físico, configure o Wi-Fi e altere a origem:
// #define WIFI_SSID "sua-rede"
// #define WIFI_PASSWORD "sua-senha"
// #define TELEMETRY_SOURCE "esp32-physical"
