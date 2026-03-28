import random
"""
Symulacja przebiegu hr (tętna) i spo2 (saturacji)
Tylko przykład do poprawy lub pobrania z jakiejs bazy bardziej stabilnego przebiegu
"""
def generate_data():
    return {
        "hr": random.randint(60, 140),
        "spo2": random.randint(85, 100)
    }

def check_alarms(data):
    alarms = []

    if data["hr"] > 100:
        alarms.append("Wysokie HR")

    if data["spo2"] < 90:
        alarms.append("Niskie SpO2")

    return alarms