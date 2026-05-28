// STAN APLIKACJI I KONFIGURACJA
const patientSeries = {}; // Historia HR i SpO2 dla wykresow kazdego pacjenta.
const collapsedWards = {}; // Zapamietuje, ktore oddzialy sa zwiniete w interfejsie.
const collapsedAlarmWards = {}; // Osobny stan zwijania sekcji alarmow.
const maxPoints = 20;
const expectedPollIntervalMs = 1000;
const telemetryLogs = [];
const metricThresholds = {
    backendLatency: { warning: 50, critical: 100 },
    clientLatency: { warning: 100, critical: 150 },
    serverJitter: { warning: 20, critical: 30 },
    clientJitter: { warning: 16, critical: 16 }
};

let selectedPatientId = null;
let lastClientPollStartedAt = null;

// REFERENCJE DO ELEMENTOW DOM
const patientGrid = document.getElementById("patientGrid");
const globalAlert = document.getElementById("globalAlert");
const globalStatus = document.getElementById("globalStatus");
const globalAlarmCount = document.getElementById("globalAlarmCount");
const patientCount = document.getElementById("patientCount");
const selectedPatientLabel = document.getElementById("selectedPatientLabel");
const instrumentationRequest = document.getElementById("instrumentationRequest");
const backendLatency = document.getElementById("backendLatency");
const clientLatency = document.getElementById("clientLatency");
const serverJitter = document.getElementById("serverJitter");
const clientJitter = document.getElementById("clientJitter");
const telemetryLog = document.getElementById("telemetryLog");
const delayWarning = document.getElementById("delayWarning");
const delayWarningTitle = document.getElementById("delayWarningTitle");
const delayWarningMessage = document.getElementById("delayWarningMessage");
const runRaceDemo = document.getElementById("runRaceDemo");
const raceDemoResult = document.getElementById("raceDemoResult");
const cpuCores = document.getElementById("cpuCores");
const cpuDuration = document.getElementById("cpuDuration");
const startCpuTest = document.getElementById("startCpuTest");
const cpuStatus = document.getElementById("cpuStatus");
const cpuTestResult = document.getElementById("cpuTestResult");

// KONFIGURACJA WYKRESOW
const sharedChartOptions = {
    responsive: false,
    maintainAspectRatio: false,
    animation: false,
    plugins: {
        legend: { display: false }
    }
};

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
            tension: 0.3,
            pointRadius: 2,
            borderWidth: 2
        }]
    },
    options: {
        ...sharedChartOptions,
        scales: {
            y: {
                min: 40,
                max: 160
            }
        }
    }
});

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
                max: 102
            }
        }
    }
});

// FUNKCJE POMOCNICZE DLA DANYCH
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

function appendPatientPoint(patient) {
    const series = getSeries(patient.patientId);
    series.labels.push(patient.updatedAt);
    series.hr.push(patient.hr);
    series.spo2.push(patient.spo2);

    if (series.labels.length > maxPoints) {
        series.labels.shift();
        series.hr.shift();
        series.spo2.shift();
    }
}

function groupPatientsByWard(patients) {
    return patients.reduce((groups, patient) => {
        if (!groups[patient.wardId]) {
            groups[patient.wardId] = {
                wardId: patient.wardId,
                wardName: patient.wardName,
                patients: []
            };
        }
        groups[patient.wardId].patients.push(patient);
        return groups;
    }, {});
}

function getAlarmBeds(patients) {
    return patients
        .filter(patient => patient.alarms.length > 0)
        .map(patient => patient.bed);
}

function formatAlarmBeds(beds) {
    return beds.length > 0 ? `Alarm: ${beds.join(", ")}` : "Brak alarmow";
}

// FUNKCJE RENDERUJACE
function renderCharts(patientId) {
    const series = getSeries(patientId);
    hrChart.data.labels = series.labels;
    hrChart.data.datasets[0].data = series.hr;
    spo2Chart.data.labels = series.labels;
    spo2Chart.data.datasets[0].data = series.spo2;
    hrChart.update();
    spo2Chart.update();
}

function createPatientCard(patient, patients) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `patient-card ${patient.status === "ALARM" ? "alarm" : "normal"}`;
    button.dataset.patientId = patient.patientId;

    if (patient.patientId === selectedPatientId) {
        button.classList.add("selected");
    }

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

    button.addEventListener("click", () => {
        selectedPatientId = patient.patientId;
        renderSelectedPatient(patient);
        renderPatientCards(patients);
        renderCharts(patient.patientId);
    });

    return button;
}

function renderPatientCards(patients) {
    patientGrid.innerHTML = "";
    const grouped = groupPatientsByWard(patients);

    Object.values(grouped).forEach(ward => {
        const wardPatients = ward.patients;
        const alarmBeds = getAlarmBeds(wardPatients);
        const activeAlarmCount = alarmBeds.length;
        const isCollapsed = collapsedWards[ward.wardId] === true;

        const section = document.createElement("section");
        section.className = `ward-section ${isCollapsed ? "collapsed" : ""}`;

        const header = document.createElement("button");
        header.type = "button";
        header.className = "ward-header";
        header.innerHTML = `
            <span>
                <strong>${ward.wardName}</strong>
                <small>${wardPatients.length} pacjentow | ${formatAlarmBeds(alarmBeds)}</small>
            </span>
            <span class="ward-summary ${activeAlarmCount > 0 ? "alarm" : "normal"}">
                ${activeAlarmCount} alarmow
            </span>
            <span class="ward-toggle">${isCollapsed ? "Rozwin" : "Zwin"}</span>
        `;

        header.addEventListener("click", () => {
            collapsedWards[ward.wardId] = !isCollapsed;
            renderPatientCards(patients);
        });

        const cards = document.createElement("div");
        cards.className = "patient-grid";
        wardPatients.forEach(patient => {
            cards.appendChild(createPatientCard(patient, patients));
        });

        section.appendChild(header);
        section.appendChild(cards);
        patientGrid.appendChild(section);
    });
}

function renderSelectedPatient(patient) {
    const hrCard = document.getElementById("hrCard");
    const statusCard = document.getElementById("statusCard");
    const statusValue = document.getElementById("statusValue");

    document.getElementById("hrValue").innerText = patient.hr;
    document.getElementById("spo2Value").innerText = patient.spo2;
    selectedPatientLabel.innerText = `${patient.wardName} | ${patient.bed} | ${patient.patientName}`;

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

function renderGlobalStatus(patients, activeAlarmCount) {
    if (activeAlarmCount > 0) {
        globalAlert.classList.remove("normal");
        globalAlert.classList.add("alarm");
        globalStatus.innerText = "Alarm na oddzialach ICU";
    } else {
        globalAlert.classList.remove("alarm");
        globalAlert.classList.add("normal");
        globalStatus.innerText = "Wszyscy pacjenci stabilni";
    }

    patientCount.innerText = `${patients.length} pacjentow`;
    globalAlarmCount.innerText = `${activeAlarmCount} aktywnych alarmow`;
}

function renderAlarms(patients) {
    const alarmsList = document.getElementById("alarms");
    alarmsList.innerHTML = "";
    const grouped = groupPatientsByWard(patients);

    // Alarmy sa liczone ze wszystkich pacjentow, niezaleznie od zwijania listy pacjentow.
    if (patients.every(patient => patient.alarms.length === 0)) {
        const li = document.createElement("li");
        li.className = "no-alarm";
        li.innerText = "Brak aktywnych alarmow";
        alarmsList.appendChild(li);
        return;
    }

    Object.values(grouped).forEach(ward => {
        const alarmPatients = ward.patients.filter(patient => patient.alarms.length > 0);
        if (alarmPatients.length === 0) {
            return;
        }

        const alarmBeds = getAlarmBeds(ward.patients);
        const isCollapsed = collapsedAlarmWards[ward.wardId] === true;
        const section = document.createElement("li");
        section.className = `alarm-ward ${isCollapsed ? "collapsed" : ""}`;

        const header = document.createElement("button");
        header.type = "button";
        header.className = "alarm-ward-header";
        header.innerHTML = `
            <span>
                <strong>${ward.wardName}</strong>
                <small>${formatAlarmBeds(alarmBeds)}</small>
            </span>
            <span>${alarmBeds.length} alarmujacych lozek</span>
            <span class="ward-toggle">${isCollapsed ? "Rozwin" : "Zwin"}</span>
        `;
        header.addEventListener("click", () => {
            collapsedAlarmWards[ward.wardId] = !isCollapsed;
            renderAlarms(patients);
        });

        const details = document.createElement("ul");
        details.className = "alarm-details";
        alarmPatients.forEach(patient => {
            patient.alarms.forEach(alarm => {
                const alarmItem = document.createElement("li");
                alarmItem.innerText = `[${patient.updatedAt}] ${patient.bed} | ${patient.patientName}: ${alarm} | HR=${patient.hr} BPM | SpO2=${patient.spo2}%`;
                details.appendChild(alarmItem);
            });
        });

        section.appendChild(header);
        section.appendChild(details);
        alarmsList.appendChild(section);
    });
}

// TELEMETRIA I INSTRUMENTACJA
function formatMetric(value) {
    return value === null || value === undefined ? "-" : Number(value).toFixed(1);
}

function metricLevel(value, thresholds, useAbsolute = false) {
    if (value === null || value === undefined) {
        return "normal";
    }

    const measuredValue = useAbsolute ? Math.abs(Number(value)) : Number(value);
    if (measuredValue > thresholds.critical) {
        return "critical";
    }
    if (measuredValue >= thresholds.warning) {
        return "warning";
    }
    return "normal";
}

function setMetricState(element, level) {
    const card = element.closest(".metric-card");
    card.classList.remove("normal", "warning", "critical");
    card.classList.add(level);
}

function addTelemetryLog(message) {
    telemetryLogs.unshift(message);
    if (telemetryLogs.length > 8) {
        telemetryLogs.pop();
    }

    telemetryLog.innerHTML = "";
    telemetryLogs.forEach(log => {
        const li = document.createElement("li");
        li.innerText = log;
        telemetryLog.appendChild(li);
    });
}

function renderInstrumentation(instrumentation, measuredClientLatencyMs, measuredClientJitterMs) {
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
    setMetricState(backendLatency, metricLevel(telemetry.backendLatencyMs, metricThresholds.backendLatency));
    setMetricState(clientLatency, metricLevel(measuredClientLatencyMs, metricThresholds.clientLatency));
    setMetricState(serverJitter, metricLevel(telemetry.serverJitterMs, metricThresholds.serverJitter, true));
    setMetricState(clientJitter, metricLevel(measuredClientJitterMs, metricThresholds.clientJitter, true));

    addTelemetryLog(
        `[${telemetry.serverTimestamp}] backend=${formatMetric(telemetry.backendLatencyMs)}ms | round-trip=${formatMetric(measuredClientLatencyMs)}ms | server jitter=${formatMetric(telemetry.serverJitterMs)}ms | UI jitter=${formatMetric(measuredClientJitterMs)}ms`
    );
}

function renderDelayWarning(delayWarningData, measuredClientLatencyMs, measuredClientJitterMs) {
    const clientTooSlow = measuredClientLatencyMs >= metricThresholds.clientLatency.warning
        || Math.abs(measuredClientJitterMs || 0) >= metricThresholds.clientJitter.warning;
    const clientCritical = measuredClientLatencyMs > metricThresholds.clientLatency.critical
        || Math.abs(measuredClientJitterMs || 0) > metricThresholds.clientJitter.critical;
    const backendWarning = delayWarningData && delayWarningData.active;

    if (backendWarning || clientTooSlow) {
        delayWarning.classList.remove("normal");
        delayWarning.classList.remove("warning", "critical");
        delayWarning.classList.add((delayWarningData && delayWarningData.level === "critical") || clientCritical ? "critical" : "warning");
        delayWarningTitle.innerText = "Uwaga: przekroczone progi opoznien";
        delayWarningMessage.innerText = backendWarning
            ? delayWarningData.message
            : "Interfejs odbiera dane z opoznieniem. Progi: client latency <100-150 ms, UI jitter <16 ms.";
        return;
    }

    delayWarning.classList.remove("warning", "critical");
    delayWarning.classList.add("normal");
    delayWarningTitle.innerText = "Opoznienia w normie";
    delayWarningMessage.innerText = "Progi: backend <50-100 ms, client <100-150 ms, server jitter <20-30 ms, UI jitter <16 ms.";
}

async function runConcurrencyDemo() {
    raceDemoResult.innerText = "Uruchamianie testu...";
    const response = await fetch("http://127.0.0.1:5000/concurrency-demo");
    const result = await response.json();

    raceDemoResult.innerText = [
        `Zjawisko: ${result.phenomenon}`,
        `Przed lockiem: oczekiwano ${result.before.expected}, otrzymano ${result.before.actual}, utracono ${result.before.lostUpdates}`,
        `Po locku: oczekiwano ${result.after.expected}, otrzymano ${result.after.actual}, utracono ${result.after.lostUpdates}`,
        `Poprawa: ${result.summary.improvement} odzyskanych aktualizacji`
    ].join("\n");
}

function renderCpuStatus(status) {
    cpuCores.max = status.maxCores;
    cpuDuration.max = status.maxDurationSeconds;

    if (status.running) {
        cpuStatus.innerText = `Test CPU trwa: ${status.activeProcesses} procesow, pozostalo ${status.remainingSeconds}s`;
        cpuTestResult.innerText = `Obciazenie: ${status.cores} rdzeni przez ${status.durationSeconds}s\nPozostalo: ${status.remainingSeconds}s`;
        startCpuTest.disabled = true;
        return;
    }

    cpuStatus.innerText = "Test CPU nieaktywny";
    startCpuTest.disabled = false;
    if (status.lastResult) {
        cpuTestResult.innerText = status.lastResult.message;
    }
}

async function refreshCpuStatus() {
    try {
        const response = await fetch("http://127.0.0.1:5000/cpu-test/status");
        const status = await response.json();
        renderCpuStatus(status);
    } catch (error) {
        cpuStatus.innerText = "Brak statusu testu CPU";
    }
}

async function startCpuLoadTest() {
    const cores = Number(cpuCores.value);
    const durationSeconds = Number(cpuDuration.value);
    cpuTestResult.innerText = "Start testu CPU...";

    const response = await fetch("http://127.0.0.1:5000/cpu-test", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ cores, durationSeconds })
    });
    const status = await response.json();

    if (!response.ok) {
        cpuTestResult.innerText = status.error || "Nie udalo sie uruchomic testu CPU.";
        if (status.status) {
            renderCpuStatus(status.status);
        }
        return;
    }

    renderCpuStatus(status);
}

// KOMUNIKACJA Z API
async function fetchPatients() {
    const clientStartedAt = performance.now();
    const measuredClientJitterMs = lastClientPollStartedAt === null
        ? null
        : clientStartedAt - lastClientPollStartedAt - expectedPollIntervalMs;
    lastClientPollStartedAt = clientStartedAt;

    try {
        const response = await fetch("http://127.0.0.1:5000/patients");
        const result = await response.json();
        const measuredClientLatencyMs = performance.now() - clientStartedAt;
        const patients = result.patients;

        patients.forEach(appendPatientPoint);

        if (!selectedPatientId && patients.length > 0) {
            selectedPatientId = patients[0].patientId;
        }

        const selectedPatient = patients.find(patient => patient.patientId === selectedPatientId) || patients[0];

        renderGlobalStatus(patients, result.activeAlarmCount);
        renderPatientCards(patients);
        renderSelectedPatient(selectedPatient);
        renderAlarms(patients);
        renderCharts(selectedPatient.patientId);
        renderInstrumentation(result.instrumentation, measuredClientLatencyMs, measuredClientJitterMs);
        renderDelayWarning(result.delayWarning, measuredClientLatencyMs, measuredClientJitterMs);

        document.getElementById("lastUpdate").innerText = `Ostatnia aktualizacja: ${result.updatedAt}`;
    } catch (error) {
        console.error("Fetch error:", error);
        document.getElementById("lastUpdate").innerText = "Blad polaczenia z API";
        addTelemetryLog(`[${new Date().toLocaleTimeString()}] Blad pobierania danych: ${error.message}`);
    }
}

// INICJALIZACJA APLIKACJI
runRaceDemo.addEventListener("click", runConcurrencyDemo);
startCpuTest.addEventListener("click", startCpuLoadTest);
fetchPatients();
refreshCpuStatus();
setInterval(fetchPatients, 1000);
setInterval(refreshCpuStatus, 1000);
