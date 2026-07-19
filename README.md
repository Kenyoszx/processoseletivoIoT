# Relatório Técnico
 
## Sistema de Monitoramento de Temperatura e Abertura de Porta
 
**Processo Seletivo – Intensivo Maker | IoT**
**Etapa Prática – Sistemas Embarcados**
 
---
 
### Identificação do Candidato
 
- **Nome completo:** João Victor de Souza Silva
- **GitHub:** kenyoszx
---
 
## 1. Visão Geral da Solução
 
Este projeto consiste em um sistema embarcado de monitoramento voltado para ambientes refrigerados, estufas ou painéis elétricos que exigem controle de qualidade e auditoria térmica. O objetivo central é acompanhar continuamente duas condições de risco: o tempo em que uma porta ou tampa permanece aberta e a ocorrência de variações bruscas de temperatura no ambiente monitorado.
 
O sistema foi desenvolvido em MicroPython para um microcontrolador ESP32 e simulado integralmente no ambiente Wokwi. Ele opera de forma autônoma, sem necessidade de intervenção do usuário durante a operação normal: a interação ocorre por meio de dois estímulos físicos simulados, a abertura ou o fechamento de uma porta (representada por um botão) e a variação de temperatura captada por um sensor. Sempre que uma condição de risco é detectada, o sistema emite um alerta pela porta serial. Quando as condições voltam a ser seguras, o sistema reporta a normalização do ambiente.
 
---
 
## 2. Arquitetura do Sistema Embarcado
 
O firmware foi estruturado em torno de um laço principal contínuo e não bloqueante, executado a cada cem milissegundos. Essa escolha foi fundamental para garantir que o sistema respondesse aos estímulos do simulador dentro da janela de tempo esperada pelos testes automatizados, já que qualquer função de espera bloqueante no código atrasaria a leitura dos sensores e comprometeria a sincronia com o ambiente de teste.
 
O diagrama abaixo resume os estados do sistema e as transições entre eles:
 
```
                    +---------------------------+
              +---->|          NORMAL           |<----+
              |     +---------------------------+     |
              |        |                    |          |
              |  porta aberta        delta T >= Y       |
              |  por >= tempo X      (com porta fechada) |
              |        |                    |          |
              |        v                    v          |
              |  +--------------+   +--------------------+
              |  | ALARME_PORTA |   |  ALARME_TERMICO    |
              |  +--------------+   +--------------------+
              |        |                    |
              |        +---------+----------+
              |                  |
              |   porta fechada E delta T < Y,
              |   estavel por ESTABILIZACAO_MS
              |                  |
              +------------------+
```
 
Ou seja: o sistema parte do estado normal e migra para um dos dois estados de alarme conforme a condição de risco correspondente é detectada. Os dois estados de alarme podem ocorrer de forma independente ou simultânea, e o retorno ao estado normal só acontece quando ambas as condições de risco deixam de estar presentes ao mesmo tempo, por um período contínuo mínimo.
 
### 2.1 Inicialização
 
Ao ligar, o microcontrolador configura a comunicação I2C com o sensor de temperatura, desperta o sensor do modo de repouso e inicializa a leitura do botão que representa o estado da porta. Em seguida, imprime uma mensagem de confirmação na porta serial, sinalizando que o sistema está pronto para operar.
 
### 2.2 Monitoramento do tempo de porta aberta
 
Quando a porta é detectada como aberta, o sistema registra o instante exato desse evento. A cada iteração do laço principal, o tempo decorrido desde a abertura é recalculado. Caso esse tempo ultrapasse o limite parametrizado, um alerta é emitido uma única vez, evitando repetições desnecessárias enquanto a condição de risco persiste.
 
### 2.3 Detecção de variação térmica
 
A detecção de variações bruscas de temperatura segue uma lógica de referência adaptativa. Enquanto o ambiente está estável e a porta permanece fechada, a temperatura atual é continuamente adotada como referência. Isso permite que o sistema acompanhe variações lentas e naturais do ambiente sem gerar falsos alarmes. No momento em que ocorre uma subida abrupta de temperatura, a diferença entre a leitura atual e a última referência estável ultrapassa o limite tolerado, e o alarme térmico é disparado imediatamente. Enquanto o alarme estiver ativo, a referência permanece congelada, preservando o registro do momento em que a anomalia começou.
 
### 2.4 Normalização
 
O retorno ao estado normal só ocorre quando as duas condições de segurança são satisfeitas ao mesmo tempo: a porta fechada e a temperatura dentro do gradiente aceitável. Para evitar que uma oscilação momentânea do sensor ou do botão gerasse uma normalização prematura, foi adicionado um pequeno período de estabilização: as condições seguras precisam se manter por um intervalo contínuo antes que o sistema declare a normalização. Essa decisão também se mostrou necessária durante os testes automatizados, pois evitou uma condição de corrida entre a impressão da mensagem de normalização e o momento em que o roteiro de teste começava a monitorar a porta serial.
 
---
 
## 3. Componentes Utilizados na Simulação
 
A simulação foi construída no Wokwi utilizando os seguintes componentes, definidos no arquivo `diagram.json`:
 
- Placa ESP32 DevKit C v4, responsável por executar o firmware MicroPython e realizar a comunicação serial com o ambiente de teste.
- Sensor MPU6050, conectado via barramento I2C, utilizado para a leitura da temperatura ambiente por meio do seu registrador interno de temperatura.
- Botão físico, conectado com resistor de pull-up interno, utilizado para simular o estado de abertura e fechamento da porta ou tampa monitorada.
A comunicação entre o microcontrolador e o computador de controle é feita por meio da porta serial, canal utilizado tanto para o envio das mensagens de status e alerta quanto para a validação automatizada dos cenários de teste.
 
---
 
## 4. Decisões Técnicas Relevantes
 
Algumas decisões de projeto merecem destaque por terem impacto direto na confiabilidade do sistema frente aos testes automatizados.
 
A primeira delas foi a escolha por uma arquitetura de laço contínuo sem bloqueios, evitando o uso de funções de espera prolongada. Isso garantiu que o firmware permanecesse responsivo durante toda a simulação, capturando corretamente as mudanças de estado do botão e as leituras do sensor no momento em que elas ocorriam.
 
A segunda foi a estratégia de referência térmica adaptativa, que permite distinguir uma variação gradual e natural de temperatura de uma subida abrupta característica de uma falha de isolamento. Em vez de comparar a temperatura atual a um valor fixo definido na inicialização, o sistema atualiza essa referência continuamente enquanto o ambiente está estável, e a mantém congelada assim que uma anomalia é detectada.
 
A terceira foi a introdução de um período mínimo de estabilização antes de declarar a normalização do sistema. Durante os testes locais, foi identificado que a mensagem de normalização podia ser emitida antes que o roteiro de teste começasse a monitorar a porta serial, o que fazia a validação expirar mesmo com o comportamento do firmware correto. A introdução desse pequeno atraso controlado resolveu o problema e, adicionalmente, tornou o sistema mais resistente a oscilações momentâneas nos sensores.
 
Por fim, as constantes de limite de tempo da porta aberta e de variação térmica tolerada foram mantidas como parâmetros isolados no início do código, facilitando ajustes futuros sem a necessidade de alterar a lógica principal do sistema.
 
---
 
## 5. Resultados Obtidos
 
O sistema foi validado com sucesso nos três cenários automatizados definidos para o desafio. No primeiro cenário, o firmware identificou corretamente a abertura da porta e emitiu o alerta de tempo excedido no instante esperado. No segundo cenário, o sistema detectou a elevação abrupta de temperatura e disparou o alerta térmico imediatamente após o salto simulado pelo sensor. No terceiro cenário, após o fechamento da porta, o sistema reportou corretamente a normalização do ambiente.
 
A validação foi realizada tanto localmente, por meio do Wokwi CLI, quanto na esteira de integração contínua configurada no GitHub Actions, com resultado consistente entre os dois ambientes após os ajustes descritos na seção anterior.
 
---
 
## 6. Comentários Adicionais
 
A principal dificuldade encontrada durante o desenvolvimento não esteve na lógica do firmware em si, mas na sincronização entre o comportamento do sistema embarcado e o momento exato em que o roteiro de teste automatizado começa a monitorar a porta serial. Esse tipo de problema só se tornou visível durante a execução dos testes locais, o que reforçou a importância de validar o projeto de ponta a ponta antes de considerá-lo concluído, e não apenas revisar a lógica isoladamente.
 
Como aprendizado, o desafio evidenciou a diferença entre escrever uma lógica de controle correta e garantir que essa lógica se comporte de forma previsível dentro das restrições de tempo de um ambiente de teste automatizado, algo especialmente relevante em sistemas embarcados que interagem com processos físicos e temporais.
 
