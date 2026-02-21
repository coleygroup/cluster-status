const THEME = {
    gridColor: 'rgba(237, 233, 227, 0.06)',
    textColor: '#b5afa6',
    teal: '#5b9a8b',
    tealLight: '#78b5a5',
    orange: '#c47a3a',
    orangeLight: '#d4924e',
    green: '#6a9e6b',
    red: '#c45c5c',
    yellow: '#c49a3a',
    fontFamily: "'IBM Plex Mono', monospace",
};

// distinct colors for per-server stacked chart
const SERVER_COLORS = [
    '#5b9a8b', '#c47a3a', '#6a9e6b', '#c45c5c',
    '#c49a3a', '#78b5a5', '#d4924e', '#8b6a9e',
];

function applyDefaults() {
    Chart.defaults.color = THEME.textColor;
    Chart.defaults.font.family = THEME.fontFamily;
    Chart.defaults.font.size = 11;
    Chart.defaults.plugins.legend.labels.usePointStyle = true;
}

function commonScaleOptions() {
    return {
        x: {
            type: 'time',
            grid: { color: THEME.gridColor },
            ticks: { maxTicksLimit: 12 },
        },
        y: {
            beginAtZero: true,
            grid: { color: THEME.gridColor },
        },
    };
}

export function createFreeGpusChart(canvas) {
    applyDefaults();
    return new Chart(canvas, {
        type: 'line',
        data: {
            datasets: [
                {
                    label: 'Free GPUs',
                    data: [],
                    borderColor: THEME.teal,
                    backgroundColor: 'rgba(91, 154, 139, 0.15)',
                    fill: true,
                    tension: 0.3,
                    pointRadius: 0,
                    pointHitRadius: 8,
                    borderWidth: 2,
                },
                {
                    label: 'Total GPUs',
                    data: [],
                    borderColor: THEME.textColor,
                    borderDash: [6, 4],
                    pointRadius: 0,
                    borderWidth: 1,
                    fill: false,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { intersect: false, mode: 'index' },
            scales: commonScaleOptions(),
            plugins: {
                tooltip: {
                    callbacks: {
                        title: (items) => new Date(items[0].parsed.x).toLocaleString(),
                    },
                },
            },
        },
    });
}

export function createServerBreakdownChart(canvas) {
    applyDefaults();
    return new Chart(canvas, {
        type: 'line',
        data: { datasets: [] },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { intersect: false, mode: 'index' },
            scales: {
                ...commonScaleOptions(),
                y: {
                    ...commonScaleOptions().y,
                    stacked: true,
                },
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        title: (items) => new Date(items[0].parsed.x).toLocaleString(),
                    },
                },
            },
        },
    });
}

export function createUtilizationChart(canvas) {
    applyDefaults();
    return new Chart(canvas, {
        type: 'line',
        data: {
            datasets: [
                {
                    label: 'Avg GPU Util %',
                    data: [],
                    borderColor: THEME.orange,
                    backgroundColor: 'rgba(196, 122, 58, 0.1)',
                    fill: true,
                    tension: 0.3,
                    pointRadius: 0,
                    pointHitRadius: 8,
                    borderWidth: 2,
                },
                {
                    label: 'Avg GPU Memory %',
                    data: [],
                    borderColor: THEME.tealLight,
                    tension: 0.3,
                    pointRadius: 0,
                    pointHitRadius: 8,
                    borderWidth: 2,
                    fill: false,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { intersect: false, mode: 'index' },
            scales: {
                ...commonScaleOptions(),
                y: {
                    ...commonScaleOptions().y,
                    max: 100,
                    ticks: {
                        callback: (v) => v + '%',
                    },
                    grid: { color: THEME.gridColor },
                },
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        title: (items) => new Date(items[0].parsed.x).toLocaleString(),
                        label: (item) => `${item.dataset.label}: ${item.parsed.y.toFixed(1)}%`,
                    },
                },
            },
        },
    });
}

export function updateAllCharts(freeGpusChart, serverBreakdownChart, utilizationChart, data) {
    const series = data.series;

    // free GPUs over time
    freeGpusChart.data.datasets[0].data = series.map(p => ({
        x: p.timestamp * 1000,
        y: p.free_gpus,
    }));
    freeGpusChart.data.datasets[1].data = series.map(p => ({
        x: p.timestamp * 1000,
        y: p.total_gpus,
    }));
    freeGpusChart.update();

    // per-server breakdown (stacked)
    const serverNames = new Set();
    series.forEach(p => {
        Object.keys(p.servers || {}).forEach(s => serverNames.add(s));
    });
    const sortedServers = [...serverNames].sort();

    serverBreakdownChart.data.datasets = sortedServers.map((name, i) => ({
        label: name,
        data: series.map(p => ({
            x: p.timestamp * 1000,
            y: (p.servers[name]?.free_gpus) ?? 0,
        })),
        borderColor: SERVER_COLORS[i % SERVER_COLORS.length],
        backgroundColor: SERVER_COLORS[i % SERVER_COLORS.length] + '20',
        fill: true,
        tension: 0.3,
        pointRadius: 0,
        pointHitRadius: 8,
        borderWidth: 1.5,
    }));
    serverBreakdownChart.options.scales.y.stacked = true;
    serverBreakdownChart.update();

    // utilization
    utilizationChart.data.datasets[0].data = series.map(p => ({
        x: p.timestamp * 1000,
        y: p.avg_gpu_util,
    }));
    utilizationChart.data.datasets[1].data = series.map(p => ({
        x: p.timestamp * 1000,
        y: p.avg_gpu_memory_percent,
    }));
    utilizationChart.update();
}
