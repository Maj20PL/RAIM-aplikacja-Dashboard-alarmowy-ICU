const hrDate = [];
const spo2Data = [];

const labels = [];
const maxPoints = 20;

// Rysowanie wykresów (do poprawy na bardziej szpitalny)
const hrChart = new Chart(document.getElementById("hrChart"), {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: "HR",
                data: hrDate,
                borderColor: "red",
                fill: false
            }]
        }
    });

    const spo2Chart = new Chart(document.getElementById("spo2Chart"), {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: "SpO2",
                data: spo2Data,
                borderColor: "blue",
                fill: false
            }]
        }
    });

// Funkcja do pobierania danych z json i wstawiania ich na strone index.html

async function fetchData() {
    const response = await fetch("http://127.0.0.1:5000/dane");
    const result = await response.json();

    const hr = result.data.hr;
    const spo2 = result.data.spo2;

    document.getElementById("hr").innerText = hr;
    document.getElementById("spo2").innerText = spo2;

    // Dodanie nowego punktu do wykresu (co 1 sekunde)
    const time = new Date().toLocaleTimeString();

    labels.push(time);
    hrDate.push(hr);
    spo2Data.push(spo2);

    // Limit punktow do wykresow
    if (labels.lenght > maxPoints) {
        labels.shift();
        hrData.shift();
        spo2Data.shift();
    }

    hrChart.update();
    spo2Chart.update();

    // Wystapienie alarmu na stronie
    const alarmsList = document.getElementById("alarms");
    alarmsList.innerHTML = "";

    result.alarms.forEach(alarm => {
        const li = document.createElement("li");
        li.innerText = alarm;
        alarmsList.appendChild(li);
    });
}
setInterval(fetchData, 1000);