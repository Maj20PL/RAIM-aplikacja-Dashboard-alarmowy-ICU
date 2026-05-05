import wfdb
import numpy as np
import os
from scipy.signal import find_peaks


class Symulacja:
    def __init__(self, record_name='100'):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.db_path = os.path.join(base_dir, 'mitdb')
        self.record_name = record_name

        try:
            if os.path.exists(os.path.join(self.db_path, f"{record_name}.dat")):
                self.record = wfdb.rdrecord(os.path.join(self.db_path, record_name))
            else:
                print(f"Brak plików lokalnych w {self.db_path}, pobieranie z PhysioNet...")
                self.record = wfdb.rdrecord(record_name, pn_dir='mitdb')

            self.signal = self.record.p_signal[:, 0]
            self.fs = self.record.fs
        except Exception as e:
            print(f"Krytyczny błąd symulatora: {e}")
            self.signal = np.random.normal(0.7, 0.1, 10000)
            self.fs = 360

        self.current_sample = 0
        self.window_size = 1000
        self.spo2 = 98.0

    def pobierz_dane(self):
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
            "alarms": self.sprawdz_alarmy(hr, self.spo2)
        }

    def sprawdz_alarmy(self, hr, spo2):
        alarms = []
        if hr > 100: alarms.append("HIGH HR")
        if hr < 60: alarms.append("LOW HR")
        if spo2 < 90: alarms.append("LOW SpO2")
        return alarms