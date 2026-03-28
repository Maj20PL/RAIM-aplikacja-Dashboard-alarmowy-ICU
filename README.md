# ICU Alarm Dashboard

## Informacje o projekcie

**Przedmiot:** Rozwój aplikacji internetowych w medycynie

**Autorzy:** Patryk Majewski, Wiktor Gnaczyński

**Indeksy** 198021, 198387

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

Niniejsza wersja obejmuje **Etap 1 – implementację bazową**.

---

## Sposób działania

Po uruchomieniu aplikacji:

* dane pacjenta są aktualizowane co 1 sekundę
* w przypadku przekroczenia progów pojawiają się alarmy
* alarmy są wyświetlane w interfejsie użytkownika
---

## Struktura projektu

```
icu-dashboard/
│
├── backend/
│   ├── app.py
│   └── simulator.py
│
└── frontend/
    ├── index.html
    ├── script.js
    └── style.css
```

### Backend

* Python + Flask
* generowanie danych pacjenta (symulacja)
* logika wykrywania alarmów

###  Frontend

* HTML + JavaScript
* wizualizacja danych pacjenta
* prezentacja alarmów

### Komunikacja

* REST API (HTTP)
* endpoint `/data` zwracający aktualne dane i alarmy
