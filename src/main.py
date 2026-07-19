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
LIMITE_VARIACAO_Y = 3.0     # graus C - variacao maxima tolerada (delta T)
ESTABILIZACAO_MS = 600      # ms - tempo que as condicoes seguras devem se manter antes de normalizar
INTERVALO_LOOP_MS = 100     # intervalo do laco principal (nao bloqueante)
 
 
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
 
 
# Estado do Sistema ->
mpu_init()
 
porta_aberta_desde = None
alarme_porta_ativo = False
alarme_termico_ativo = False
temperatura_referencia = None
normalizando_desde = None
 
print("Sistema de Monitoramento Inicializado")
 
# teste workflow 1 

# Loop infinito principal ->
while True:
    porta_fechada = is_door_closed()
    temp_atual = read_temperature()
 
    # --- primeira leitura com porta fechada ---
    if temperatura_referencia is None and porta_fechada:
        temperatura_referencia = temp_atual
 
    delta_t = (temp_atual - temperatura_referencia) if temperatura_referencia is not None else 0.0
 
    # --- Tempo de porta aberta (Limite X) ---
    if not porta_fechada:
        if porta_aberta_desde is None:
            porta_aberta_desde = time.ticks_ms()
        elif not alarme_porta_ativo:
            decorrido = time.ticks_diff(time.ticks_ms(), porta_aberta_desde)
            if decorrido >= LIMITE_TEMPO_X:
                alarme_porta_ativo = True
                print("ALERTA: Porta aberta por muito tempo!")
    else:
        porta_aberta_desde = None
 
    # --- Elevacao termica (Variacao Y) ---
    if delta_t >= LIMITE_VARIACAO_Y:
        if not alarme_termico_ativo:
            alarme_termico_ativo = True
            print("ALERTA: Degradacao termica detectada!")
    elif porta_fechada and not alarme_termico_ativo:
        # Se a temperatura varia lentamente o fluxo segue normal,,
        # mas congela assim que um salto abrupto dispara o alarme.
        temperatura_referencia = temp_atual
 
    # --- Normalizacao - se ambas as condicoes seguras funcionam ao mesmo tempo ---
    condicoes_seguras = porta_fechada and delta_t < LIMITE_VARIACAO_Y
 
    if (alarme_porta_ativo or alarme_termico_ativo) and condicoes_seguras:
        if normalizando_desde is None:
            normalizando_desde = time.ticks_ms()
        elif time.ticks_diff(time.ticks_ms(), normalizando_desde) >= ESTABILIZACAO_MS:
            alarme_porta_ativo = False
            alarme_termico_ativo = False
            temperatura_referencia = temp_atual
            normalizando_desde = None
            print("Status: Sistema Normalizado.")
    else:
        normalizando_desde = None
 
    time.sleep_ms(INTERVALO_LOOP_MS)
 