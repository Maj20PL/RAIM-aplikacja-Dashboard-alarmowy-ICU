import wfdb
import numpy as np
import os
import random
import time
import logging
from scipy.signal import find_peaks

logger = logging.getLogger(__name__)


class Symulacja:
    def __init__(self, record_name='100'):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.db_path = os.path.join(base_dir, 'mitdb')
        self.record_name = record_name
        self.signal = None
        self.record = None
        self.annotation = None
        self.ann_index = 0

        # Ładowanie sygnału
        try:
            record_path = os.path.join(self.db_path, record_name)
            if not os.path.exists(f"{record_path}.hea"):
                raise FileNotFoundError(f"Record file not found: {record_path}.hea")
            
            self.record = wfdb.rdrecord(record_path)
            self.signal = self.record.p_signal[:, 0]
            self.fs = self.record.fs
            logger.info(f"Successfully loaded MIT-BIH record {record_name}: {len(self.signal)} samples, fs={self.fs}Hz")
        except FileNotFoundError as e:
            logger.warning(f"Record not found, generating synthetic signal: {e}")
            self.signal = np.random.normal(0.7, 0.1, 10000)
            self.fs = 360
        except Exception as e:
            logger.error(f"Error loading record {record_name}: {e}")
            self.signal = np.random.normal(0.7, 0.1, 10000)
            self.fs = 360

        # Ładowanie adnotacji dla alarmów arytmii
        try:
            annotation_path = os.path.join(self.db_path, record_name)
            self.annotation = wfdb.rdann(annotation_path, 'atr')
            self.ann_index = 0
            logger.info(f"Successfully loaded annotations for {record_name}: {len(self.annotation.symbol)} annotations")
        except FileNotFoundError:
            logger.warning(f"Annotation file not found for {record_name}")
            self.annotation = None
        except Exception as e:
            logger.warning(f"Error loading annotations for {record_name}: {e}")
            self.annotation = None

        self.current_sample = 0
        self.window_size = 1000

        # --- PARAMETRY REALIZMU SpO2 ---
        self.spo2 = 98.0
        self.spo2_trend = 0.0  # Kierunek zmian
        self.base_spo2 = 98.0  # "Zdrowy" poziom dla tego pacjenta
        self.high_hr_count = 0
        self.low_hr_count = 0
        self.bradycardia_severe = 0
        self.tachycardia_severe = 0
        self.desat_timer = random.randint(300, 600)  # Losowy czas do następnego desaturacji (5-10 min)
        self.desat_duration = 0
        self.prev_hr = 72.0  # Poprzednia wartość HR do śledzenia zmian
        self.hr_change_count = 0  # Licznik nagłych zmian HR

    def pobierz_dane(self):
        """Metoda pozwalająca traktować symulację jako strumień danych."""
        # Pobieranie segmentu EKG
        end_idx = self.current_sample + self.window_size
        if end_idx > len(self.signal):
            self.current_sample = 0  # Zapętlamy nagranie
            end_idx = self.window_size

        segment = self.signal[self.current_sample:end_idx]
        self.current_sample += int(self.fs)  # Przesunięcie o 1 sekundę

        # 1. ANALIZA HR (Z bazy MIT-BIH) - Improved peak detection
        try:
            # Normalize signal for better peak detection
            segment_normalized = (segment - np.mean(segment)) / (np.std(segment) + 1e-6)
            
            # Adaptive peak detection
            min_distance = max(int(self.fs * 0.4), 1)  # Minimum 0.4s between peaks
            min_height = np.percentile(np.abs(segment_normalized), 50)  # 50th percentile
            
            peaks, properties = find_peaks(segment_normalized, distance=min_distance, height=min_height)
            
            if len(peaks) > 1:
                # Calculate RR intervals and HR
                rr_intervals = np.diff(peaks) / self.fs  # Convert to seconds
                mean_rr = np.mean(rr_intervals)
                
                # Filter out aberrant intervals (>3s or <0.3s)
                valid_intervals = rr_intervals[(rr_intervals > 0.3) & (rr_intervals < 3.0)]
                
                if len(valid_intervals) > 0:
                    hr = 60.0 / np.mean(valid_intervals)
                    # Clamp HR to realistic range
                    hr = max(30.0, min(220.0, hr))
                else:
                    hr = 72.0
            else:
                hr = 72.0 + random.uniform(-5, 5)  # Fallback with more variation
        except Exception as e:
            logger.warning(f"Error in HR calculation: {e}")
            hr = 72.0

        # 2. MODELOWANIE SpO2 (Bardziej złożone i realistyczne)
        noise = random.uniform(-0.3, 0.3)  # Zwiększony szum pomiarowy czujnika
        
        # Śledzenie zmian HR
        hr_change = abs(hr - self.prev_hr)
        if hr_change > 10:  # Nagła zmiana HR
            self.hr_change_count += 1
        else:
            self.hr_change_count = max(0, self.hr_change_count - 1)
        self.prev_hr = hr
        
        # Severe tachycardia effect (>120 BPM)
        if hr > 120:
            self.tachycardia_severe += 1
            self.bradycardia_severe = max(0, self.bradycardia_severe - 1)
            if self.tachycardia_severe > 5:  # Sustained tachycardia
                self.spo2_trend -= 0.015  # Significant SpO2 drop
        # Severe bradycardia effect (<45 BPM)
        elif hr < 45:
            self.bradycardia_severe += 1
            self.tachycardia_severe = max(0, self.tachycardia_severe - 1)
            if self.bradycardia_severe > 5:  # Sustained bradycardia
                self.spo2_trend -= 0.012  # Hypoperfusion causes desaturation
        # Tachycardia (100-120)
        elif hr > 100:
            self.high_hr_count += 1
            if self.high_hr_count > 8:
                self.spo2_trend -= 0.008
        # Bradycardia (50-60)
        elif hr < 60:
            self.low_hr_count += 1
            if self.low_hr_count > 8:
                self.spo2_trend -= 0.006
        # Normal HR - recovery
        else:
            self.high_hr_count = max(0, self.high_hr_count - 1)
            self.low_hr_count = max(0, self.low_hr_count - 1)
            self.tachycardia_severe = max(0, self.tachycardia_severe - 1)
            self.bradycardia_severe = max(0, self.bradycardia_severe - 1)
            
            # Powrót do bazy (regeneracja)
            if self.spo2 < self.base_spo2:
                self.spo2_trend += 0.008  # Faster recovery in normal HR
            else:
                self.spo2_trend *= 0.92  # Fade out trend
        
        # Sudden HR changes can trigger desaturation
        if self.hr_change_count > 3:
            self.spo2_trend -= 0.02
            if self.hr_change_count > 10:
                self.desat_duration = max(self.desat_duration, 15)  # Force desaturation
        
        # Random desaturations (episodic hypoxemia - common in ICU)
        self.desat_timer -= 1
        if self.desat_timer <= 0 and self.desat_duration == 0:
            self.desat_duration = random.randint(8, 25)  # 8-25 seconds
            self.spo2_trend -= random.uniform(0.12, 0.35)
            self.desat_timer = random.randint(250, 600)  # 4-10 min intervals
        
        if self.desat_duration > 0:
            self.desat_duration -= 1
        
        # Apply trend with inertia (SpO2 doesn't change instantly)
        self.spo2 += (self.spo2_trend + noise) * 0.7  # 70% of trend applied per sample
        self.spo2 = max(70.0, min(100.0, self.spo2))
        
        # Decay trend back to baseline
        self.spo2_trend *= 0.94

        # 3. ALARMY - Realistic ICU alarm prioritization
        alarms = self.sprawdz_alarmy(hr, self.spo2)

        # Dodanie alarmów z adnotacji MIT-BIH
        if self.annotation:
            try:
                start_sample = self.current_sample - int(self.fs)  # Poprzednia sekunda
                end_sample = self.current_sample
                while self.ann_index < len(self.annotation.sample) and self.annotation.sample[self.ann_index] < end_sample:
                    ann_sample = self.annotation.sample[self.ann_index]
                    if ann_sample >= start_sample:
                        symbol = self.annotation.symbol[self.ann_index]
                        # Mapowanie symboli na alarmy arytmii
                        if symbol in ['V', 'F', 'L', 'R', 'B', 'a', 'J', 'S', 'e', 'j', 'n', 'E', '/', 'f', 'Q', '?']:
                            alarms.append(f"ARRHYTHMIA_{symbol}")
                        elif symbol == 'A':
                            alarms.append("ATRIAL_PREMIATURE")
                        elif symbol == '(':
                            alarms.append("PAUSE")
                    self.ann_index += 1
            except Exception as e:
                logger.warning(f"Error processing annotations: {e}")

        return {
            "hr": round(hr, 1),
            "spo2": round(self.spo2, 1),
            "alarms": alarms,
            "generated_at": time.perf_counter()
        }

    def sprawdz_alarmy(self, hr, spo2):
        """Alarm prioritization based on ICU standards"""
        alarms = []
        
        # CRITICAL ALARMS (life-threatening)
        if spo2 < 85:
            alarms.append("CRITICAL_LOW_SPO2")
        if hr < 40 or hr > 140:
            alarms.append("CRITICAL_HR")
        
        # HIGH PRIORITY ALARMS
        if 85 <= spo2 < 90:
            alarms.append("LOW_SPO2")
        if (100 <= hr < 120) or (60 <= hr < 70 and self.low_hr_count > 5):
            alarms.append("ABNORMAL_HR")
        if 40 <= hr < 50:
            alarms.append("SEVERE_BRADYCARDIA")
        if hr > 130:
            alarms.append("SEVERE_TACHYCARDIA")
        
        # MEDIUM PRIORITY ALARMS
        if self.hr_change_count > 5:
            alarms.append("RAPID_HR_CHANGE")
        
        return alarms