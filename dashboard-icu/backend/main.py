import os
import logging
import time
from threading import Lock
from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS
from models import db, PatientLog
from symulacja import Symulacja
from sqlalchemy import inspect, text

# KONFIGURACJA LOGOWANIA I APLIKACJI FLASK
# Ustawienie formatu logów wyświetlanych w konsoli
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# Inicjalizacja głównego obiektu aplikacji Flask
app = Flask(__name__)
CORS(app)

# KONFIGURACJA BAZY DANYCH (SQLAlchemy)
# Ustalenie ścieżki do głównego katalogu projektu
project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(project_dir, 'icu_database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Podpięcie obiektu bazy danych pod aplikację Flask
db.init_app(app)

# KONFIGURACJA PACJENTÓW
# Statyczna lista definiująca pacjentów, ich identyfikatory i przypisane nagrania EKG (z bazy MIT-BIH)
PACJENT_CONFINGS = [
    {"id": "P001", "nazwa": "Pacjent 01", "lozko": "Łózko 1", "record": "100"},
    {"id": "P002", "nazwa": "Pacjent 02", "lozko": "Łózko 2", "record": "101"},
    {"id": "P003", "nazwa": "Pacjent 03", "lozko": "Łózko 3", "record": "102"},
    {"id": "P004", "nazwa": "Pacjent 04", "lozko": "Łózko 4", "record": "103"},
    {"id": "P005", "nazwa": "Pacjent 05", "lozko": "Łózko 5", "record": "104"},
    {"id": "P006", "nazwa": "Pacjent 06", "lozko": "Łózko 6", "record": "105"},
    {"id": "P007", "nazwa": "Pacjent 07", "lozko": "Łózko 7", "record": "106"},
    {"id": "P008", "nazwa": "Pacjent 08", "lozko": "Łózko 8", "record": "107"},
    {"id": "P009", "nazwa": "Pacjent 09", "lozko": "Łózko 9", "record": "108"},
    {"id": "P010", "nazwa": "Pacjent 10", "lozko": "Łózko 10", "record": "203"},
]

# KONFIGURACJA TELEMETRII (Mierzenie czasu odpowiedzi)
EXPECTED_POLL_INTERVAL_MS = 1000 # Spodziewany czas między zapytaniami z frontendu (1 sekunda)
instrumentation_lock = Lock() # Blokada (Mutex) do bezpiecznej zmiany stanu telemetrii pomiędzy wieloma wątkami
instrumentation_state = {
    "request_id": 0,          # Licznik przetworzonych zapytań
    "last_started_at": {},    # Czas rozpoczęcia ostatniego zapytania dla konkretnego endpointu
}

# FUNKCJE POMOCNICZE
def sprawdzenie_bazy_dla_pacejnta():
    """
    Funkcja sprawdzająca czy w bazie danych brakuje kolumn.
    """
    inspector = inspect(db.engine)
    if not inspector.has_table(PatientLog.__tablename__):
        return

    columns = {column["name"] for column in inspector.get_columns(PatientLog.__tablename__)}
    migrations = {
        "id_pacjenta": "ALTER TABLE patient_logs ADD COLUMN id_pacjenta VARCHAR(20)",
        "nazwa_pacjenta": "ALTER TABLE patient_logs ADD COLUMN nazwa_pacjenta VARCHAR(80)",
        "lozko": "ALTER TABLE patient_logs ADD COLUMN lozko VARCHAR(20)",
    }

    # Wykonanie bezpośrednich zapytań SQL jeśli brakuje kolumny
    for column, statement in migrations.items():
        if column not in columns:
            db.session.execute(text(statement))
    db.session.commit()


def create_simulators():
    """
    Inicjalizuje obiekty symulacji dla każdego pacjenta ze zdefiniowanej listy.
    Nadaje im początkowe "przesunięcie" (offset), aby wykresy każdego pacjenta 
    startowały od innego momentu i nie wyglądały identycznie. Poprzednio był z tym duży prbolem
    """
    simulators = {}
    for index, patient in enumerate(PACJENT_CONFINGS):
        simulator = Symulacja(record_name=patient["record"])
        offset = index * int(simulator.fs) * 15 # Przesunięcie o 15 sekund dla kolejnych pacjentów
        if offset < len(simulator.signal) - simulator.window_size:
            simulator.current_sample = offset
        simulators[patient["id"]] = simulator
    return simulators


def stworz_snapshot_pacjenta(patient, simulator):
    """
    Pobiera najnowsze dane z symulatora danego pacjenta i przygotowuje obiekt
    w formacie zgodnym z oczekiwaniami frontendu.
    """
    data = simulator.pobierz_dane()
    status = "ALARM" if data["alarms"] else "NORMAL"

    return {
        "patientId": patient["id"],
        "patientName": patient["nazwa"],
        "bed": patient["lozko"],
        "record": patient["record"],
        "hr": data["hr"],
        "spo2": data["spo2"],
        "alarms": data["alarms"],
        "status": status,
        "updatedAt": datetime.now().strftime("%H:%M:%S"),
    }


def zapis_logi_pacjenta(snapshot):
    """
    Zapisuje obecny stan pacjenta (tętno, saturacja, alarmy) jako nowy wpis w bazie danych.
    """
    log = PatientLog(
        patient_id=snapshot["patientId"],
        patient_name=snapshot["patientName"],
        bed=snapshot["bed"],
        hr=snapshot["hr"],
        spo2=snapshot["spo2"],
        alarms=", ".join(snapshot["alarms"])
    )
    db.session.add(log)


def stworz_instrumentacje(endpoint, started_at):
    """
    Kalkuluje metryki sieciowe dla pojedynczego zapytania: opóźnienie backendu (latency)
    oraz wahania (jitter) - czyli opóźnienia w stosunku do oczekiwanego interwału.
    Zwraca słownik danych telemetrycznych dołączany do każdej odpowiedzi.
    """
    ended_at = time.perf_counter()
    latency_ms = (ended_at - started_at) * 1000

    # Dałem Lock() aby uniknąć błędów przy jednoczesnym odpytywaniu przez różne przeglądarki
    with instrumentation_lock:
        instrumentation_state["request_id"] += 1
        request_id = instrumentation_state["request_id"]
        last_started_at = instrumentation_state["last_started_at"].get(endpoint)
        instrumentation_state["last_started_at"][endpoint] = started_at

    interval_ms = None
    jitter_ms = None
    if last_started_at is not None:
        interval_ms = (started_at - last_started_at) * 1000
        jitter_ms = interval_ms - EXPECTED_POLL_INTERVAL_MS

    return {
        "requestId": request_id,
        "endpoint": endpoint,
        "backendLatencyMs": round(latency_ms, 2),
        "serverPollIntervalMs": round(interval_ms, 2) if interval_ms is not None else None,
        "serverJitterMs": round(jitter_ms, 2) if jitter_ms is not None else None,
        "expectedPollIntervalMs": EXPECTED_POLL_INTERVAL_MS,
        "serverTimestamp": datetime.now().strftime("%H:%M:%S"),
    }

# START APILKACJI I BAZY DANYCH
# Kontekst aplikacji - przygotowanie bazy i stworzenie instancji symulatorów przed pierwszym requestem
with app.app_context():
    db.create_all() # Utworzenie struktury bazy jeśli nie istnieje
    sprawdzenie_bazy_dla_pacejnta() # Sprawdzenie czy dodano nowe kolumny
    simulators = create_simulators()


# ENDPOINTY API (Miejsca styku z frontendem)
@app.route("/data")
def pobierz_dane():
    """
    [GET] /data Pobiera pojedynczy 'snapshot' wybranego pacjent
    """
    started_at = time.perf_counter()
    patient_id = request.args.get("id_pacjenta", PACJENT_CONFINGS[0]["id"])
    patient = next((p for p in PACJENT_CONFINGS if p["id"] == patient_id), PACJENT_CONFINGS[0])
    
    # Pobranie danych i zapis do bazy
    snapshot = stworz_snapshot_pacjenta(patient, simulators[patient["id"]])
    zapis_logi_pacjenta(snapshot)
    db.session.commit()
    
    # Zbieranie metryk telemetrii
    instrumentation = stworz_instrumentacje("/data", started_at)

    logger.info(
        "Pobrano i zapisano: %s %s HR=%s BPM SpO2=%s%% latency=%sms jitter=%sms",
        snapshot["patientId"],
        snapshot["bed"],
        snapshot["hr"],
        snapshot["spo2"],
        instrumentation["backendLatencyMs"],
        instrumentation["serverJitterMs"],
    )
    
    snapshot["instrumentation"] = instrumentation
    return jsonify(snapshot)


@app.route("/patients")
def pobierz_pacjentow():
    """
    [GET] /patients Pobiea najnowsze dane dla WSZYSTKICH pacjentów na oddziale na raz.
    Jest to głowny endpoint używany przez dashboard frontndu co 1 sekundę.
    """
    started_at = time.perf_counter()
    snapshots = []
    
    # Przejście po każdym pacjencie i pobranie wyników
    for pacjent in PACJENT_CONFINGS:
        snapshot = stworz_snapshot_pacjenta(pacjent, simulators[pacjent["id"]])
        zapis_logi_pacjenta(snapshot) # Dodanie operacji do kolejki bazy danych
        snapshots.append(snapshot)

    db.session.commit() # Zatwirdzenie wszystkich zmian w bazie za jednym razem
    
    # Sprawdzenie ile pacjentów posiada obecnie jakikolwiek alarm
    active_alarms = [snapshot for snapshot in snapshots if snapshot["alarms"]]
    instrumentation = stworz_instrumentacje("/patients", started_at)

    logger.info(
        "Snapshot oddzialu: patients=%s active_alarms=%s latency=%sms jitter=%sms",
        len(snapshots),
        len(active_alarms),
        instrumentation["backendLatencyMs"],
        instrumentation["serverJitterMs"],
    )

    # Zwrócenie zbiorczego formatu JSON
    return jsonify({
        "patients": snapshots,
        "activeAlarmCount": len(active_alarms),
        "updatedAt": datetime.now().strftime("%H:%M:%S"),
        "instrumentation": instrumentation,
    })


@app.route("/history")
def pobierz_historie():
    """
    [GET] /history Endpoint pomocniczy, zwracający 20 ostatnich logów pacjenta z bazy danych.
    (Opcjonalny np. do zasilenia wykresów po odświeżeniu strony, jeśli frontend zechce to wykorzystać)
    """
    id_pacjenta = request.args.get("id_pacjenta")
    query = PatientLog.query
    if id_pacjenta:
        query = query.filter(PatientLog.patient_id == id_pacjenta)
    
    # Pobranie 20 ostatnich wpisów od najnowszego
    logs = query.order_by(PatientLog.id.desc()).limit(20).all()
    return jsonify([l.to_dict() for l in logs])

# URUCHOMIENIE SERWERA
if __name__ == "__main__":
    # Parametr threaded=False wymusza działanie w pojedynczym wątku, co na systemach 
    # Windows i w środowiskach IDE (np. PyCharm) pozwala uniknąć wieszania się 
    # procesu po jego wyłączeniu, zapobiegając "zombie procesom" portu 5000.
    app.run(host="127.0.0.1", port=5000, threaded=False)