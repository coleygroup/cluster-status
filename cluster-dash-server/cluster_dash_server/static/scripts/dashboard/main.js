/**
 * main.js - Entry point for the GPU Cluster Dashboard
 *
 * This is the main module that:
 * 1. Initializes the dashboard on page load
 * 2. Fetches data from the API
 * 3. Renders the summary cards and GPU details
 * 4. Updates the header with cluster-wide summary
 * 5. Manages auto-refresh with live indicator
 */

import { fetchDashboardData } from './api.js';
import { renderSummaryCards } from './summaryCards.js';
import { renderGpuDetails } from './gpuDetails.js';

// Configuration
const REFRESH_INTERVAL_MS = 30000; // 30 seconds

// DOM element references (set in init)
let summaryCardsContainer = null;
let gpuDetailsContainer = null;
let lastUpdateEl = null;
let clusterSummaryEl = null;
let liveIndicatorEl = null;

// Refresh timer
let refreshTimer = null;

/**
 * Initialize the dashboard.
 * Called when the DOM is ready.
 */
async function init() {
    // Cache DOM references
    summaryCardsContainer = document.getElementById('summary-cards');
    gpuDetailsContainer = document.getElementById('gpu-details');
    lastUpdateEl = document.getElementById('last-update');
    clusterSummaryEl = document.getElementById('cluster-summary');
    liveIndicatorEl = document.getElementById('live-indicator');

    // Load and render data
    await refreshData();

    // Start auto-refresh
    startAutoRefresh();
}

/**
 * Fetch fresh data and render the dashboard.
 */
async function refreshData() {
    try {
        // Fetch data from API
        const data = await fetchDashboardData();

        // Render both sections
        renderSummaryCards(summaryCardsContainer, data.servers);
        renderGpuDetails(gpuDetailsContainer, data.servers);

        // Update header elements
        updateClusterSummary(data.servers);
        updateLastUpdateBadge();
        setLiveIndicatorState('live');

    } catch (error) {
        console.error('Failed to fetch dashboard data:', error);
        setLiveIndicatorState('error');

        // Show error in the summary section
        summaryCardsContainer.innerHTML = `
            <div class="col-12 text-center py-5">
                <div class="text-danger mb-2">Failed to load data</div>
                <div class="text-muted small">${error.message}</div>
                <button class="btn btn-sm btn-outline-secondary mt-3" onclick="location.reload()">
                    Retry
                </button>
            </div>
        `;
    }
}

/**
 * Start the auto-refresh timer.
 */
function startAutoRefresh() {
    if (refreshTimer) {
        clearInterval(refreshTimer);
    }
    refreshTimer = setInterval(() => {
        refreshData();
    }, REFRESH_INTERVAL_MS);
}

/**
 * Update the cluster-wide summary line in the header.
 * Shows: "X/Y servers online · Z/W GPUs free"
 *
 * @param {Object} servers - Server data from the API
 */
function updateClusterSummary(servers) {
    if (!clusterSummaryEl) return;

    const serverNames = Object.keys(servers);
    const totalServers = serverNames.length;
    let onlineServers = 0;
    let totalGpus = 0;
    let freeGpus = 0;

    serverNames.forEach(hostname => {
        const server = servers[hostname];
        if (server.status === 'online') {
            onlineServers++;
        }
        totalGpus += server.summary.total_gpus;
        freeGpus += server.summary.free_gpus;
    });

    clusterSummaryEl.textContent = `${onlineServers}/${totalServers} servers online · ${freeGpus}/${totalGpus} GPUs free`;
}

/**
 * Update the "last update" badge with current time.
 */
function updateLastUpdateBadge() {
    if (lastUpdateEl) {
        const now = new Date();
        const timeStr = now.toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
        lastUpdateEl.textContent = `Updated ${timeStr}`;
    }
}

/**
 * Set the state of the live indicator dot.
 *
 * @param {'live' | 'stale' | 'error'} state - The indicator state
 */
function setLiveIndicatorState(state) {
    if (!liveIndicatorEl) return;

    liveIndicatorEl.classList.remove('stale', 'error');

    if (state === 'stale') {
        liveIndicatorEl.classList.add('stale');
    } else if (state === 'error') {
        liveIndicatorEl.classList.add('error');
    }
    // 'live' is the default state (no extra class)
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    // DOM already loaded
    init();
}
