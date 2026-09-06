#pragma once

// Copie secrets.example.h para secrets.h para usar credenciais privadas.
// secrets.h é ignorado pelo Git, mas projetos públicos no Wokwi expõem todos os arquivos.
#if __has_include("secrets.h")
#include "secrets.h"
#endif

#ifndef WIFI_SSID
#define WIFI_SSID "Wokwi-GUEST"
#endif
#ifndef WIFI_PASSWORD
#define WIFI_PASSWORD ""
#endif
#ifndef MQTT_HOST
// Broker Mosquitto público apenas para a apresentação com dados não sensíveis.
#define MQTT_HOST "test.mosquitto.org"
#endif
#ifndef MQTT_PORT
#define MQTT_PORT 1883
#endif
#ifndef MQTT_USERNAME
#define MQTT_USERNAME ""
#endif
#ifndef MQTT_PASSWORD
#define MQTT_PASSWORD ""
#endif
#ifndef MQTT_USE_TLS
#define MQTT_USE_TLS 0
#endif
#ifndef DEVICE_ID
#define DEVICE_ID "arcade-01"
#endif
#ifndef MQTT_TOPIC
// Sufixo aleatório reduz colisões no broker compartilhado; não é um segredo.
#define MQTT_TOPIC "arcadeos/a9f4c2d1/telemetry"
#endif
#ifndef TELEMETRY_SOURCE
#define TELEMETRY_SOURCE "esp32-wokwi"
#endif

// Com MQTT_USE_TLS=1, defina MQTT_ROOT_CA em secrets.h, conforme o exemplo.
