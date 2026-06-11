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

## Etap 4 - Wnioski z pracy i analiza kompromisów implementacyjnych

Ostatni etap projektu polegał na ocenie gotowej aplikacji jako systemu medycznego, 
w którym samo poprawne wyswietlenie danych nie wystarcza. 
Dashboard alarmowy ICU musi byc analizowany pod kątem aktualności danych, 
priorytetów alarmów, stabilności pod obciażeniem oraz czytelności informacji dla personelu medycznego.

### Najwazniejsze wnioski

* System czasu rzeczywistego powinien jawnie mierzyc opoznienia, a nie tylko zakladac, ze dane sa aktualne. W projekcie dlatego dodaliśmy pomiar backend latency, client latency, server jitter i UI jitter.
* Cache snapshotów pacjentów poprawia wydajnosc endpointow API, ale wymaga blokad (Lock), aby frontend nie otrzymał niespojnego stanu kilku watkow symulacji.
* Oddzielenie symulacji od zapisu do SQLite przez kolejke producent-konsument zmniejsza ryzyko blokowania odświeżania danych przez operacje bazodanowe.
* Priorytety alarmów są konieczne, poniewaz nie kazdy alarm ma taka sama wagę kliniczną. Alarmy krytyczne musza byc widoczne szybciej i wyraźniej niz ostrzeżenia aby personel mógł na nie szybko reagować.
* Test obciazenia CPU pokazuje, ze sama funkcjonalnośc aplikacji nie gwarantuje bezpieczenstwa. Przy wysokim obciazeniu dane moga byc opóźnione, a dashboard powinien informowac użytkownika o ryzyku nieaktualnego odczytu.

### Analiza decyzji implementacyjnych

| Decyzja | Korzysc | Koszt / ryzyko | Ocena kompromisu |
| --- | --- | --- | --- |
| Odczyt danych z cache zamiast liczenia ich w kazdym requescie | Krotki czas odpowiedzi API i mniejsze obciażenie backendu | Dane moga miec maksymalnie ok. 1 s | Dopuszczalne, bo interwal jest znany, a system pokazuje czas aktualizacji i ostrzezenia opóźnień |
| Blokady Lock dla snapshotow i metryk | Spojnosc danych wspoldzielonych miedzy wątkami | Minimalny narzut czasowy i ryzyko kolejkowania wątków | Dopuszczalne, bo spojnosc danych medycznych jest ważniejsza niz mikrooptymalizacja |
| Batchowy zapis logow do SQLite | Mniej transakcji i mniejsze blokowanie symulacji | Log historyczny może zostac zapisany z niewielkim opóżnieniem | Dopuszczalne, bo historia jest mniej krytyczna niz aktualny alarm na dashboardzie |
| Wiele wątków symulacji oddziałów | Lepsze odwzorowanie pracy kilku oddzialow ICU | Wymaga kontroli race condition i synchronizacji | Dopuszczalne przy zastosowaniu blokad i testow demonstracyjnych |
| Progi opoznien i ostrzeżenia w UI | Użytkownik widzi, kiedy dane moga być mniej wiarygodne | Interfejs staje sie bardziej zlożony | Dopuszczalne, bo w aplikacji medycznej ukrycie opóznien byłoby bardzo niebezpieczne |
| Ograniczony czas i liczba rdzeni w tescie CPU | Chroni komputer przed niekontrolowanym obciazeniem | Test nie odwzorowuje pełnego środowiska produkcyjnego | Dopuszczalne w projekcie edukacyjnym, bo pokazuje trend bez nadmiernego ryzyka |

### Opóźnienia a spójność danych

W projekcie przyjeto, ze lepiej pokazać spójny snapshot z niewielkim opóznieniem niz szybki, ale niespojny zestaw danych. Gdyby endpoint /patients czytał dane w trakcie aktualizacji przez watki symulacji, użytkownik mógłby zobaczyć np. liczbe alarmów z jednej chwili, a parametry pacjentów z innej. Taki błąd jest trudny do wykrycia, a w systemie medycznym może prowadzic do złej interpretacji sytuacji.

Zastosowany kompromis polega na tym, ze:

* wątki symulacji aktualizują dane cyklicznie,
* API zwraca gotowy snapshot z pamięci,
* blokada chroni moment odczytu i zapisu,
* frontend pokazuje czas aktualizacji oraz ostrzeżenia, gdy opóźnienia przekraczaja ustalone progi.

Opoznienie rzedu pojedynczego interwału odswiezania jest akceptowalne w symulowanym dashboardzie, jezeli system jawnie informuje o czasie ostatniego odczytu. Niedopuszczalne byłoby natomiast ukrywanie opóznienia lub prezentowanie niespojnych danych jako aktualnych.

### Wydajnosc a bezpieczeństwo

Wydajnosc w aplikacji ICU jest ważna, ale nie może byc uzyskana kosztem bezpieczeństwa interpretacji danych. Najważniejsze dane alarmowe powinny być traktowane priorytetowo, nawet jezeli oznacza to dodatkowe obliczenia, walidacje lub synchronizacje.

Przykladowo:

* usuniecie blokad mogloby minimalnie przyspieszyc wykonanie kodu, ale groziłoby race condition,
* rzadsze odswieżanie zmniejszyłoby obciazenie API, ale pogorszyloby aktualnosc alarmów,
* częstrze odswiezanie poprawiłoby pozorną aktualność, ale mogloby zwiekszyc jitter i obciazenie CPU, nie mówiąc już o problemie nadążenia symulacji danych z bazy,
* pominięcie tworzenia logów poprawiłoby wydajność, ale utrudniłoby analizę zdarzeń.

Dlatego w projekcie wybrano rozwiazania umiarkowane: odświezanie co 1 sekunde, szybki odczyt z cache, kolejke do tworzenia logów, priorytety alarmow i widoczne metryki opóźnień.

### Kiedy programista jest świadom kompromisów implementacyjnych?

Programista jest świadom kompromisów wtedy, gdy potrafi wskazać nie tylko zalete zastosowanego rozwiazania, ale tez jego koszt i możliwe konsekwencje. W naszej aplikacji medycznej oznacza to szczególnie odpowiedzenie na pytania:

* czy dane sa aktualne, czy tylko ostatnio dostępne?
* czy poprawa wydajnosci nie obniża spójności lub wiarygodności danych?
* co stanie sie przy przeciążeniu CPU, sieci lub bazy danych?
* czy użytkownik zostanie poinformowany o opóźnieniu albo błędzie?
* które alarmy muszą mieć pierwszeństwo?
* czy system zachowa się przewidywalnie przy wielu jednoczesnych zdarzeniach?

### Jakie kompromisy są dopuszczalne?

Dopuszczalne są te, ktore nie ukrywają ryzyka przed użytkownikiem i nie naruszają podstawowej funkcji systemu, czyli bezpiecznej prezentacji alarmow. W naszym projekcie dopuszczalne są m.in.:

* niewielkie opóźnienie snapshotu, jeżeli jest mierzone i sygnalizowane,
* batchowy zapis danych historycznych, jeżeli aktualne alarmy pozostaja dostepne natychmiast z cache,
* ograniczenie szczegółów wykresu do ostatnich próbek, jeżeli poprawia to czytelność i wydajność UI,
* uproszczona symulacja SpO2 i HR z bazy MIT-BIH, jezeli jest traktowana jako model edukacyjny,
* lokalna baza SQLite, jeżeli projekt nie jest wdrożeniem produkcyjnym.

---

### Problemy napotkane w projekcie

Podczas tworzenia aplikacji pojawiło sie kilka problemów typowych dla systemów monitorowania danych w czasie zbliżonym do rzeczywistego:

* *Spójność danych przy wielu watkach* - po rozszerzeniu aplikacji do wielu oddzialow i pacjentow trzeba bylo kontrolować dostep do wspólnych struktur danych. Bez blokad mogły pojawiac się niespojne snapshoty, np. alarmy policzone dla innego momentu niz parametry pacjentow.
* *Ryzyko race condition* - równolegla praca watkow symulacji pokazala, ze pozornie proste operacje na wspólnym stanie moga prowadzić do utraty aktualizacji. Szczególnie niebezpieczny z powodu trudności wykrycia dla wielu pacjentów jednocześnie.
* *Obciażenie backendu* - symulowanie daych z bazy dla wielu pacjentow przy każdym zapytaniu HTTP było by bardzo nie optymalne (czas, możliwe opóźnienia i utrata pakietów). Problem rozwiazano przez cykliczne przygotowywanie snapshotow w tle i szybki odczyt z cache.
* *Zapis historii do bazy danych* - bezposredni zapis do SQLite w wątkach symulacji mogłby blokowac aktualizacje pacjentow. Wprowadzono kolejke logow i batchowy zapis, aby zmniejszyć liczbe jednoczesnych operacji.
* *Dobór progów opóźnień* - konieczne było ustalenie, kiedy opóźnienie jest jeszcze akceptowalne, a kiedy powinno byc pokazane jako ostrzezenie. Progi dobrano tak, aby były zrozumiałe w dashboardzie i widoczne podczas testu CPU.
* *Czytelność interfejsu przy wielu alarmach* - lista 60 pacjentow i wiele jednoczesnych alarmów mogłyby przeciażyc użytkownika. Dlatego dodano grupowanie po oddziałach, zwijanie sekcji oraz oznaczanie priorytetów alarmów.
* *Symulacja realistycznych danych medycznych* - samo losowanie HR i SpO2 byłoby mało wiarygodne, dlatego wykorzystaliśmy rekordy MIT-BIH dla sygnalu EKG oraz SpO2 (uproszczony model desaturacji). Nadal pozostaje to symulacja edukacyjna, a nie system diagnostyczny.
* *Testowanie przeciażenia* - trudno było pokazać problem opoźnien bez kontrolowanego obciażenia. Dodano test CPU, ale ograniczono czas i liczbe rdzeni, aby demonstracja nie byla niebezpieczna dla komputera (w przypadku noweczesnych sprzętów np. laptopów gamingowych mieliśmy problem z uzyskaniem z kolej takich przeciążeń)

Najwieksza trudność polegała na pogodzeniu prostoty projektu akademickiego (ograniczony czas, wiele projektów jednocześnie w semestrze) z wymaganiami charakterystycznymi dla aplikacji medycznych: aktualnością danych, czytelnym alarmowaniem, kontrolą opóźnień i unikaniem niepokojącego stanu systemu.

### Krótkie podsumowanie projektu

Najważniejszym wnioskiem z naszego projektu jest to, ze w aplikacjach medycznych decyzje implementacyjne maja bezpośredni wpływ na interpretacje danych. Wydajność, opóźnienia, synchronizacja i sposób prezentacji alarmów nie są detalami technicznymi, lecz elementami bezpieczeństwa pracy systemu. Dobry dashboard alarmowy powinien nie tylko szybko prezentować dane, ale też informować, kiedy ich aktualność lub wiarygodność może być ograniczona.

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
dashboard-icu/
│
├── backend/
│   ├── main.py           # Główny serwer Flask, obsługa endpointów i telemetrii
│   ├── symulacja.py      # Klasa iteratora (serce DSP i modelowania SpO2)
│   ├── models.py         # Definicje tabel bazy danych (SQLAlchemy)
│   └── mitdb/            # Lokalne pliki bazy MIT-BIH (.dat, .hea)
│
├── frontend/             
│   ├── index.html
│   ├── script.js
│   └── style.css
│
├── icu_database.db       # Baza danych SQLite (logi pacjentów)
└── requirements.txt     
