# ESP32 no Wokwi

## Usar no VS Code

Abra a pasta raiz `ArcadeOS` no VS Code. O arquivo `wokwi.toml` aponta para o firmware compilado pelo ambiente `esp32dev` do `platformio.ini`; o `diagram.json` da raiz contém o circuito ESP32 + DHT22.

1. Instale a extensão oficial **Wokwi Simulator** (`Wokwi.wokwi-vscode`).
2. Pressione F1 e execute **Wokwi: Request a new License**. A ativação ocorre no navegador; pode ser o Brave. Conclua a ativação pessoalmente e permita retornar ao VS Code. O uso depende de uma licença válida conforme as condições do Wokwi.
3. Execute **Wokwi: Start Simulator** pela paleta F1.
4. Inicie os serviços do ArcadeOS e selecione **Conexão IoT** no dashboard. Confirme uma leitura com origem `esp32-wokwi`; apenas compilar o firmware não valida o fluxo completo.

Os binários locais já foram compilados nesta máquina, mas `.pio` não é versionado. Em outra máquina, ou após alterar o código, compile novamente com PlatformIO (`pio run -e esp32dev`), preferencialmente em um ambiente separado do Python do backend. Se editar o circuito, mantenha os dois arquivos `diagram.json` sincronizados.

Documentação: [instalação e licença](https://docs.wokwi.com/vscode/getting-started) e [configuração do projeto](https://docs.wokwi.com/vscode/project-config).

## Criar o circuito

1. Crie um projeto ESP32 em [wokwi.com](https://wokwi.com/).
2. Copie `firmware/arcadeos/arcadeos.ino` para o `sketch.ino` do projeto.
3. Adicione `config.h`, `libraries.txt` e o conteúdo de `diagram.json`.
4. O código já está configurado para o caminho público abaixo; altere somente se optar pelo gateway privado ou broker próprio.
5. Inicie a simulação e abra o monitor serial.
6. Clique no DHT22 e altere temperatura/umidade. Uma leitura deve sair a cada 5 segundos.

| DHT22 | ESP32 |
| --- | --- |
| VCC | 3V3 |
| DATA/SDA | GPIO 4 |
| GND | GND |

O circuito inclui um resistor de 10k entre DATA e 3V3. O LED integrado no GPIO2 indica a tentativa bem-sucedida de publicação MQTT; não comprova a gravação no banco. Confira também o log do Python e o InfluxDB.

## Caminho recomendado para a apresentação: Mosquitto público

O firmware usa `test.mosquitto.org:1883` e o tópico `arcadeos/a9f4c2d1/telemetry`. No `backend/.env`, configure os mesmos valores em `MQTT_HOST`, `MQTT_PORT` e `MQTT_TOPIC`, depois reinicie o backend.

Esse broker é público, compartilhado e não oferece garantia de disponibilidade. Publique apenas temperatura e umidade simuladas, não use senhas nem informações pessoais e mantenha `retain=false`. O sufixo reduz colisões, mas não fornece privacidade. Faça um ensaio na mesma rede da apresentação e tenha o gateway privado como alternativa se disponível.

## Caminho alternativo A: gateway privado e broker local

Altere o firmware para `MQTT_HOST = host.wokwi.internal`, `MQTT_PORT = 1883`, sem TLS e sem senha. Isso é exclusivo do ambiente local de desenvolvimento.

1. Inicie o Mosquitto com `infra/mosquitto.conf`.
2. Execute e habilite o **Private Wokwi IoT Gateway** conforme a documentação oficial.
3. O gateway privado requer um plano compatível do Wokwi; não há assinatura inclusa neste projeto.
4. Inicie o ESP32. O serial deve mostrar “Conectado ao Mosquitto”.
5. Abra o dashboard em **Conexão IoT** e confirme a origem `esp32-wokwi` em Meu arcade.

O gateway público não tem acesso a `localhost`, `127.0.0.1` ou serviços da sua rede local. Trocar apenas o endereço do firmware por seu IP local não resolve essa restrição.

## Caminho alternativo B: Mosquitto remoto protegido

Pode ser usado com o gateway público. Você precisa de um servidor autorizado pelo grupo/professor com acesso TCP ao Mosquitto.

1. Instale Mosquitto no servidor, configure domínio e certificado TLS válido.
2. Adapte `infra/mosquitto-remote.example.conf`. Crie dois usuários com `mosquitto_passwd`: `arcade-device` e `arcade-backend`.
3. Instale a ACL de `infra/arcadeos.acl`. O dispositivo apenas publica; o backend apenas assina.
4. Abra somente a porta MQTT TLS necessária (normalmente 8883) no servidor. Não exponha InfluxDB nem seu painel administrativo.
5. Copie `secrets.example.h` para `secrets.h` no projeto do ESP32 e preencha host, credenciais temporárias e certificado CA verdadeiro.
6. No `backend/.env`, configure o mesmo host, porta 8883, `MQTT_TLS=true` e as credenciais de `arcade-backend`.
7. Para uma CA privada, configure `MQTT_CA_CERT` no Python e o mesmo certificado raiz no firmware.

O firmware não usa `setInsecure()`: ele verifica o certificado. O relógio é sincronizado por NTP para TLS. Erros de DNS, firewall, horário e cadeia de certificados podem impedir a conexão; veja o monitor serial.

**Segurança:** `secrets.h` é ignorado no Git local, mas isso não protege um projeto público do Wokwi. Não copie credenciais permanentes para uma simulação pública. Use acesso temporário e restrito ao tópico, evite dados sensíveis, revogue as credenciais após a apresentação. O gateway público é um serviço de terceiros.

## ESP32 físico

Configure Wi-Fi em `secrets.h`, use `TELEMETRY_SOURCE="esp32-physical"` e aponte para o Mosquitto acessível na rede. A configuração local em loopback não aceita conexões de outro dispositivo. Para uma LAN, configure listener autenticado, ACL e TLS conforme o ambiente; não exponha um listener anônimo na rede.

O DHT22 deve ficar no ar do gabinete, longe do contato com circuitos ou partes quentes. Não conecte o ESP32 a tensão de rede ou à fonte do arcade sem projeto elétrico apropriado. Esta entrega funciona integralmente por simulação.

## Ensaio de avaliação

1. Inicie todos os serviços e use o modo **Conexão IoT**, não a demonstração visual.
2. Ajuste o DHT22 para 28 °C. Confira o payload no serial, gravação no log Python e leitura no dashboard.
3. Mude para 37 °C e depois 42 °C. Aguarde as leituras e mostre os estados de atenção e crítico.
4. Consulte o histórico, altere o período e exporte o CSV.
5. Pare o Wokwi. Após 30 segundos, confirme “Offline”.
6. Recarregue o dashboard ou reinicie somente o backend: o histórico deve continuar no InfluxDB.
7. Mostre o projeto salvo no Wokwi e o repositório GitHub do grupo.

Referências: [rede ESP32 no Wokwi](https://docs.wokwi.com/guides/esp32-wifi), [DHT22](https://docs.wokwi.com/parts/wokwi-dht22), [Mosquitto.conf](https://mosquitto.org/man/mosquitto-conf-5.html).
