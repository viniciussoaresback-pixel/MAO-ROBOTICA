import inspect

# Correção para pyfirmata em Python novo
if not hasattr(inspect, "getargspec"):
    inspect.getargspec = inspect.getfullargspec

import cv2
import mediapipe as mp
from pyfirmata import Arduino, SERVO, util
import time
import math


PORTA = "COM3"

placa = Arduino(PORTA)

it = util.Iterator(placa)
it.start()

CONFIG = {
    "polegar": {
        "pino": 10,
        "aberto": 1.15,
        "fechado": 0.78,
        "servo_aberto": 0,
        "servo_fechado": 130
    },
    "indicador": {
        "pino": 9,
        "aberto": 1.72,
        "fechado": 1.40,
        "servo_aberto": 0,
        "servo_fechado": 180
    },
    "meio": {
        "pino": 8,
        "aberto": 1.72,
        "fechado": 1.40,
        "servo_aberto": 0,
        "servo_fechado": 180
    },
    "anelar": {
        "pino": 7,
        "aberto": 1.62,
        "fechado": 1.50,
        "servo_aberto": 0,
        "servo_fechado": 180
    },
    "mindinho": {
        "pino": 6,
        "aberto": 1.52,
        "fechado": 1.22,
        "servo_aberto": 0,
        "servo_fechado": 145
    }
}

PASSO = 50
INTERVALO_SERVO = 0.008
SUAVIDADE = 0.80
DIFERENCA_MINIMA = 1
GANHO_FECHAMENTO = 1.35
CURVA_FECHAMENTO = 0.65
DESENHAR_MAO = False

for dedo in CONFIG:
    placa.digital[CONFIG[dedo]["pino"]].mode = SERVO
    time.sleep(0.05)

angulo_atual = {}
angulo_destino = {}
ultimo_enviado = {}
leitura_suave = {}

for dedo in CONFIG:
    angulo_atual[dedo] = CONFIG[dedo]["servo_aberto"]
    angulo_destino[dedo] = CONFIG[dedo]["servo_aberto"]
    ultimo_enviado[dedo] = -1
    leitura_suave[dedo] = None
    placa.digital[CONFIG[dedo]["pino"]].write(CONFIG[dedo]["servo_aberto"])
    time.sleep(0.05)

mp_maos = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils

hands = mp_maos.Hands(
    static_image_mode=False,
    max_num_hands=1,
    model_complexity=0,
    min_detection_confidence=0.55,
    min_tracking_confidence=0.55
)

camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)

camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
camera.set(cv2.CAP_PROP_FPS, 30)
camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
camera.set(cv2.CAP_PROP_ZOOM, 0)

cv2.namedWindow("Camera IA - Mao Robotica", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Camera IA - Mao Robotica", 900, 650)


def distancia(a, b):
    return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2)


def limitar(valor, minimo, maximo):
    if valor < minimo:
        return minimo

    if valor > maximo:
        return maximo

    return valor


def suavizar(dedo, valor):
    if leitura_suave[dedo] is None:
        leitura_suave[dedo] = valor
    else:
        leitura_suave[dedo] = leitura_suave[dedo] + (valor - leitura_suave[dedo]) * SUAVIDADE

    return leitura_suave[dedo]


def converter_para_servo(dedo, valor):
    cfg = CONFIG[dedo]

    aberto = cfg["aberto"]
    fechado = cfg["fechado"]

    porcentagem = (aberto - valor) / (aberto - fechado)
    porcentagem = limitar(porcentagem, 0, 1)

    porcentagem = porcentagem * GANHO_FECHAMENTO
    porcentagem = limitar(porcentagem, 0, 1)

    porcentagem = porcentagem ** CURVA_FECHAMENTO

    angulo = cfg["servo_aberto"] + porcentagem * (cfg["servo_fechado"] - cfg["servo_aberto"])

    return int(angulo), int(porcentagem * 100)


def taxa_polegar(lm):
    largura_mao = distancia(lm[5], lm[17])

    if largura_mao == 0:
        return 0

    abertura = distancia(lm[4], lm[17])

    return abertura / largura_mao


def taxa_dedo(lm, base, ponta):
    base_mao = distancia(lm[0], lm[base])

    if base_mao == 0:
        return 0

    abertura = distancia(lm[0], lm[ponta])

    return abertura / base_mao


def detectar_dedos(lm):
    valores = {
        "polegar": taxa_polegar(lm),
        "indicador": taxa_dedo(lm, 5, 8),
        "meio": taxa_dedo(lm, 9, 12),
        "anelar": taxa_dedo(lm, 13, 16),
        "mindinho": taxa_dedo(lm, 17, 20)
    }

    resultado = {}

    for dedo in valores:
        valor_suave = suavizar(dedo, valores[dedo])
        angulo, porcentagem = converter_para_servo(dedo, valor_suave)

        resultado[dedo] = {
            "valor": valor_suave,
            "angulo": angulo,
            "porcentagem": porcentagem
        }

    return resultado


def atualizar_destinos(resultado):
    for dedo in resultado:
        angulo_destino[dedo] = resultado[dedo]["angulo"]


def mover_servos():
    for dedo in CONFIG:
        atual = angulo_atual[dedo]
        destino = angulo_destino[dedo]

        if abs(destino - atual) <= PASSO:
            novo = destino
        elif destino > atual:
            novo = atual + PASSO
        else:
            novo = atual - PASSO

        angulo_atual[dedo] = novo

        if abs(novo - ultimo_enviado[dedo]) >= DIFERENCA_MINIMA:
            placa.digital[CONFIG[dedo]["pino"]].write(int(novo))
            ultimo_enviado[dedo] = novo


def abrir_tudo():
    for dedo in CONFIG:
        angulo_atual[dedo] = CONFIG[dedo]["servo_aberto"]
        angulo_destino[dedo] = CONFIG[dedo]["servo_aberto"]
        ultimo_enviado[dedo] = CONFIG[dedo]["servo_aberto"]
        placa.digital[CONFIG[dedo]["pino"]].write(CONFIG[dedo]["servo_aberto"])
        time.sleep(0.03)


def fechar_tudo():
    for dedo in CONFIG:
        angulo_atual[dedo] = CONFIG[dedo]["servo_fechado"]
        angulo_destino[dedo] = CONFIG[dedo]["servo_fechado"]
        ultimo_enviado[dedo] = CONFIG[dedo]["servo_fechado"]
        placa.digital[CONFIG[dedo]["pino"]].write(CONFIG[dedo]["servo_fechado"])
        time.sleep(0.03)


print("Sistema iniciado")
print("Q ou ESC = sair")
print("R = abrir tudo")
print("F = fechar tudo")

abrir_tudo()

ultimo_envio = time.time()

try:
    while True:
        sucesso, frame = camera.read()

        if not sucesso:
            print("Erro ao abrir a camera")
            break

        frame = cv2.flip(frame, 1)

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        resultado = hands.process(rgb)

        if resultado.multi_hand_landmarks:
            mao = resultado.multi_hand_landmarks[0]
            lm = mao.landmark

            dados = detectar_dedos(lm)
            atualizar_destinos(dados)

            if DESENHAR_MAO:
                mp_draw.draw_landmarks(frame, mao, mp_maos.HAND_CONNECTIONS)

            y = 25

            for dedo in dados:
                texto = f"{dedo}: {dados[dedo]['porcentagem']}% ang {dados[dedo]['angulo']}"

                cv2.putText(
                    frame,
                    texto,
                    (10, y),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.45,
                    (0, 255, 0),
                    1
                )

                y += 22

        else:
            cv2.putText(
                frame,
                "Mostre a mao para a camera",
                (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (0, 0, 255),
                1
            )

        agora = time.time()

        if agora - ultimo_envio >= INTERVALO_SERVO:
            mover_servos()
            ultimo_envio = agora

        cv2.imshow("Camera IA - Mao Robotica", frame)

        tecla = cv2.waitKey(1) & 0xFF

        if tecla == ord("q") or tecla == 27:
            break

        if tecla == ord("r"):
            abrir_tudo()
            print("Mao aberta")

        if tecla == ord("f"):
            fechar_tudo()
            print("Mao fechada")

finally:
    camera.release()
    cv2.destroyAllWindows()
    abrir_tudo()
    placa.exit()