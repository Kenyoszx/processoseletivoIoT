from machine import Pin, I2C
import time
 
# Configuracao de Hardware ->

i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=400000)
MPU_ADDR = 0x68
PWR_MGMT_1 = 0x6B
TEMP_OUT_H = 0x41
 
btn = Pin(4, Pin.IN, Pin.PULL_UP)
 
# Parametros do Sistema ->

LIMITE_TEMPO_X = 5000       # ms - tempo maximo com a porta aberta
LIMITE_VARIACAO_Y = 3.0     # graus C - variacao abrupta maxima tolerada
ESTABILIZACAO_MS = 600      # ms - tempo que as condicoes seguras devem se manter antes de normalizar
INTERVALO_LOOP_MS = 100     # intervalo do loop infinito
 
 
def mpu_init():
    """Acorda o MPU6050 (sai do modo sleep)."""
    i2c.writeto_mem(MPU_ADDR, PWR_MGMT_1, b'\x00')
 
 
def read_temperature():
    """Le o registrador de temperatura do MPU6050 e converte para Celsius."""
    data = i2c.readfrom_mem(MPU_ADDR, TEMP_OUT_H, 2)
    raw = (data[0] << 8) | data[1]
    if raw > 32767:
        raw -= 65536
    return (raw / 340.0) + 36.53
 
 
def is_door_closed():
    """btn1 com pull-up: pressionado (fechado) = nivel logico BAIXO (0)."""
    return btn.value() == 0
 
 
def novo_estado():
    """Cria o dicionario de estado inicial do sistema."""
    return {
        "porta_aberta_desde": None,
        "alarme_porta_ativo": False,
        "alarme_termico_ativo": False,
        "temperatura_referencia": None,
        "normalizando_desde": None,
    }
 
 
def verificar_porta_aberta(estado, porta_fechada):
    """Atualiza o alarme de tempo de porta aberta (Limite X)."""
    if not porta_fechada:
        if estado["porta_aberta_desde"] is None:
            estado["porta_aberta_desde"] = time.ticks_ms()
        elif not estado["alarme_porta_ativo"]:
            decorrido = time.ticks_diff(time.ticks_ms(), estado["porta_aberta_desde"])
            if decorrido >= LIMITE_TEMPO_X:
                estado["alarme_porta_ativo"] = True
                print("ALERTA: Porta aberta por muito tempo!")
    else:
        estado["porta_aberta_desde"] = None
 
 
def verificar_temperatura(estado, porta_fechada, temp_atual):
    """Calcula o delta termico e atualiza o alarme de variacao brusca (Variacao Y).
 
    Retorna o delta_t calculado, usado tambem na verificacao de normalizacao.
    """
    if estado["temperatura_referencia"] is None and porta_fechada:
        estado["temperatura_referencia"] = temp_atual
 
    referencia = estado["temperatura_referencia"]
    delta_t = (temp_atual - referencia) if referencia is not None else 0.0
 
    if delta_t >= LIMITE_VARIACAO_Y:
        if not estado["alarme_termico_ativo"]:
            estado["alarme_termico_ativo"] = True
            print("ALERTA: Degradacao termica detectada!")
    elif porta_fechada and not estado["alarme_termico_ativo"]:
        # Se a temperatura varia lentamente o fluxo segue normal,
        # mas congela assim que um salto abrupto dispara o alarme.
        estado["temperatura_referencia"] = temp_atual
 
    return delta_t
 
 
def verificar_normalizacao(estado, porta_fechada, temp_atual, delta_t):
    """Declara a normalizacao apos as condicoes seguras se manterem estaveis
    por ESTABILIZACAO_MS, evitando falsos positivos por oscilacao momentanea."""
    condicoes_seguras = porta_fechada and delta_t < LIMITE_VARIACAO_Y
    alarme_ativo = estado["alarme_porta_ativo"] or estado["alarme_termico_ativo"]
 
    if alarme_ativo and condicoes_seguras:
        if estado["normalizando_desde"] is None:
            estado["normalizando_desde"] = time.ticks_ms()
        elif time.ticks_diff(time.ticks_ms(), estado["normalizando_desde"]) >= ESTABILIZACAO_MS:
            estado["alarme_porta_ativo"] = False
            estado["alarme_termico_ativo"] = False
            estado["temperatura_referencia"] = temp_atual
            estado["normalizando_desde"] = None
            print("Status: Sistema Normalizado.")
    else:
        estado["normalizando_desde"] = None
 
 
# Inicialização do sistema ->
mpu_init()
estado = novo_estado()
 
print("Sistema de Monitoramento Inicializado")
 
# Loop infinito principal ->
while True:
    porta_fechada = is_door_closed()
    temp_atual = read_temperature()
 
    verificar_porta_aberta(estado, porta_fechada)
    delta_t = verificar_temperatura(estado, porta_fechada, temp_atual)
    verificar_normalizacao(estado, porta_fechada, temp_atual, delta_t)
 
    time.sleep_ms(INTERVALO_LOOP_MS)