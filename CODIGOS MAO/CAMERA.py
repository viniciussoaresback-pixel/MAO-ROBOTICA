import inspect

# Correção para pyFirmata funcionar no Python 3.11+
if not hasattr(inspect, "getargspec"):
    inspect.getargspec = inspect.getfullargspec

import cv2
import mediapipe as mp
from pyfirmata import Arduino, SERVO, util
import time

PORTA = "COM3"

PINOS = {
    "polegar": 10,
    "indicador": 9,
    "meio": 8,
    "anelar": 7,
    "mindinho": 6
}

ABERTO = {
    "polegar": 0,
    "indicador": 0,
    "meio": 0,
    "anelar": 0,
    "mindinho": 0
}

FECHADO = {
    "polegar": 140,
    "indicador": 150,
    "meio": 150,
    "anelar": 150,
    "mindinho": 150
}

PASSO = 12
INTERVALO_SERVO = 0.025

INVERTER = {
    "polegar": False,
    "indicador": False,
    "meio": False,
    "anelar": False,
    "mindinho": False
}

DESENHAR_MAO = False

print("Conectando no Arduino...")

placa = Arduino(PORTA)

it = util.Iterator(placa)
it.start()

time.sleep(2)

for dedo, pino in PINOS.items():
    placa.digital[pino].mode = SERVO
    time.sleep(0.05)

posicao_atual = {}
destino_servo = {}

for dedo in PINOS:
    posicao_atual[dedo] = ABERTO[dedo]
    destino_servo[dedo] = ABERTO[dedo]
    placa.digital[PINOS[dedo]].write(ABERTO[dedo])
    time.sleep(0.1)

mp_maos = mp.solutions.hands
mp_desenho = mp.solutions.drawing_utils

maos = mp_maos.Hands(
    static_image_mode=False,
    max_num_hands=1,
    model_complexity=0,
    min_detection_confidence=0.55,
    min_tracking_confidence=0.55
)

camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)

camera.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
camera.set(cv2.CAP_PROP_FPS, 30)
camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)


def detectar_dedos(lm):
    dedos = {}

    dedos["polegar"] = lm[4].x < lm[3].x
    dedos["indicador"] = lm[8].y < lm[6].y
    dedos["meio"] = lm[12].y < lm[10].y
    dedos["anelar"] = lm[16].y < lm[14].y
    dedos["mindinho"] = lm[20].y < lm[18].y

    return dedos


def atualizar_destinos(dedos):
    for dedo, aberto in dedos.items():
        if INVERTER[dedo]:
            aberto = not aberto

        if aberto:
            destino_servo[dedo] = ABERTO[dedo]
        else:
            destino_servo[dedo] = FECHADO[dedo]


def mover_servos():
    for dedo in PINOS:
        atual = posicao_atual[dedo]
        destino = destino_servo[dedo]

        if atual == destino:
            continue

        if abs(destino - atual) <= PASSO:
            novo = destino
        elif destino > atual:
            novo = atual + PASSO
        else:
            novo = atual - PASSO

        posicao_atual[dedo] = novo
        placa.digital[PINOS[dedo]].write(novo)


def abrir_tudo():
    for dedo in PINOS:
        destino_servo[dedo] = ABERTO[dedo]
        posicao_atual[dedo] = ABERTO[dedo]
        placa.digital[PINOS[dedo]].write(ABERTO[dedo])
        time.sleep(0.05)


print("Sistema iniciado")
print("Q = sair")
print("R = abrir tudo")

ultimo_envio_servo = time.time()

try:
    while True:
        sucesso, frame = camera.read()

        if not sucesso:
            print("Erro ao abrir a câmera")
            break

        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        resultado = maos.process(rgb)

        if resultado.multi_hand_landmarks:
            mao = resultado.multi_hand_landmarks[0]
            lm = mao.landmark

            dedos = detectar_dedos(lm)
            atualizar_destinos(dedos)

            if DESENHAR_MAO:
                mp_desenho.draw_landmarks(frame, mao, mp_maos.HAND_CONNECTIONS)

            y = 25
            for dedo, aberto in dedos.items():
                texto = f"{dedo}: {'ABERTO' if aberto else 'FECHADO'}"

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

        agora = time.time()

        if agora - ultimo_envio_servo >= INTERVALO_SERVO:
            mover_servos()
            ultimo_envio_servo = agora

        cv2.imshow("Mao Robotica - Camera Leve", frame)

        tecla = cv2.waitKey(1) & 0xFF

        if tecla == ord("q"):
            break

        if tecla == ord("r"):
            abrir_tudo()
            print("Mao aberta/resetada")

finally:
    print("Encerrando sistema...")

    try:
        abrir_tudo()
    except:
        pass

    camera.release()
    cv2.destroyAllWindows()

    try:
        placa.exit()
    except:
        pass