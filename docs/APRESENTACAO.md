# ArcadeOS — roteiro de apresentação

Entrega: 28/09. Duração sugerida: 6 a 8 minutos. Ajuste ao tempo informado pelo professor.

## 1. Problema (40 segundos)

“Escolhemos o universo dos fliperamas. Dentro de um gabinete, nem sempre é fácil acompanhar as condições do ar. O ArcadeOS centraliza temperatura, umidade e histórico para que o responsável perceba alterações e confira o equipamento.”

Explique que OS é a marca da aplicação Web. O sensor não lê diretamente a CPU e os limites usados são didáticos.

## 2. Proposta e arquitetura (1 minuto)

Mostre o fluxo: **DHT22 → ESP32 → MQTT/Mosquitto → Python → InfluxDB → API Python → Vue/Chart.js**.

Uma frase por camada:

- DHT22 faz a leitura e ESP32 publica uma mensagem JSON.
- Mosquitto distribui a mensagem no tópico assinado pelo Python.
- Python valida dispositivo, formato e limites físicos do sensor.
- InfluxDB persiste os valores com horário de recebimento.
- Vue consulta a API Python e Chart.js apresenta o histórico.

## 3. Dispositivo e comunicação (1 minuto)

Mostre o circuito no Wokwi, a ligação no GPIO4 e o monitor serial. Mostre o tópico `arcadeos/arcade-01/telemetry` e um payload. Identifique o processo Mosquitto e o log de conexão.

## 4. Demonstração ao vivo (2 minutos)

Use **Conexão IoT** e o ESP32/Wokwi, não apenas os dados fictícios:

1. 28 °C: normal.
2. 37 °C: atenção.
3. 42 °C: crítico.
4. Mostre a mesma origem `esp32-wokwi` no painel e as novas linhas no banco.

O gráfico agrega amostras por janelas; o indicador atual usa a última leitura bruta.

## 5. Persistência e histórico (1 minuto)

Abra Histórico, mude o período e exporte o CSV. Recarregue a aplicação para mostrar que as leituras permanecem. Se possível, reinicie o backend e consulte novamente o banco.

## 6. Evolução (40 segundos)

Para o 2º bimestre: sensores adicionais, controle de ventilação via MQTT bidirecional, banco relacional para equipamentos/usuários e Docker da aplicação completa. A primeira etapa apenas monitora.

## Checklist da avaliação

| Critério | Evidência para mostrar |
| --- | --- |
| Problema e solução (1,0) | Contexto de gabinete arcade e objetivo do monitoramento |
| Vue/TS/Vite (2,0) | Interface em funcionamento e arquivos de configuração |
| ESP32/Wokwi (1,5) | Circuito ativo, sensor alterado ao vivo e serial |
| MQTT/Mosquitto (2,0) | Broker ativo, tópico e mensagens recebidas pelo Python |
| Python (1,0) | Código de validação/ingestão e log de gravação |
| InfluxDB (1,5) | Leituras persistidas e consulta após recarregar/reiniciar |
| Dashboard (1,0) | Indicadores e gráfico mudando com o sensor |

Antes da apresentação: testar a rede do local, salvar o projeto Wokwi, publicar o código no GitHub, verificar credenciais e preparar um vídeo de apoio caso permitido. Um vídeo ou o modo fictício não garantem a pontuação do funcionamento ao vivo.
