// STAN APLIKACJI I KONFIGURACJA
const patientSeries = {}; // Przechowuje dane historyczne (HR, SpO2) dla wykresów każdego pacjenta
const maxPoints = 20; // Maksymalna liczba punktów danych widoczna na wykresach
const expectedPollIntervalMs = 1000; // Oczekiwany interwał odpytywania serwera (1 sekunda)
const telemetryLogs = []; // Tablica przechowująca historię logów telemetrii
let selectedPatientId = null; // ID aktualnie wybranego pacjenta (do wyświetlania szczegółów)
let lastClientPollStartedAt = null; // Czas rozpoczęcia ostatniego zapytania (do obliczania opóźnień)

// REFERENCJE DO ELEMENTÓW DOM (HTML)
const patientGrid = document.getElementById("patientGrid"); // Kontener na kafelki pacjentów
const globalAlert = document.getElementById("globalAlert"); // Pasek globalnego statusu (alarm/normal)
const globalStatus = document.getElementById("globalStatus"); // Tekst globalnego statusu
const globalAlarmCount = document.getElementById("globalAlarmCount"); // Licznik wszystkich alarmów
const patientCount = document.getElementById("patientCount"); // Licznik monitorowanych pacjentów
const selectedPatientLabel = document.getElementById("selectedPatientLabel"); // Etykieta wybranego pacjenta w szczegółach
const instrumentationRequest = document.getElementById("instrumentationRequest"); // Informacje o żądaniu (telemetria)
const backendLatency = document.getElementById("backendLatency"); // Opóźnienie backendu
const clientLatency = document.getElementById("clientLatency"); // Czas trwania żądania od przeglądarki do serwera (round-trip)
const serverJitter = document.getElementById("serverJitter"); // Odchylenie czasu odpowiedzi serwera
const clientJitter = document.getElementById("clientJitter"); // Odchylenie czasu zapytania klienta
const telemetryLog = document.getElementById("telemetryLog"); // Lista logów telemetrii

// KONFIGURACJA WYKRESÓW
const sharedChartOptions = {
    responsive: false,
    maintainAspectRatio: false,
    animation: false,
    plugins: {
        legend: { display: false }
    }
};

// Inicjalizacja wykresu tętna (HR)
const hrChart = new Chart(document.getElementById("hrChart"), {
    type: "line",
    data: {
        labels: [],
        datasets: [{
            label: "HR",
            data: [],
            borderColor: "#ff5c5c",
            backgroundColor: "rgba(255,92,92,0.14)",
            fill: true,
            tension: 0.3, // Zakrzywienie linii wykresu
            pointRadius: 2,
            borderWidth: 2
        }]
    },
    options: {
        ...sharedChartOptions,
        scales: {
            y: {
                min: 40,
                max: 160 // Stały zakres osi Y dla tętna
            }
        }
    }
});

// Inicjalizacja wykresu saturacji (SpO2)
const spo2Chart = new Chart(document.getElementById("spo2Chart"), {
    type: "line",
    data: {
        labels: [],
        datasets: [{
            label: "SpO2",
            data: [],
            borderColor: "#54d3ff",
            backgroundColor: "rgba(84,211,255,0.16)",
            fill: true,
            tension: 0.3,
            pointRadius: 2,
            borderWidth: 2
        }]
    },
    options: {
        ...sharedChartOptions,
        scales: {
            y: {
                min: 70,
                max: 102 // Stały zakres osi Y dla saturacji
            }
        }
    }
});

// FUNKCJE POMOCNICZE I PRZETWARZANIE DANYCH
function getSeries(patientId) {
    if (!patientSeries[patientId]) {
        patientSeries[patientId] = {
            labels: [],
            hr: [],
            spo2: []
        };
    }
    return patientSeries[patientId];
}

// Dodaje nowy punkt danych pacjenta do jego historii wykresów
function appendPatientPoint(patient) {
    const series = getSeries(patient.patientId);
    series.labels.push(patient.updatedAt);
    series.hr.push(patient.hr);
    series.spo2.push(patient.spo2);

    // Usuwanie najstarszych danych, jeśli przekroczono limit punktów na wykresie
    if (series.labels.length > maxPoints) {
        series.labels.shift();
        series.hr.shift();
        series.spo2.shift();
    }
}

// FUNKCJE RENDERUJĄCE
// Aktualizuje dane i odświeża wykresy dla wybranego pacjenta
function renderCharts(patientId) {
    const series = getSeries(patientId);
    hrChart.data.labels = series.labels;
    hrChart.data.datasets[0].data = series.hr;
    spo2Chart.data.labels = series.labels;
    spo2Chart.data.datasets[0].data = series.spo2;
    hrChart.update();
    spo2Chart.update();
}

// Tworzy i wyświetla kafelki dla wszystkich pacjentów na liście po lewej stronie
function renderPatientCards(patients) {
    patientGrid.innerHTML = ""; // Czyszczenie aktualnej listy

    patients.forEach(patient => {
        const button = document.createElement("button");
        button.type = "button";
        // Nadanie klas w zależności od statusu (alarm/normal)
        button.className = `patient-card ${patient.status === "ALARM" ? "alarm" : "normal"}`;
        
        // Zaznaczenie aktualnie wybranego pacjenta na liście
        if (patient.patientId === selectedPatientId) {
            button.classList.add("selected");
        }
        button.dataset.patientId = patient.patientId;

        // Struktura HTML pojedynczego kafelka pacjenta
        button.innerHTML = `
            <span class="patient-topline">
                <strong>${patient.bed}</strong>
                <span>${patient.status}</span>
            </span>
            <span class="patient-name">${patient.patientName}</span>
            <span class="patient-vitals">
                <span>HR ${patient.hr}</span>
                <span>SpO2 ${patient.spo2}%</span>
            </span>
        `;

        // Obsługa kliknięcia kafelka - zmiana wybranego pacjenta
        button.addEventListener("click", () => {
            selectedPatientId = patient.patientId;
            renderSelectedPatient(patient); // Aktualizacja panelu szczegółów
            renderPatientCards(patients); // Odświeżenie kafelków (aby zaktualizować zaznaczenie)
            renderCharts(patient.patientId); // Przełączenie wykresów na nowego pacjenta
        });

        patientGrid.appendChild(button);
    });
}

// Aktualizuje środkowy panel (szczegóły) danymi aktualnie wybranego pacjenta
function renderSelectedPatient(patient) {
    const hrCard = document.getElementById("hrCard");
    const statusCard = document.getElementById("statusCard");
    const statusValue = document.getElementById("statusValue");

    document.getElementById("hrValue").innerText = patient.hr;
    document.getElementById("spo2Value").innerText = patient.spo2;
    selectedPatientLabel.innerText = `${patient.bed} | ${patient.patientName}`;

    if (patient.alarms.length > 0) {
        statusValue.innerText = "ALARM";
        statusCard.classList.remove("normal");
        statusCard.classList.add("alarm");
        hrCard.classList.add("active");
    } else {
        statusValue.innerText = "Normal";
        statusCard.classList.remove("alarm");
        statusCard.classList.add("normal");
        hrCard.classList.remove("active");
    }
}

// Aktualizuje globalny pasek statusu na górze ekranu
function renderGlobalStatus(patients, activeAlarmCount) {
    if (activeAlarmCount > 0) {
        globalAlert.classList.remove("normal");
        globalAlert.classList.add("alarm");
        globalStatus.innerText = "Alarm na oddziale";
    } else {
        globalAlert.classList.remove("alarm");
        globalAlert.classList.add("normal");
        globalStatus.innerText = "Wszyscy pacjenci stabilni";
    }

    patientCount.innerText = `${patients.length} pacjentow`;
    globalAlarmCount.innerText = `${activeAlarmCount} aktywnych alarmow`;
}

// Generuje listę aktywnych alarmów w panelu po prawej stronie
function renderAlarms(patients) {
    const alarmsList = document.getElementById("alarms");
    alarmsList.innerHTML = "";

    // Filtrowanie pacjentów posiadających aktywne alarmy
    const alarmPatients = patients.filter(patient => patient.alarms.length > 0);

    if (alarmPatients.length === 0) {
        const li = document.createElement("li");
        li.className = "no-alarm";
        li.innerText = "Brak aktywnych alarmow";
        alarmsList.appendChild(li);
        return;
    }

    // Dodawanie każdego alarmu do listy
    alarmPatients.forEach(patient => {
        patient.alarms.forEach(alarm => {
            const li = document.createElement("li");
            li.innerText = `[${patient.updatedAt}] ${patient.bed} | ${patient.patientName}: ${alarm} | HR=${patient.hr} BPM | SpO2=${patient.spo2}%`;
            alarmsList.appendChild(li);
        });
    });
}


// TELEMETRIA I INSTRUMENTACJA
// Formatuje wartości liczbowe telemetrii (np. czas w milisekundach)
function formatMetric(value) {
    return value === null || value === undefined ? "-" : Number(value).toFixed(1);
}

// Dodaje nowy wpis do panelu logów telemetrii i usuwa najstarsze
function addTelemetryLog(message) {
    telemetryLogs.unshift(message); // Dodanie na początek tablicy logów
    if (telemetryLogs.length > 8) {
        telemetryLogs.pop(); // Usunięcie ostatniego (najstarszego) elementu
    }

    telemetryLog.innerHTML = "";
    telemetryLogs.forEach(log => {
        const li = document.createElement("li");
        li.innerText = log;
        telemetryLog.appendChild(li);
    });
}

// Aktualizuje sekcję instrumentacji na dole strony
function renderInstrumentation(instrumentation, measuredClientLatencyMs, measuredClientJitterMs) {
    // W przypadku braku danych z backendu
    const telemetry = instrumentation || {
        requestId: "-",
        endpoint: "/patients",
        backendLatencyMs: null,
        serverJitterMs: null,
        serverTimestamp: new Date().toLocaleTimeString()
    };

    instrumentationRequest.innerText = `Request ${telemetry.requestId} | ${telemetry.endpoint}`;
    backendLatency.innerText = formatMetric(telemetry.backendLatencyMs);
    clientLatency.innerText = formatMetric(measuredClientLatencyMs);
    serverJitter.innerText = formatMetric(telemetry.serverJitterMs);
    clientJitter.innerText = formatMetric(measuredClientJitterMs);

    addTelemetryLog(
        `[${telemetry.serverTimestamp}] backend=${formatMetric(telemetry.backendLatencyMs)}ms | round-trip=${formatMetric(measuredClientLatencyMs)}ms | server jitter=${formatMetric(telemetry.serverJitterMs)}ms | UI jitter=${formatMetric(measuredClientJitterMs)}ms`
    );
}

// KOMUNIKACJA Z API (BACKENDEM)
// Główna funkcja pobierająca dane pacjentów z serwera i aktualizująca interfejs
async function fetchPatients() {
    const clientStartedAt = performance.now(); // Czas rozpoczęcia zapytania
    
    // Obliczanie opóźnienia interfejsu klienta (jitter)
    const measuredClientJitterMs = lastClientPollStartedAt === null
        ? null
        : clientStartedAt - lastClientPollStartedAt - expectedPollIntervalMs;
    lastClientPollStartedAt = clientStartedAt;

    try {
        // Wysłanie zapytania GET do API backendu pod adres /patients
        const response = await fetch("http://127.0.0.1:5000/patients");
        const result = await response.json();
        
        // Zmierzenie całkowitego czasu od wysłania zapytania do odebrania odpowiedzi
        const measuredClientLatencyMs = performance.now() - clientStartedAt; 
        const patients = result.patients;

        // Aktualizacja danych do wyświetlenia na wykresach dla każdego pacjenta
        patients.forEach(appendPatientPoint);

        // Domyślne zaznaczenie pierwszego pacjenta na liście po załadowaniu strony
        if (!selectedPatientId && patients.length > 0) {
            selectedPatientId = patients[0].patientId;
        }

        const selectedPatient = patients.find(patient => patient.patientId === selectedPatientId) || patients[0];

        // Wywołanie funkcji odświeżających poszczególne sekcje interfejsu
        renderGlobalStatus(patients, result.activeAlarmCount);
        renderPatientCards(patients);
        renderSelectedPatient(selectedPatient);
        renderAlarms(patients);
        renderCharts(selectedPatient.patientId);
        renderInstrumentation(result.instrumentation, measuredClientLatencyMs, measuredClientJitterMs);

        document.getElementById("lastUpdate").innerText = `Ostatnia aktualizacja: ${result.updatedAt}`;
    } catch (error) {
        // Obsługa błędów połączenia (np. gdy wyłączono serwer backendu)
        console.error("Fetch error:", error);
        document.getElementById("lastUpdate").innerText = "Blad polaczenia z API";
        addTelemetryLog(`[${new Date().toLocaleTimeString()}] Blad pobierania danych: ${error.message}`);
    }
}

// INICJALIZACJA APLIKACJI
fetchPatients(); // Pierwsze, natychmiastowe pobranie danych po załadowaniu okna przeglądarki
setInterval(fetchPatients, 1000); // Cykliczne odpytywanie serwera o nowe dane co 1000 milisekund (1 sekunda)