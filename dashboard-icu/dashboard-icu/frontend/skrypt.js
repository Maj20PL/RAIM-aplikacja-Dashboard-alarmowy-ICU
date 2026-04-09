const hrData = [];
const spo2Data = [];
const labels = [];
const maxPoints = 40;
// Obsługa wykresu HR
const hrChart = new Chart(document.getElementById("hrChart"), {
    type: 'line',
    data: {
        labels: labels,
        datasets: [{
            label: "HR",
            data: hrData,
            borderColor: "#ff5c5c",
            backgroundColor: "rgba(255,92,92,0.14)",
            fill: true,
            tension: 0.3,
            pointRadius: 2,
            borderWidth: 2
        }]
    },
    options: {
        responsive: true,
        plugins: {
            legend: { display: false }
        },
        scales: {
            y: {
                min: 40,
                max: 160
            }
        }
    }
});
// Obsługa wykresu SPO2
const spo2Chart = new Chart(document.getElementById("spo2Chart"), {
    type: 'line',
    data: {
        labels: labels,
        datasets: [{
            label: "SpO2",
            data: spo2Data,
            borderColor: "#5ca8ff",
            backgroundColor: "rgba(92,168,255,0.16)",
            fill: true,
            tension: 0.3,
            pointRadius: 2,
            borderWidth: 2
        }]
    },
    options: {
        responsive: true,
        plugins: {
            legend: { display: false }
        },
        scales: {
            y: {
                min: 70,
                max: 102
            }
        }
    }
});

// Funkcja do pobierania danych z json i wstawiania ich na strone index.html

async function fetchData() {
    try {
        const response = await fetch("http://127.0.0.1:5000/dane");
        const result = await response.json();

        const hr = result.data.hr;
        const spo2 = result.data.spo2;
        // Dodanie nowego punktu do wykresu (co 1 sekunde)
        const time = new Date().toLocaleTimeString();

        document.getElementById("hrValue").innerText = hr;
        document.getElementById("spo2Value").innerText = spo2;
        document.getElementById("lastUpdate").innerText = `Last update: ${time}`;

        labels.push(time);
        hrData.push(hr);
        spo2Data.push(spo2);

        // Limit punktow do wykresow
        if (labels.length > maxPoints) {
            labels.shift(time)
            hrData.shift(hr);
            spo2Data.shift(spo2);
        }

        hrChart.update();
        spo2Chart.update();

        const alarmsList = document.getElementById("alarms");
        alarmsList.innerHTML = "";
        // Zmienne statusu
        const hrKart = document.getElementById("hrKart");
        const statusKart = document.getElementById("statusKart");
        const statusValue = document.getElementById("statusValue");

        // Obsługa alarmów na stronie
        if (result.alarms.length > 0) {
            statusValue.innerText = "ALARM";
            statusKart.classList.remove("normal");
            statusKart.classList.add("alarm");
            hrKart.classList.add("active");

            result.alarms.forEach(alarm => {
                const li = document.createElement("li");
                li.innerText = `[${time}] ALERT: ${alarm} | HR=${hr} BPM | SpO2=${spo2}%`;
                alarmsList.appendChild(li);
            });
        } else {
            statusValue.innerText = "Normal";
            statusKart.classList.remove("alarm");
            statusKart.classList.add("normal");
            hrKart.classList.remove("active");

            const li = document.createElement("li");
            li.innerText = `[${time}] Brak aktywnych alarmow`;
            li.style.background = "rgba(50, 150, 255, 0.12)";
            li.style.color = "#d7f4ff";
            alarmsList.appendChild(li);
        }
    } catch (error) {
        console.error("Fetch error:", error);
    }
}

fetchData();
setInterval(fetchData, 1000);