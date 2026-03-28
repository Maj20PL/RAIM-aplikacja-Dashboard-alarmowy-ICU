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
* lista aktywnych alarmów

---

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
python backend/app.py
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
│
├── backend/
│   ├── app.py
│   └── simulator.py
│
├── frontend/
│   ├── index.html
│   ├── script.js
│   └── style.css
│
└── requirements.txt
