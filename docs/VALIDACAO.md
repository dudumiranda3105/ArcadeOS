# Validação da primeira versão

Verificação em 31/08/2026, Windows, Python 3.12, Node 24.

## Executado com sucesso

- `pnpm build`: verificação TypeScript/Vue e build de produção do frontend.
- 18 testes automatizados Python: formato e faixa das leituras, NaN, tópico/dispositivo incompatíveis, retenção MQTT, falha de persistência, timeout, limites inclusivos, consultas e indisponibilidade do banco.
- Mosquitto **2.1.2 real**, executado localmente em `127.0.0.1:1883`.
- InfluxDB **2.9.1 real**, executado em `127.0.0.1:8086`, bucket `telemetry` com retenção de 30 dias.
- Conta local InfluxDB e token restrito à leitura/escrita no bucket; credenciais fora do Git.
- Teste de integração publicando 28,5 °C, 37 °C e 42 °C: mensagens percorreram MQTT → Mosquitto → Python → InfluxDB → API, com estados normal, atenção e crítico.
- Consulta dos quatro períodos: 1h, 6h, 24h e 7d; pico de 42 °C preservado nas estatísticas brutas mesmo com agregação do gráfico.
- Sensor marcado offline após mais de 30 segundos sem novas leituras.
- Persistência confirmada após reinício do backend e dos serviços: as três leituras originais e o pico de 42 °C continuaram disponíveis.
- Frontend respondendo HTTP 200 e proxy `/api/health` chegando ao Python.
- Acesso HTTP a `.runtime/local-access.txt` negado pelo Vite com 403.
- Credenciais, ferramentas, banco e ambiente Python excluídos pelo `.gitignore`.
- Inicializador `start-local.ps1` executado com os cinco processos (Mosquitto, InfluxDB, Python, Vite e simulador); segunda execução preservou os serviços existentes, sem duplicá-los.

Os testes de integração usam `source: mqtt-simulator`. São mensagens MQTT reais de um publicador Python, **não dados de um ESP32**.

## Firmware e configuração Wokwi em 06/09/2026

- Circuito montado na interface do Wokwi com ESP32 DevKit, DHT22 no GPIO4 e resistor de 10k.
- Bibliotecas adicionadas no Library Manager: DHT sensor library 1.4.6, Adafruit Unified Sensor 1.1.15 e PubSubClient 2.8.
- Código configurado para `Wokwi-GUEST`, `test.mosquitto.org:1883` e tópico `arcadeos/a9f4c2d1/telemetry`.
- Backend conectado ao mesmo broker/tópico; InfluxDB e API locais disponíveis.
- Compilação local do mesmo firmware aprovada pelo PlatformIO: ESP32 Arduino, 44.768 bytes de RAM (13,7%) e 732.709 bytes de flash (55,9%).
- Build final criado com sucesso; `.pio/` está fora do Git.

## Fluxo completo validado no Wokwi para VS Code em 06/09/2026

- Extensão oficial Wokwi 3.7.0 instalada e licença ativada pelo usuário.
- Simulação executada usando `wokwi.toml`, `diagram.json` e firmware compilado localmente.
- Monitor serial confirmou conexão MQTT e publicação com origem `esp32-wokwi`.
- Leituras de 28 °C e 47% chegaram ao Python e ao InfluxDB, sem falhas de escrita.
- Temperatura alterada no DHT22 para 46,9 °C: API e dashboard em **Conexão IoT** mostraram estado crítico, sensor online e pico de 46,9 °C.
- Histórico de 1h confirmou a sequência de 28 °C para 46,9 °C persistida com origem `esp32-wokwi`.
- Fluxo: ESP32 simulado → MQTT → Mosquitto público (`test.mosquitto.org`) → Python local → InfluxDB local → Vue. O broker público é compartilhado e sem garantia de disponibilidade.

## Ainda depende de validação externa

- Firmware ESP32, `diagram.json`, bibliotecas e instruções completos em `firmware/arcadeos/` e `docs/WOKWI.md`.
- A primeira compilação no site retornou “Build Servers Busy”; a segunda ainda aguardava compilação ao encerrar aquele ensaio. A simulação foi depois validada no VS Code, conforme acima.
- O projeto do site não foi salvo na conta; a versão funcional está na pasta local para uso no VS Code.
- TLS remoto e caminho do gateway privado não foram testados; a simulação validada usa o broker público.
- ESP32 físico não conectado nem testado.
- GitHub: publicado em 08/09/2026 em `https://github.com/dudumiranda3105/ArcadeOS`, branch `main`. Envio confirmado comparando o SHA local com o remoto.
- Docker Compose fornecido como alternativa, mas não executado; Docker Desktop não está instalado neste ambiente.
- Dashboard inspecionado no navegador com leitura do Wokwi e estado crítico; ainda não foi realizada uma bateria completa de testes em desktop/celular.

## Limitações conscientes da etapa

- Um único gabinete; sem cadastro de usuários/equipamentos.
- Sem autenticação Web; serviços locais somente em loopback.
- Sem controle de atuadores nesta entrega.
- Alertas visuais por limites didáticos, sem notificação externa.
- Fila de ingestão não durável; falhas no banco podem perder leituras, e são contabilizadas.
- CSV e eventos na tela derivam da amostragem do gráfico, não de um registro completo de alarmes.
- O modo de demonstração visual roda só no navegador e não comprova os requisitos MQTT, ESP32 ou persistência.

Antes da avaliação, execute o roteiro em `docs/APRESENTACAO.md` com o ESP32/Wokwi e **Conexão IoT**.
