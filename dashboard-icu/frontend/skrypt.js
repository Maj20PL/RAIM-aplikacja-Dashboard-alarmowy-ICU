const hrData = [];
const spo2Data = [];
const labels = [];
const maxPoints = 20;

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
        const response = await fetch("http://127.0.0.1:5000/data");
        const result = await response.json();

        const hr = result.hr;
        const spo2 = result.spo2;
        const time = new Date().toLocaleTimeString();

        document.getElementById("hrValue").innerText = hr;
        document.getElementById("spo2Value").innerText = spo2;
        document.getElementById("lastUpdate").innerText = `Last update: ${time}`;

        labels.push(time);
        hrData.push(hr);
        spo2Data.push(spo2);

        if (labels.length > maxPoints) {
            labels.shift();
            hrData.shift();
            spo2Data.shift();
        }

        hrChart.update();
        spo2Chart.update();

        const alarmsList = document.getElementById("alarms");
        alarmsList.innerHTML = "";

        const hrCard = document.getElementById("hrCard");
        const statusCard = document.getElementById("statusCard");
        const statusValue = document.getElementById("statusValue");

        if (result.alarms.length > 0) {
            statusValue.innerText = "ALARM";
            statusCard.classList.remove("normal");
            statusCard.classList.add("alarm");
            hrCard.classList.add("active");

            result.alarms.forEach(alarm => {
                const li = document.createElement("li");
                li.innerText = `[${time}] ALERT: ${alarm} | HR=${hr} BPM | SpO2=${spo2}%`;
                alarmsList.appendChild(li);
            });
        } else {
            statusValue.innerText = "Normal";
            statusCard.classList.remove("alarm");
            statusCard.classList.add("normal");
            hrCard.classList.remove("active");

            const li = document.createElement("li");
            li.innerText = `[${time}] No active alarms`;
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