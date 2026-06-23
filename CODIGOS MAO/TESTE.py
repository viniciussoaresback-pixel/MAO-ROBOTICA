import inspect

# Correção para pyFirmata funcionar no Python 3.11+
if not hasattr(inspect, "getargspec"):
    inspect.getargspec = inspect.getfullargspec

from pyfirmata import Arduino, SERVO
import time

PORTA = "COM3"

# Ordem: mindinho, anelar, meio, indicador, polegar
dedos = {
    "mindinho": 6,
    "anelar": 7,
    "meio": 8,
    "indicador": 9,
    "polegar": 10
}

placa = Arduino(PORTA)
time.sleep(2)

for nome, pino in dedos.items():
    placa.digital[pino].mode = SERVO
    time.sleep(0.1)

print("Teste iniciado")
print("CTRL + C para parar")

try:
    while True:
        print("\nAbrindo todos...")
        for nome, pino in dedos.items():
            print(f"Abrindo {nome} - pino {pino}")
            placa.digital[pino].write(0)
            time.sleep(0.4)

        time.sleep(2)

        print("\nFechando todos...")
        for nome, pino in dedos.items():
            print(f"Fechando {nome} - pino {pino}")
            placa.digital[pino].write(150)
            time.sleep(0.7)

        time.sleep(2)

except KeyboardInterrupt:
    print("\nParando teste...")

    for nome, pino in dedos.items():
        placa.digital[pino].write(0)
        time.sleep(0.2)

    placa.exit()