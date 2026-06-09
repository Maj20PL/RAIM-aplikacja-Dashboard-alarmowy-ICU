import os
import subprocess
import sys
import time
from datetime import datetime
from threading import Lock, Thread

from flask import Blueprint, jsonify, request


MAX_CPU_TEST_SECONDS = 120


# Tworzy osobny modul endpointow testowych dla Etapu 3

def create_testing_blueprint(create_instrumentation):
    testing = Blueprint("testing_tools", __name__)
    cpu_test_lock = Lock()
    cpu_test_state = {
        "running": False,
        "cores": 0,
        "durationSeconds": 0,
        "startedAt": None,
        "endsAt": None,
        "processes": [],
        "lastResult": None,
    }

    # Demonstracja race condition
    def run_race_demo(use_lock=False, thread_count=8, increments=2000):
        state = {"counter": 0}
        demo_lock = Lock()

        def increment_worker():
            for index in range(increments):
                if use_lock:
                    with demo_lock:
                        state["counter"] += 1
                else:
                    current_value = state["counter"]
                    if index % 5 == 0:
                        time.sleep(0)
                    state["counter"] = current_value + 1

        threads = [Thread(target=increment_worker) for _ in range(thread_count)]
        started_at = time.perf_counter()
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        expected = thread_count * increments
        actual = state["counter"]
        return {
            "threads": thread_count,
            "incrementsPerThread": increments,
            "expected": expected,
            "actual": actual,
            "lostUpdates": expected - actual,
            "durationMs": round((time.perf_counter() - started_at) * 1000, 2),
            "control": "lock" if use_lock else "none",
        }

    # Buduje komenda Pythona wykonujaca kontrolowane obciazenie CPU
    def cpu_burn_command(duration_seconds):
        script = (
            "import math,time\n"
            f"end=time.perf_counter()+{duration_seconds}\n"
            "value=0.0\n"
            "while time.perf_counter()<end:\n"
            "    for i in range(10000):\n"
            "        value += math.sqrt((i % 97) + 1)\n"
        )
        return [sys.executable, "-c", script]

    # Usuwa zakonczone procesy testu CPU i aktualizuje status testu
    def cleanup_finished_cpu_processes():
        with cpu_test_lock:
            processes = cpu_test_state["processes"]
            alive = [process for process in processes if process.poll() is None]
            finished_count = len(processes) - len(alive)
            cpu_test_state["processes"] = alive

            if cpu_test_state["running"] and not alive:
                cpu_test_state["running"] = False
                cpu_test_state["lastResult"] = {
                    "finishedAt": datetime.now().strftime("%H:%M:%S"),
                    "finishedProcesses": finished_count,
                    "message": "Test CPU zakonczony.",
                }

    # Demon pilnujacy czasu trwania testu CPU
    def watch_cpu_test():
        while True:
            cleanup_finished_cpu_processes()
            with cpu_test_lock:
                running = cpu_test_state["running"]
                ends_at = cpu_test_state["endsAt"]
                processes = list(cpu_test_state["processes"])

            if not running:
                return

            if ends_at is not None and time.time() >= ends_at:
                for process in processes:
                    if process.poll() is None:
                        process.terminate()
                cleanup_finished_cpu_processes()
                return

            time.sleep(0.25)

    # Zwraca status testu CPU bez nieserializowalnych obiektow procesow
    def get_cpu_test_public_state():
        cleanup_finished_cpu_processes()
        with cpu_test_lock:
            remaining = 0
            if cpu_test_state["running"] and cpu_test_state["endsAt"]:
                remaining = max(0, round(cpu_test_state["endsAt"] - time.time(), 1))
            return {
                "running": cpu_test_state["running"],
                "cores": cpu_test_state["cores"],
                "durationSeconds": cpu_test_state["durationSeconds"],
                "startedAt": cpu_test_state["startedAt"],
                "remainingSeconds": remaining,
                "activeProcesses": len(cpu_test_state["processes"]),
                "maxCores": os.cpu_count() or 1,
                "maxDurationSeconds": MAX_CPU_TEST_SECONDS,
                "lastResult": cpu_test_state["lastResult"],
            }

    @testing.route("/concurrency-demo")

    # [GET] /concurrency-demo porownuje race condition przed i po uzyciu locka
    def concurrency_demo():
        started_at = time.perf_counter()
        unsafe = run_race_demo(use_lock=False)
        safe = run_race_demo(use_lock=True)
        instrumentation = create_instrumentation("/concurrency-demo", started_at)

        return jsonify({
            "phenomenon": "race condition",
            "before": unsafe,
            "after": safe,
            "summary": {
                "beforeLostUpdates": unsafe["lostUpdates"],
                "afterLostUpdates": safe["lostUpdates"],
                "improvement": unsafe["lostUpdates"] - safe["lostUpdates"],
            },
            "instrumentation": instrumentation,
        })

    @testing.route("/cpu-test", methods=["POST"])

    # [POST] /cpu-test uruchamia kontrolowany test obciazenia CPU"
    def start_cpu_test():
        payload = request.get_json(silent=True) or {}
        max_cores = os.cpu_count() or 1
        cores = int(payload.get("cores", 1))
        duration_seconds = int(payload.get("durationSeconds", 10))
        cores = max(1, min(cores, max_cores))
        duration_seconds = max(1, min(duration_seconds, MAX_CPU_TEST_SECONDS))

        with cpu_test_lock:
            if cpu_test_state["running"]:
                remaining = 0
                if cpu_test_state["endsAt"]:
                    remaining = max(0, round(cpu_test_state["endsAt"] - time.time(), 1))
                status = {
                    "running": True,
                    "cores": cpu_test_state["cores"],
                    "durationSeconds": cpu_test_state["durationSeconds"],
                    "startedAt": cpu_test_state["startedAt"],
                    "remainingSeconds": remaining,
                    "activeProcesses": len(cpu_test_state["processes"]),
                    "maxCores": max_cores,
                    "maxDurationSeconds": MAX_CPU_TEST_SECONDS,
                    "lastResult": cpu_test_state["lastResult"],
                }
                return jsonify({"error": "Test CPU juz trwa.", "status": status}), 409

            processes = [
                subprocess.Popen(
                    cpu_burn_command(duration_seconds),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                for _ in range(cores)
            ]

            now = time.time()
            cpu_test_state.update({
                "running": True,
                "cores": cores,
                "durationSeconds": duration_seconds,
                "startedAt": datetime.now().strftime("%H:%M:%S"),
                "endsAt": now + duration_seconds,
                "processes": processes,
                "lastResult": None,
            })

        Thread(target=watch_cpu_test, name="cpu-test-watchdog", daemon=True).start()
        return jsonify(get_cpu_test_public_state())

    @testing.route("/cpu-test/status")

    # [GET] /cpu-test/status zwraca biezacy status testu CPU
    def cpu_test_status():
        return jsonify(get_cpu_test_public_state())

    return testing
