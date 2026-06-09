import logging
import os
import time
from datetime import datetime
from queue import Empty, Queue
from threading import Event, Lock, Thread
from flask import Flask, jsonify, request
from flask_cors import CORS
from sqlalchemy import inspect, text
from models import PatientLog, db
from symulacja import Symulacja
from testing_tools import create_testing_blueprint


# Konfiguracja Flask, logowania i bazy danych
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(project_dir, "icu_database.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)


# Konfiguracja oddzialow i pacjentow.
# Aplikacja obsluguje 3 oddzialy po 20 pacjentow, czyli lacznie 60 stanowisk.
PATIENTS_PER_WARD = 20
SIMULATION_INTERVAL_SECONDS = 1
DB_LOG_BATCH_SIZE = 120
BACKEND_LATENCY_WARNING_MS = 50
BACKEND_LATENCY_CRITICAL_MS = 100
SERVER_JITTER_WARNING_MS = 20
SERVER_JITTER_CRITICAL_MS = 30

WARDS = [
    {"id": "ICU-A", "name": "Oddzial ICU A"},
    {"id": "ICU-B", "name": "Oddzial ICU B"},
    {"id": "ICU-C", "name": "Oddzial ICU C"},
]

MITDB_RECORDS = [
    "100", "101", "102", "103", "104", "105", "106", "107", "108", "109",
    "111", "112", "113", "114", "115", "116", "117", "118", "119", "121",
    "122", "123", "124", "200", "201", "202", "203", "205", "207", "208",
    "209", "210", "212", "213", "214", "215", "217", "219", "220", "221",
    "222", "223", "228", "230", "231", "232", "233", "234",
]


# Tworzy konfiguracje pacjentow dla wszystkich oddzialow
def build_patient_configs():
    patients = []
    global_index = 0
    for ward in WARDS:
        for bed_number in range(1, PATIENTS_PER_WARD + 1):
            global_index += 1
            record = MITDB_RECORDS[(global_index - 1) % len(MITDB_RECORDS)]
            patients.append({
                "id": f"P{global_index:03d}",
                "nazwa": f"Pacjent {global_index:03d}",
                "lozko": f"Lozko {ward['id'][-1]}-{bed_number:02d}",
                "record": record,
                "wardId": ward["id"],
                "wardName": ward["name"],
                "offsetSeconds": global_index * 11,
            })
    return patients


PACJENT_CONFIGS = build_patient_configs()
PATIENTS_BY_ID = {patient["id"]: patient for patient in PACJENT_CONFIGS}


# Wspoldzielony stan symulacji
# Watki-demony aktualizuja patient_snapshots, a endpointy API tylko odczytuja cache
snapshot_lock = Lock()
instrumentation_lock = Lock()
log_queue = Queue()
stop_event = Event()

patient_snapshots = {}
ward_status = {
    ward["id"]: {
        "wardId": ward["id"],
        "wardName": ward["name"],
        "patientCount": PATIENTS_PER_WARD,
        "activeAlarmCount": 0,
        "updatedAt": None,
    }
    for ward in WARDS
}

EXPECTED_POLL_INTERVAL_MS = 1000
instrumentation_state = {
    "request_id": 0,
    "last_started_at": {},
}

# Dodaje brakujace kolumny do istniejacej tabeli bez kasowania starych logow
def sprawdzenie_bazy_dla_pacjenta():

    inspector = inspect(db.engine)
    if not inspector.has_table(PatientLog.__tablename__):
        return

    columns = {column["name"] for column in inspector.get_columns(PatientLog.__tablename__)}
    migrations = {
        "patient_id": "ALTER TABLE patient_logs ADD COLUMN patient_id VARCHAR(20)",
        "patient_name": "ALTER TABLE patient_logs ADD COLUMN patient_name VARCHAR(80)",
        "ward_id": "ALTER TABLE patient_logs ADD COLUMN ward_id VARCHAR(20)",
        "ward_name": "ALTER TABLE patient_logs ADD COLUMN ward_name VARCHAR(80)",
        "bed": "ALTER TABLE patient_logs ADD COLUMN bed VARCHAR(20)",
        "record_name": "ALTER TABLE patient_logs ADD COLUMN record_name VARCHAR(20)",
        "alarms": "ALTER TABLE patient_logs ADD COLUMN alarms VARCHAR(200)",
    }

    for column, statement in migrations.items():
        if column not in columns:
            db.session.execute(text(statement))
    db.session.commit()

# Inicjalizuje osobny obiekt Symulacja dla kazdego pacjenta.
def create_simulators():
    simulators = {}
    for patient in PACJENT_CONFIGS:
        simulator = Symulacja(record_name=patient["record"])
        offset = int(simulator.fs) * patient["offsetSeconds"]
        simulator.ustaw_offset(offset)
        simulators[patient["id"]] = simulator
    return simulators

# Pobiera aktualny pomiar pacjenta i opakowuje go w format JSON dla frontendu
def okresl_priorytet_alarmu(alarms):
    if any(alarm.startswith("CRITICAL:") for alarm in alarms):
        return "critical", "Krytyczny"
    if any(alarm.startswith("HIGH:") for alarm in alarms):
        return "warning", "Wysoki"
    return "normal", "Normalny"


def stworz_snapshot_pacjenta(patient, simulator):
    data = simulator.pobierz_dane()
    status = "ALARM" if data["alarms"] else "NORMAL"
    alarm_priority, alarm_priority_label = okresl_priorytet_alarmu(data["alarms"])

    return {
        "patientId": patient["id"],
        "patientName": patient["nazwa"],
        "wardId": patient["wardId"],
        "wardName": patient["wardName"],
        "bed": patient["lozko"],
        "record": patient["record"],
        "hr": data["hr"],
        "spo2": data["spo2"],
        "alarms": data["alarms"],
        "alarmPriority": alarm_priority,
        "alarmPriorityLabel": alarm_priority_label,
        "status": status,
        "updatedAt": datetime.now().strftime("%H:%M:%S"),
    }

# Zamienia snapshot z pamieci na rekord bazy danych
def zapis_logi_pacjenta(snapshot):
    return PatientLog(
        patient_id=snapshot["patientId"],
        patient_name=snapshot["patientName"],
        ward_id=snapshot["wardId"],
        ward_name=snapshot["wardName"],
        bed=snapshot["bed"],
        record_name=snapshot["record"],
        hr=snapshot["hr"],
        spo2=snapshot["spo2"],
        alarms=", ".join(snapshot["alarms"]),
    )

# Aktualizuje licznik alarmow i czas ostatniej symulacji dla jednego oddzialu
def update_ward_status(ward_id, ward_snapshots):
    ward = next(ward for ward in WARDS if ward["id"] == ward_id)
    ward_status[ward_id] = {
        "wardId": ward_id,
        "wardName": ward["name"],
        "patientCount": len(ward_snapshots),
        "activeAlarmCount": sum(1 for snapshot in ward_snapshots if snapshot["alarms"]),
        "updatedAt": datetime.now().strftime("%H:%M:%S"),
    }

"""
Watek-demon oddzialu
Co sekunde przelicza pacjentow tylko z jednego oddzialu i zapisuje gotowe wyniki do cache
"""
def ward_simulation_worker(ward, simulators):
    ward_id = ward["id"]
    patients = [patient for patient in PACJENT_CONFIGS if patient["wardId"] == ward_id]

    while not stop_event.is_set():
        ward_snapshots = [
            stworz_snapshot_pacjenta(patient, simulators[patient["id"]])
            for patient in patients
        ]

        with snapshot_lock:
            for snapshot in ward_snapshots:
                patient_snapshots[snapshot["patientId"]] = snapshot
            update_ward_status(ward_id, ward_snapshots)

        for snapshot in ward_snapshots:
            log_queue.put(snapshot.copy())

        stop_event.wait(SIMULATION_INTERVAL_SECONDS)

"""
Osobny watek-demon zapisujacy logi do SQLite.
Oddzielenie zapisu od symulacji ogranicza blokowanie workerow oddzialow przez baze.
"""
def db_log_worker():
    with app.app_context():
        pending_logs = []
        while not stop_event.is_set():
            try:
                snapshot = log_queue.get(timeout=0.5)
                pending_logs.append(zapis_logi_pacjenta(snapshot))
                log_queue.task_done()
            except Empty:
                pass

            if pending_logs and (len(pending_logs) >= DB_LOG_BATCH_SIZE or log_queue.empty()):
                db.session.add_all(pending_logs)
                db.session.commit()
                pending_logs = []

# Uruchamia demony symulacji dla oddzialow oraz demona logowania do bazy
def start_background_services():
    simulators = create_simulators()

    # Pierwszy snapshot jest tworzony synchronicznie, zeby frontend od razu mial dane
    for ward in WARDS:
        patients = [patient for patient in PACJENT_CONFIGS if patient["wardId"] == ward["id"]]
        ward_snapshots = [
            stworz_snapshot_pacjenta(patient, simulators[patient["id"]])
            for patient in patients
        ]
        with snapshot_lock:
            for snapshot in ward_snapshots:
                patient_snapshots[snapshot["patientId"]] = snapshot
            update_ward_status(ward["id"], ward_snapshots)

    for ward in WARDS:
        thread = Thread(
            target=ward_simulation_worker,
            args=(ward, simulators),
            name=f"simulation-{ward['id']}",
            daemon=True,
        )
        thread.start()

    Thread(target=db_log_worker, name="patient-log-writer", daemon=True).start()

# Zwraca spojny odczyt pacjentow i statusow oddzialow z pamieci wspoldzielonej
def get_cached_snapshots():
    with snapshot_lock:
        patients = [patient_snapshots[patient["id"]].copy() for patient in PACJENT_CONFIGS]
        wards = [ward_status[ward["id"]].copy() for ward in WARDS]
    return patients, wards

# Ocenia, czy opoznienia moga utrudnic poprawny odczyt danych ICU
def get_warning_level(instrumentation):
    latency = instrumentation["backendLatencyMs"] or 0
    jitter = abs(instrumentation["serverJitterMs"] or 0)
    latency_critical = latency >= BACKEND_LATENCY_CRITICAL_MS
    jitter_critical = jitter >= SERVER_JITTER_CRITICAL_MS
    latency_warning = latency >= BACKEND_LATENCY_WARNING_MS
    jitter_warning = jitter >= SERVER_JITTER_WARNING_MS

    if latency_warning or jitter_warning:
        return {
            "active": True,
            "level": "critical" if latency_critical or jitter_critical else "warning",
            "message": (
                "Zbyt duze opoznienie transmisji. Dane moga byc nieaktualne "
                "i wymagaja ostroznej interpretacji."
            ),
            "thresholds": {
                "backendLatencyWarningMs": BACKEND_LATENCY_WARNING_MS,
                "backendLatencyCriticalMs": BACKEND_LATENCY_CRITICAL_MS,
                "serverJitterWarningMs": SERVER_JITTER_WARNING_MS,
                "serverJitterCriticalMs": SERVER_JITTER_CRITICAL_MS,
            },
        }

    return {
        "active": False,
        "level": "normal",
        "message": "Opoznienia w normie dla odswiezania danych co 1 sekunde.",
        "thresholds": {
            "backendLatencyWarningMs": BACKEND_LATENCY_WARNING_MS,
            "backendLatencyCriticalMs": BACKEND_LATENCY_CRITICAL_MS,
            "serverJitterWarningMs": SERVER_JITTER_WARNING_MS,
            "serverJitterCriticalMs": SERVER_JITTER_CRITICAL_MS,
        },
    }

# Kalkuluje latency i jitter dla odpowiedzi API
def stworz_instrumentacje(endpoint, started_at):
    ended_at = time.perf_counter()
    latency_ms = (ended_at - started_at) * 1000

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


app.register_blueprint(create_testing_blueprint(stworz_instrumentacje))


with app.app_context():
    db.create_all()
    sprawdzenie_bazy_dla_pacjenta()
    start_background_services()


@app.route("/data")
# [GET] /data zwraca gotowy snapshot jednego pacjenta z cache
def pobierz_dane():
    started_at = time.perf_counter()
    patient_id = request.args.get("id_pacjenta", PACJENT_CONFIGS[0]["id"])

    with snapshot_lock:
        snapshot = patient_snapshots.get(patient_id, patient_snapshots[PACJENT_CONFIGS[0]["id"]]).copy()

    instrumentation = stworz_instrumentacje("/data", started_at)
    snapshot["instrumentation"] = instrumentation
    snapshot["delayWarning"] = get_warning_level(instrumentation)
    return jsonify(snapshot)


@app.route("/patients")
# [GET] /patients zwraca wszystkich pacjentow pogrupowanych po oddzialach
def pobierz_pacjentow():
    started_at = time.perf_counter()
    patients, wards = get_cached_snapshots()
    active_alarms = [snapshot for snapshot in patients if snapshot["alarms"]]
    instrumentation = stworz_instrumentacje("/patients", started_at)

    logger.info(
        "Snapshot ICU: wards=%s patients=%s active_alarms=%s latency=%sms jitter=%sms",
        len(wards),
        len(patients),
        len(active_alarms),
        instrumentation["backendLatencyMs"],
        instrumentation["serverJitterMs"],
    )

    return jsonify({
        "wards": wards,
        "patients": patients,
        "totalPatientCount": len(patients),
        "activeAlarmCount": len(active_alarms),
        "updatedAt": datetime.now().strftime("%H:%M:%S"),
        "instrumentation": instrumentation,
        "delayWarning": get_warning_level(instrumentation),
    })


@app.route("/history")
# [GET] /history zwraca ostatnie logi pacjenta lub oddzialu
def pobierz_historie():
    id_pacjenta = request.args.get("id_pacjenta")
    ward_id = request.args.get("ward_id")
    query = PatientLog.query

    if id_pacjenta:
        query = query.filter(PatientLog.patient_id == id_pacjenta)
    if ward_id:
        query = query.filter(PatientLog.ward_id == ward_id)

    logs = query.order_by(PatientLog.id.desc()).limit(20).all()
    return jsonify([log.to_dict() for log in logs])


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, threaded=True)
