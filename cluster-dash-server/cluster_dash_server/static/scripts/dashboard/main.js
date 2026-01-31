/**
 * main.js - Entry point for the GPU Cluster Dashboard
 *
 * This is the main module that:
 * 1. Initializes the dashboard on page load
 * 2. Fetches data from the API
 * 3. Renders the summary cards and GPU details
 * 4. Sets up auto-refresh (30 second polling)
 */

import { fetchDashboardData } from './api.js';
import { renderSummaryCards } from './summaryCards.js';
import { renderGpuDetails } from './gpuDetails.js';

// Configuration
const REFRESH_INTERVAL_MS = 30 * 1000;  // 30 seconds

// DOM element references (set in init)
let summaryCardsContainer = null;
let gpuDetailsContainer = null;
let refreshCountdownEl = null;
let lastUpdateEl = null;

// State
let countdownTimer = null;
let secondsRemaining = 30;

/**
 * Initialize the dashboard.
 * Called when the DOM is ready.
 */
async function init() {
    // Cache DOM references
    summaryCardsContainer = document.getElementById('summary-cards');
    gpuDetailsContainer = document.getElementById('gpu-details');
    refreshCountdownEl = document.getElementById('refresh-countdown');
    lastUpdateEl = document.getElementById('last-update');

    // Initial data load
    await refreshData();

    // Start auto-refresh timer
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

        // Update "last update" badge
        updateLastUpdateBadge();

    } catch (error) {
        console.error('Failed to fetch dashboard data:', error);

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
 * Start the auto-refresh countdown and periodic data fetching.
 */
function startAutoRefresh() {
    // Reset countdown
    secondsRemaining = 30;
    updateCountdownBadge();

    // Clear any existing timer
    if (countdownTimer) {
        clearInterval(countdownTimer);
    }

    // Update countdown every second
    countdownTimer = setInterval(() => {
        secondsRemaining--;

        if (secondsRemaining <= 0) {
            // Time to refresh
            secondsRemaining = 30;
            refreshData();
        }

        updateCountdownBadge();
    }, 1000);
}

/**
 * Update the countdown badge text.
 */
function updateCountdownBadge() {
    if (refreshCountdownEl) {
        refreshCountdownEl.textContent = `Auto-refresh in ${secondsRemaining}s`;
    }
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
        lastUpdateEl.textContent = `Updated: ${timeStr}`;
    }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    // DOM already loaded
    init();
}
