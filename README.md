# ICU Alarm Dashboard
![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![Flask](https://img.shields.io/badge/flask-%23000.svg?style=for-the-badge&logo=flask&logoColor=white)
![JavaScript](https://img.shields.io/badge/javascript-%23323330.svg?style=for-the-badge&logo=javascript&logoColor=%23F7DF1E)
![HTML5](https://img.shields.io/badge/html5-%23E34F26.svg?style=for-the-badge&logo=html5&logoColor=white)
![CSS3](https://img.shields.io/badge/css3-%231572B6.svg?style=for-the-badge&logo=css3&logoColor=white)
## Informacje o projekcie

**Przedmiot:** Rozwój aplikacji internetowych w medycynie  
**Autorzy:** Patryk Majewski, Wiktor Gnaczyński  
**Indeksy:** 198021, 198387  
**Rok studiów:** 3  
**Prowadzący:** dr inż. Anna Jezierska  
**Uczelnia:** Politechnika Gdańska – Katedra Inżynierii Biomedycznej

---

## Cel projektu

Celem projektu jest stworzenie aplikacji webowej symulującej system monitorowania pacjenta na oddziale intensywnej terapii (ICU), ze szczególnym uwzględnieniem:

* generowania alarmów medycznych w czasie rzeczywistym
* analizy przeciążenia systemu (system overload)
* badania wpływu opóźnień na prezentację alarmów
* implementacji mechanizmów harmonogramowania zadań (task scheduling)

Projekt realizowany jest etapowo – niniejsza wersja obejmuje **Etap 1 – implementację bazową**.

---

## Architektura systemu

Aplikacja została zaprojektowana w architekturze klient-serwer:

### 🔹 Backend

* Python + Flask
* generowanie danych pacjenta (symulacja)
* logika wykrywania alarmów

### 🔹 Frontend

* HTML + JavaScript
* wizualizacja danych pacjenta
* prezentacja alarmów

### 🔹 Komunikacja

* REST API (HTTP)
* endpoint `/data` zwracający aktualne dane i alarmy

---

## Implementacja alarmu progowego

Przykładowe reguły:

* HR > 100 → alarm „HIGH HR”
* SpO₂ < 90 → alarm „LOW SpO₂”

---

## Funkcjonalności aplikacji

* symulacja danych pacjenta w czasie rzeczywistym
* wykrywanie stanów alarmowych
* wyświetlanie aktualnych parametrów
* wyświetlanie wykresów trendu parametrów
* lista aktywnych alarmów
* testy kontrolne aplikacji

---

## Cel projektu (Etap 1)
Celem niniejszego etapu jest stworzenie stabilnej bazy systemu, obejmującej:
* Generowanie danych pacjenta (HR, SpO2).
* Implementację alarmu progowego:
    * **HR > 100** → "HIGH HR"
    * **SpO₂ < 90** → "LOW SpO₂"
* Prezentację danych w czasie rzeczywistym na dashboardzie.

---

## Omówienie teoretyczne zaburzeń (Etap 2)

### 1. Przeciążenie systemu (System Overload)

Przeciążenie systemu występuje w sytuacji, gdy liczba generowanych zdarzeń przekracza możliwości ich przetwarzania przez system. W środowisku ICU może to prowadzić do opóźnień w prezentacji alarmów oraz utraty aktualności danych pacjenta.

W systemach czasu rzeczywistego przeciążenie może skutkować:
* wzrostem opóźnień,
* pomijaniem alarmów,
* spadkiem responsywności dashboardu,
* zwiększonym wykorzystaniem CPU.

---

### 2. Burst alarmów

Burst alarmów oznacza nagłe pojawienie się dużej liczby alarmów w krótkim czasie. W środowisku szpitalnym może to wystąpić np. podczas awarii urządzeń lub pogorszenia stanu wielu pacjentów jednocześnie.

Konsekwencje:
* przeciążenie interfejsu użytkownika,
* alarm fatigue,
* wydłużenie czasu reakcji personelu.

---

### 3. Opóźnienia (Latency)

Latency oznacza czas pomiędzy wygenerowaniem alarmu a jego wyświetleniem użytkownikowi. W systemach ICU minimalizacja opóźnień jest kluczowa, ponieważ alarmy dotyczą stanów zagrożenia życia.

Źródła opóźnień:
* przetwarzanie backendu,
* komunikacja sieciowa,
* renderowanie frontendowe,
* przeciążenie CPU.

---

### 4. Harmonogramowanie zadań (Task Scheduling)

Task scheduling odnosi się do mechanizmów decydujących o kolejności obsługi alarmów. W systemach medycznych nie wszystkie alarmy mają taki sam priorytet – alarm krytyczny powinien zostać obsłużony szybciej niż alarm ostrzegawczy.

Brak odpowiedniego harmonogramowania może prowadzić do:
* opóźnienia alarmów krytycznych,
* blokowania systemu przez alarmy niskiego priorytetu,
* obniżenia bezpieczeństwa pacjentów.

---

## Etap 3 - Wspolbieznosc i analiza bledow

W aktualnej wersji system monitoruje 3 oddzialy ICU po 20 pacjentow. Dane pacjentow sa aktualizowane w tle przez watki-demony, a frontend cyklicznie odpytuje endpoint `/patients`. Taki model dobrze pasuje do dashboardu alarmowego, ale wymaga kontroli wspoldzielonego stanu.

### Wybrane zagadnienia wspolbieznosci

* **Race condition** - blad, w ktorym kilka watkow jednoczesnie odczytuje i zapisuje te same dane. W dashboardzie mogloby to spowodowac niespojna liczbe alarmow albo odczyt pacjenta z poprzedniej iteracji symulacji.
* **Lock / mutex** - mechanizm wzajemnego wykluczania. W projekcie blokady chronia snapshoty pacjentow, metryki instrumentacji i stan testu CPU.
* **Buforowanie** - backend nie liczy danych pacjentow w trakcie requestu HTTP. Watki oddzialow wpisuja gotowe snapshoty do cache, a API wykonuje szybki odczyt z pamieci.
* **Kolejka producent-konsument** - watki symulacji produkuja logi pacjentow, a osobny demon zapisuje je batchowo do SQLite. Dzieki temu zapis do bazy nie blokuje symulacji oddzialow.
* **Drift i jitter** - przy odswiezaniu co 1 sekunde opoznienia moga narastac, gdy system jest obciazony. Dashboard mierzy latency i jitter, a przy przekroczeniu progow pokazuje ostrzezenie o ryzyku nieaktualnych danych.

### Progi opoznien

W dashboardzie zaimplementowano nastepujace progi oceny czytelnosci danych:

| Metryka | OK | Ostrzezenie | Krytyczne |
| --- | --- | --- | --- |
| Backend latency | < 50 ms | 50-100 ms | > 100 ms |
| Client latency | < 100 ms | 100-150 ms | > 150 ms |
| Server jitter | < 20 ms | 20-30 ms | > 30 ms |
| UI jitter | < 16 ms | >= 16 ms | > 16 ms |

Przekroczenia sa oznaczane kolorami w panelu instrumentacji. Dodatkowo nad wykresami pojawia sie ostrzezenie, gdy ktorykolwiek z progow moze utrudnic poprawny odczyt danych pacjentow.

### Demonstracja zjawiska wspolbieznosci

Endpoint `/concurrency-demo` uruchamia kontrolowana demonstracje `race condition`:

* wariant **przed poprawka** zwieksza wspolny licznik w wielu watkach bez locka,
* wariant **po poprawce** wykonuje te sama operacje z blokada `Lock`,
* wynik pokazuje wartosc oczekiwana, wartosc uzyskana i liczbe utraconych aktualizacji.

Demonstracje mozna uruchomic z panelu **Etap 3: Wspolbieznosc i test CPU** przyciskiem `Uruchom porownanie`.

### Mechanizmy kontroli zaimplementowane w aplikacji

* `snapshot_lock` - chroni wspolny cache snapshotow pacjentow i statusow oddzialow.
* `instrumentation_lock` - chroni licznik requestow i pomiar jittera.
* `cpu_test_lock` - chroni status testu CPU, aby nie uruchomic dwoch testow naraz.
* `Queue` - buforuje logi pacjentow miedzy watkami symulacji a demonem zapisu do bazy.
* batchowy zapis logow - ogranicza liczbe transakcji SQLite i zmniejsza ryzyko blokowania symulacji.

### Porownanie przed i po poprawce

W demonstracji race condition porownywane sa dwa warianty:

| Wariant | Mechanizm | Oczekiwany efekt |
| --- | --- | --- |
| Przed poprawka | brak locka | licznik moze byc mniejszy od oczekiwanego, bo watki nadpisuja swoje aktualizacje |
| Po poprawce | `Lock` | licznik powinien zgadzac sie z wartoscia oczekiwana |

Dodatkowo aplikacja ma test CPU na zywo. Uzytkownik wybiera liczbe rdzeni oraz czas testu. Backend uruchamia osobne procesy obciazajace CPU, a dashboard pokazuje, jak zmieniaja sie opoznienia, jitter i ostrzezenia o wiarygodnosci odczytu.

---

## Instrukcja uruchomienia

### 1. Klonowanie repozytorium

```bash
git clone https://github.com/Maj20PL/RAIM-aplikacja-Dashboard-alarmowy-ICU.git
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
python backend/main.py
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
dashboard-icu/
│
├── backend/
│   ├── main.py
│   ├── symulacja.py
│   ├── models.py
    ├── testing_tools.py
│   └── mitdb/
│
├── frontend/             
│   ├── index.html
│   ├── script.js
│   └── style.css
│
├── icu_database.db
└── requirements.txt     
