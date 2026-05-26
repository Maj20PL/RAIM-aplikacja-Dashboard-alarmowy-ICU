import os
from threading import Lock

import numpy as np
import wfdb
from scipy.signal import find_peaks


class Symulacja:
    """Symulator odczytujacy sygnal EKG z MITDB i generujacy parametry zyciowe."""

    _record_cache = {}
    _cache_lock = Lock()

    def __init__(self, record_name="100"):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.db_path = os.path.join(base_dir, "mitdb")
        self.record_name = record_name
        self.signal, self.fs = self._load_record(record_name)

        self.current_sample = 0
        self.window_size = 1000
        self.spo2 = 98.0

    def _load_record(self, record_name):
        """
        Wczytuje rekord MITDB tylko raz na nazwe rekordu.
        Wielu pacjentow moze korzystac z tego samego sygnalu, ale kazdy ma wlasny offset.
        """

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

    def ustaw_offset(self, offset):
        """Ustawia punkt startowy pacjenta w sygnale, aby pacjenci nie byli zsynchronizowani."""

        max_start = max(0, len(self.signal) - self.window_size - 1)
        self.current_sample = min(offset % max(1, max_start), max_start)

    def pobierz_dane(self):
        """Zwraca aktualne HR, SpO2 i liste alarmow dla jednego okna sygnalu."""

        end_idx = self.current_sample + self.window_size
        segment = self.signal[self.current_sample:end_idx]

        peaks, _ = find_peaks(segment, distance=self.fs * 0.4, height=0.5)

        if len(peaks) > 1:
            avg_rr = np.mean(np.diff(peaks))
            hr = (60 * self.fs) / avg_rr
        else:
            hr = 72.0

        self.current_sample += int(self.fs)
        if self.current_sample > len(self.signal) - self.window_size:
            self.current_sample = 0

        if hr > 110:
            self.spo2 -= 0.1
        elif self.spo2 < 98:
            self.spo2 += 0.05

        return {
            "hr": round(hr, 1),
            "spo2": round(self.spo2, 1),
            "alarms": self.sprawdz_alarmy(hr, self.spo2),
        }

    def sprawdz_alarmy(self, hr, spo2):
        """Proste reguly progowe alarmow medycznych."""

        alarms = []
        if hr > 100:
            alarms.append("HIGH HR")
        if hr < 60:
            alarms.append("LOW HR")
        if spo2 < 90:
            alarms.append("LOW SpO2")
        return alarms
