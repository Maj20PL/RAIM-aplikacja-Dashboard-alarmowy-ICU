import os
import random
import time
from threading import Lock
import numpy as np
import wfdb
from scipy.signal import find_peaks


class Symulacja:
    _record_cache = {}
    _annotation_cache = {}
    _cache_lock = Lock()

    def __init__(self, record_name="100"):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.db_path = os.path.join(base_dir, "mitdb")
        self.record_name = record_name

        self.signal, self.fs = self._load_record(record_name)
        self.annotation = self._load_annotation(record_name)
        self.ann_index = 0

        self.current_sample = 0
        self.window_size = 1000

        self.spo2 = 97.5
        self.base_spo2 = 97.5
        self.spo2_trend = 0.0
        self.desat_timer = random.randint(20, 40)
        self.desat_duration = 0

    def _load_record(self, record_name):
        with self._cache_lock:
            if record_name in self._record_cache:
                return self._record_cache[record_name]

            try:
                local_record = os.path.join(self.db_path, record_name)
                if os.path.exists(f"{local_record}.dat"):
                    record = wfdb.rdrecord(local_record)
                else:
                    print(f"Brak plikow lokalnych w {self.db_path}, pobieranie z PhysioNet...")
                    record = wfdb.rdrecord(record_name, pn_dir="mitdb")

                signal = record.p_signal[:, 0]
                fs = record.fs
            except Exception as exc:
                print(f"Krytyczny blad symulatora dla rekordu {record_name}: {exc}")
                signal = np.random.normal(0.7, 0.1, 10000)
                fs = 360

            self._record_cache[record_name] = (signal, fs)
            return signal, fs

    def _load_annotation(self, record_name):
        with self._cache_lock:
            if record_name in self._annotation_cache:
                return self._annotation_cache[record_name]

            try:
                local_record = os.path.join(self.db_path, record_name)
                if os.path.exists(f"{local_record}.atr") or os.path.exists(f"{local_record}.dat"):
                    annotation = wfdb.rdann(local_record, "atr")
                else:
                    annotation = wfdb.rdann(record_name, "atr", pn_dir="mitdb")
            except Exception:
                annotation = None

            self._annotation_cache[record_name] = annotation
            return annotation

    def ustaw_offset(self, offset):
        max_start = max(0, len(self.signal) - self.window_size - 1)
        self.current_sample = min(offset % max(1, max_start), max_start)

    def pobierz_dane(self):
        end_idx = self.current_sample + self.window_size
        if end_idx > len(self.signal):
            self.current_sample = 0
            end_idx = self.window_size

        segment = self.signal[self.current_sample:end_idx]
        self.current_sample += int(self.fs)

        if self.current_sample > len(self.signal) - self.window_size:
            self.current_sample = 0

        peaks, _ = find_peaks(segment, distance=self.fs * 0.4, height=np.max(segment) * 0.5)
        if len(peaks) > 1:
            hr = (60 * self.fs) / np.mean(np.diff(peaks))
        else:
            hr = 72.0

        noise = random.uniform(-0.15, 0.15)

        self.desat_timer -= 1
        if self.desat_timer <= 0 and self.desat_duration == 0:
            self.desat_duration = random.randint(4, 8)
            self.desat_timer = int(np.random.exponential(scale=60.0))

        if self.desat_duration > 0:
            self.desat_duration -= 1
            self.spo2_trend = -1.5
        elif hr > 110 or hr < 55:
            self.spo2_trend = -0.1
        else:
            if self.spo2 < self.base_spo2:
                self.spo2_trend = 0.4
            else:
                self.spo2_trend = 0.0

        self.spo2 += self.spo2_trend + noise
        self.spo2 = max(72.0, min(100.0, self.spo2))

        alarms = self.sprawdz_alarmy(hr, self.spo2)

        if self.annotation:
            start_sample = self.current_sample - int(self.fs)
            end_sample = self.current_sample
            while self.ann_index < len(self.annotation.sample) and self.annotation.sample[self.ann_index] < end_sample:
                ann_sample = self.annotation.sample[self.ann_index]
                if ann_sample >= start_sample:
                    symbol = self.annotation.symbol[self.ann_index]
                    if symbol in ["V", "F", "L", "R"]:
                        alarms.append(f"HIGH: ARRYTHMIA ({symbol})")
                self.ann_index += 1

        return {
            "hr": round(hr, 1),
            "spo2": round(self.spo2, 1),
            "alarms": alarms,
            "generated_at": time.perf_counter(),
        }

    def sprawdz_alarmy(self, hr, spo2):
        alarms = []
        if spo2 < 85:
            alarms.append("CRITICAL: LOW SpO2")
        if hr < 40 or hr > 140:
            alarms.append("CRITICAL: EXTREME HR")
        if 85 <= spo2 < 92:
            alarms.append("HIGH: ABNORMAL SpO2")
        if (100 < hr <= 140) or (40 <= hr < 60):
            alarms.append("HIGH: ABNORMAL HR")
        return alarms
