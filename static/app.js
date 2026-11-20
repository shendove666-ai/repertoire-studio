document.addEventListener("DOMContentLoaded", () => {
    // Filter only the repertoire rows already rendered by the server.
    const quickFilterInput = document.getElementById("quickFilterInput");
    const repertoireRows = document.querySelectorAll(".repertoire-row");

    if (quickFilterInput && repertoireRows.length > 0) {
        quickFilterInput.addEventListener("input", (event) => {
            const searchTerm = event.target.value.trim().toLowerCase();
            repertoireRows.forEach((row) => {
                const rowText = row.textContent.toLowerCase();
                row.style.display = rowText.includes(searchTerm) ? "" : "none";
            });
        });
    }

    // Load analytics only when both dashboard canvases and Chart.js are present.
    const composerCanvas = document.getElementById("composerChart");
    const dailyCanvas = document.getElementById("dailyChart");

    if (composerCanvas && dailyCanvas && typeof Chart !== "undefined") {
        fetch("/api/analytics-data")
            .then((response) => response.json())
            .then((analytics) => {
                const composerLabels = analytics.composers.map((total) => total.composer);
                const composerMinutes = analytics.composers.map((total) => total.minutes);

                new Chart(composerCanvas, {
                    type: "bar",
                    data: {
                        labels: composerLabels,
                        datasets: [
                            {
                                label: "Total Practice Minutes",
                                data: composerMinutes,
                                backgroundColor: "#1D3557",
                                borderRadius: 3,
                            },
                        ],
                    },
                    options: {
                        responsive: true,
                        plugins: {
                            legend: { display: false },
                        },
                        scales: {
                            y: { beginAtZero: true },
                        },
                    },
                });

                const dailyLabels = analytics.daily.map((total) => total.practiced_on);
                const dailyMinutes = analytics.daily.map((total) => total.minutes);

                new Chart(dailyCanvas, {
                    type: "line",
                    data: {
                        labels: dailyLabels,
                        datasets: [
                            {
                                label: "Daily Duration (min)",
                                data: dailyMinutes,
                                borderColor: "#7A2E3A",
                                backgroundColor: "rgba(122, 46, 58, 0.12)",
                                tension: 0.25,
                                fill: true,
                                pointRadius: 4,
                            },
                        ],
                    },
                    options: {
                        responsive: true,
                        plugins: {
                            legend: { display: false },
                        },
                        scales: {
                            y: { beginAtZero: true },
                        },
                    },
                });
            })
            .catch((error) => {
                console.error("Failed to load analytics data:", error);
            });
    }
});
