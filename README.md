# ICU Alarm Dashboard
![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![Flask](https://img.shields.io/badge/flask-%23000.svg?style=for-the-badge&logo=flask&logoColor=white)
![JavaScript](https://img.shields.io/badge/javascript-%23323330.svg?style=for-the-badge&logo=javascript&logoColor=%23F7DF1E)
![HTML5](https://img.shields.io/badge/html5-%23E34F26.svg?style=for-the-badge&logo=html5&logoColor=white)
![CSS3](https://img.shields.io/badge/css3-%231572B6.svg?style=for-the-badge&logo=css3&logoColor=white)
## Informacje o projekcie

<p align="center">
  <img src="https://upload.wikimedia.org/wikipedia/commons/8/8c/Logo_Pg_en.jpg" alt="Politechnika Gdańska" width="200"/>
  <br>
  <b>Politechnika Gdańska</b><br>
  Wydział Elektroniki, Telekomunikacji i Informatyki<br>
  Katedra Inżynierii Biomedycznej
</p>

**Przedmiot:** Rozwój aplikacji internetowych w medycynie  
**Autorzy:** Patryk Majewski, Wiktor Gnaczyński  
**Indeksy:** 198021, 198387  
**Rok studiów:** 3  
**Prowadzący:** dr inż. Anna Jezierska  
---

## Analiza potrzeb i wymagań klinicznych

### 1. Identyfikacja problemu
W systemach ICU monitoring odbywa się w sposób ciągły, a decyzje kliniczne podejmowane są w oparciu o dane czasu rzeczywistego. Każde opóźnienie w prezentacji danych lub alarmów może prowadzić do pogorszenia stanu pacjenta, dlatego systemy te muszą charakteryzować się wysoką niezawodnością i niską latencją.
Na oddziałach intensywnej terapii personel medyczny jest zalewany ogromną ilością danych z wielu urządzeń monitorujących jednocześnie. Kluczowym wyzwaniem jest:
* **Przeciążenie informacyjne:** Zbyt duża liczba bodźców utrudnia szybką reakcję.
* **Alarm Fatigue:** Ignorowanie sygnałów dźwiękowych/wizualnych z powodu ich nadmiaru.
* **Krytyczność czasu:** W stanach zagrożenia życia, każda sekunda opóźnienia w wyświetleniu alarmu ma znaczenie.

### 2. Określenie użytkowników
* **Lekarze intensywnej terapii:** Potrzebują szybkiego podglądu trendów parametrów życiowych do podejmowania decyzji diagnostycznych.
* **Personel pielęgniarski:** Główni odbiorcy alarmów, wymagający natychmiastowej i jednoznacznej informacji o przekroczeniu norm.

### 3. Analiza ryzyka

Systemy monitorowania pacjentów w środowisku ICU należą do systemów krytycznych, w których błędy mogą prowadzić do bezpośredniego zagrożenia życia. W związku z tym zbadano i zidentyfikowano następujące kategorie ryzyk:

#### Ryzyka systemowe
* **Przeciążenie systemu:** Duża liczba jednoczesnych alarmów lub pacjentów może prowadzić do spadku wydajności systemu i opóźnień w ich prezentacji.
* **Opóźnienia (latency):** Opóźnienie pomiędzy wygenerowaniem/pobraniem danych a ich wyświetleniem może skutkować nieaktualną oceną stanu pacjenta.
* **Jitter:** Nieregularność w dostarczaniu danych może zaburzyć interpretację  wykresów.
* **Utrata danych:** Pakiety danych mogą zostać utracone podczas transmisji.

#### Ryzyka związane z danymi
* **Niespójność danych:** Różnice między stanem rzeczywistym a prezentowanym mogą prowadzić do błędnych decyzji klinicznych.
* **Błędne progi alarmowe:** Nieprawidłowo dobrane wartości progowe mogą powodować brak alarmów lub ich nadmiar.
* **Dryft czasowy:** Różnice w czasie między backendem a frontendem mogą powodować błędne odwzorowanie danych na osi czasu.

#### Ryzyka użytkownika
* **Alarm fatigue:** Nadmiar alarmów prowadzi do ich ignorowania przez personel.
* **Nieczytelny interfejs:** Zbyt skomplikowany lub nieintuicyjny dashboard może wydłużyć czas reakcji.
* **Błędna interpretacja danych:** Użytkownik może źle zinterpretować wykresy lub wartości.

#### Ryzyka techniczne
* **Awaria backendu:** Brak możliwości generowania i udostępniania danych.
* **Brak komunikacji frontend-backend:** Utrata połączenia skutkuje brakiem aktualizacji danych.
* **Błędy implementacyjne:** Np. błędy w logice alarmów mogą generować fałszywe lub brakujące alarmy.

#### Ryzyka kliniczne
* **Fałszywie pozytywne alarmy:** Mogą prowadzić do niepotrzebnych interwencji.
* **Fałszywie negatywne alarmy:** Brak alarmu w sytuacji zagrożenia życia.
* **Opóźniona reakcja personelu:** Wynikająca z błędów systemowych lub przeciążenia informacyjnego.
---

## Projekt architektury systemu

Projekt realizowany jest w modelu **API First** z wyraźnym rozdziałem warstw:

1.  **Warstwa Generowania Danych:**
    * Niezależny moduł generujący parametry życiowe w czasie rzeczywistym.
3.  **Warstwa Logiki i Serwera:**
    * Przechowywanie aktualnych wyników.
    * **Silnik alarmów:** Porównywanie danych z zadanymi progami medycznymi.
    * Udostępnianie danych przez endpoint REST API `/data`.
4.  **Warstwa Prezentacji (Frontend - JS/HTML):**
    * Cykliczne pobieranie danych (polling).
    * Wizualizacja trendów na wykresach (Chart.js).
    * Moduł powiadomień o aktywnych alarmach.

### Schemat przepływu danych

[Generator danych/Baza danych] → [Backend Flask + logika alarmów] → [REST API] → [Frontend]

1. Generator tworzy dane pacjenta (lub pobierane one są z bazy danych)
2. Backend analizuje dane i wykrywa alarmy
3. Dane są udostępniane przez API
4. Frontend cyklicznie pobiera i wizualizuje dane
---

## Cel projektu (Etap 1)
Celem niniejszego etapu jest stworzenie stabilnej bazy systemu, obejmującej:
* Generowanie danych pacjenta (HR, SpO2).
* Implementację alarmu progowego:
    * **HR > 100** → "HIGH HR"
    * **SpO₂ < 90** → "LOW SpO₂"
* Prezentację danych w czasie rzeczywistym na dashboardzie.

---

## Technologie
* **Backend:** Python 3.13, Flask
* **Frontend:** HTML5, CSS3, JavaScript (Vanilla JS), Chart.js
* **Komunikacja:** REST API (JSON)

## Instrukcja uruchomienia

### 1. Klonowanie repozytorium

```bash
git clone https://github.com/your-repo/icu-dashboard.git
cd icu-dashboard
```

### 2. Utworzenie środowiska

```bash
python -m venv venv
```

Aktywacja:

Windows:

```bash
venv\Scripts\activate
```

Linux/Mac:

```bash
source venv/bin/activate
```

---

### 3. Instalacja zależności

```bash
pip install -r requirements.txt
```

---

### 4. Uruchomienie backendu

```bash
python -m backend.main
```

---

### 5. Uruchomienie frontendu

Otwórz plik:

```text
frontend/index.html
```

w przeglądarce.

---

## Demonstracja działania

Po uruchomieniu aplikacji:

* dane pacjenta są aktualizowane co 1 sekundę
* w przypadku przekroczenia progów pojawiają się alarmy
* alarmy są wyświetlane w interfejsie użytkownika

---

## 📁 Struktura projektu

```
icu-dashboard/
├── backend/
│   ├── main.py        # Główny serwer Flask
│   ├── simulacja.py   # Logika generowania danych
├── frontend/
│   ├── index.html     # Widok dashboardu
│   ├── script.js      # Logika pobierania danych i wykresy
│   └── styl.css       # Style interfejsu
├── requirements.txt   # Zależności projektu
└── README.md
