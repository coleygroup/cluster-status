import { fetchHistoryData } from './api.js';
import {
    createFreeGpusChart,
    createServerBreakdownChart,
    createUtilizationChart,
    updateAllCharts,
} from './charts.js';

let freeGpusChart, serverBreakdownChart, utilizationChart;
let currentHours = 24;

async function init() {
    freeGpusChart = createFreeGpusChart(document.getElementById('free-gpus-chart'));
    serverBreakdownChart = createServerBreakdownChart(document.getElementById('server-breakdown-chart'));
    utilizationChart = createUtilizationChart(document.getElementById('utilization-chart'));

    document.getElementById('time-range').addEventListener('change', async (e) => {
        currentHours = parseInt(e.target.value, 10);
        await refreshData();
    });

    await refreshData();
}

async function refreshData() {
    try {
        const data = await fetchHistoryData(currentHours);

        if (data.series.length < 2) {
            showEmptyState();
            return;
        }

        hideEmptyState();
        updateAllCharts(freeGpusChart, serverBreakdownChart, utilizationChart, data);
        updateStatsCards(data.stats);
        updateHeroSubtitle(data.stats);
    } catch (error) {
        console.error('Failed to fetch history data:', error);
        document.getElementById('waste-subtitle').textContent =
            'Failed to load history data. Is the server running?';
    }
}

function showEmptyState() {
    document.getElementById('empty-state').style.display = '';
    document.querySelectorAll('.chart-panel').forEach(el => el.style.display = 'none');
    document.getElementById('waste-stats').innerHTML = '';
    document.getElementById('waste-subtitle').textContent =
        'Collecting data... Check back in a few hours for your first waste report.';
}

function hideEmptyState() {
    document.getElementById('empty-state').style.display = 'none';
    document.querySelectorAll('.chart-panel').forEach(el => el.style.display = '');
}

function updateHeroSubtitle(stats) {
    const el = document.getElementById('waste-subtitle');
    if (stats.total_snapshots === 0) {
        el.textContent = 'No data yet.';
        return;
    }
    const label = formatRangeLabel(currentHours);
    el.textContent =
        `${stats.avg_free_gpus} of ${stats.avg_total_gpus} GPUs sat idle on average over the ${label}. ` +
        `That's ${stats.waste_percent}% waste.`;
}

function updateStatsCards(stats) {
    const container = document.getElementById('waste-stats');

    const cards = [
        { value: stats.avg_free_gpus, label: 'Avg Free GPUs' },
        { value: stats.peak_free_gpus, label: 'Peak Idle' },
        { value: `${stats.avg_cluster_util}%`, label: 'Avg GPU Util' },
        { value: `${stats.waste_percent}%`, label: 'Waste' },
    ];

    container.innerHTML = cards.map(c => `
        <div class="col-6 col-md-3">
            <div class="stat-card">
                <div class="stat-value">${c.value}</div>
                <div class="stat-label">${c.label}</div>
            </div>
        </div>
    `).join('');
}

function formatRangeLabel(hours) {
    if (hours <= 24) return `last ${hours}h`;
    const days = Math.round(hours / 24);
    return `last ${days} days`;
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
