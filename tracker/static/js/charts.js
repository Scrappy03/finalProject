// Weekly Chart
const weeklyCtx = document.getElementById('weeklyChart');
if (weeklyCtx) {
    const getChartData = (id) => {
        const element = document.getElementById(id);
        return element ? JSON.parse(element.textContent) : [];
    };

    const labels = getChartData('chart-labels');
    const sleepData = getChartData('sleep-data');
    const moodData = getChartData('mood-data');

    const weeklyChart = new Chart(weeklyCtx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Sleep Quality',
                    data: sleepData,
                    borderColor: '#47644f',
                    backgroundColor: 'rgba(71, 100, 79, 0.1)',
                    tension: 0.4,
                    fill: true,
                    pointBackgroundColor: '#47644f',
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                },
                {
                    label: 'Mood Rating',
                    data: moodData,
                    borderColor: '#426374',
                    backgroundColor: 'rgba(66, 99, 116, 0.1)',
                    tension: 0.4,
                    fill: true,
                    pointBackgroundColor: '#426374',
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: true,
                    labels: {
                        font: {
                            size: 12,
                            weight: 500,
                            family: "'Manrope', sans-serif"
                        },
                        padding: 15,
                        usePointStyle: true,
                        color: '#1b1c19'
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 10,
                    ticks: {
                        stepSize: 2,
                        font: {
                            size: 11,
                            family: "'Manrope', sans-serif"
                        },
                        color: '#424843'
                    },
                    grid: {
                        drawBorder: false,
                        color: 'rgba(0, 0, 0, 0.05)'
                    }
                },
                x: {
                    grid: {
                        drawBorder: false,
                        display: false
                    },
                    ticks: {
                        font: {
                            size: 11,
                            family: "'Manrope', sans-serif"
                        },
                        color: '#1b1c19'
                    }
                }
            }
        }
    });
}
