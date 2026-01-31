/**
 * summaryCards.js - Render the server summary cards
 *
 * This module creates the top section of the dashboard showing
 * a card for each server with quick status info.
 */

import { formatDuration, getAvailabilityLevel, escapeHtml } from './utils.js';

/**
 * Render all server summary cards into the container.
 *
 * @param {HTMLElement} container - The DOM element to render cards into
 * @param {Object} servers - Server data from the API
 *
 * @example
 * const container = document.getElementById('summary-cards');
 * renderSummaryCards(container, data.servers);
 */
export function renderSummaryCards(container, servers) {
    // Clear existing content
    container.innerHTML = '';

    // Get sorted server names
    const serverNames = Object.keys(servers).sort();

    // Handle empty state
    if (serverNames.length === 0) {
        container.innerHTML = `
            <div class="col-12 text-center text-muted py-5">
                No server data available. Waiting for servers to report...
            </div>
        `;
        return;
    }

    // Create a card for each server
    serverNames.forEach(hostname => {
        const server = servers[hostname];
        const card = createServerCard(hostname, server);
        container.appendChild(card);
    });
}

/**
 * Create a single server summary card element.
 *
 * @param {string} hostname - Server hostname (e.g., "molgpu01")
 * @param {Object} server - Server data object
 * @returns {HTMLElement} - The card wrapper element (col div)
 */
function createServerCard(hostname, server) {
    const { status, last_seen_mins, cpu, summary } = server;

    // Determine GPU availability class
    const availLevel = getAvailabilityLevel(summary.free_gpus, summary.total_gpus);

    // Create wrapper column
    const col = document.createElement('div');
    col.className = 'col-6 col-sm-4 col-md-3 col-xl-2';

    // Build the card HTML
    col.innerHTML = `
        <div class="server-card status-${status}">
            <div class="server-name">${escapeHtml(hostname)}</div>
            <div class="server-status">
                ${status === 'online'
                    ? `<span class="text-success">Online</span> &middot; ${formatDuration(last_seen_mins)}`
                    : `<span class="text-secondary">Offline</span> &middot; ${formatDuration(last_seen_mins)}`
                }
            </div>

            <div class="metric-row">
                <span class="metric-label">CPU</span>
                <span class="metric-value">${cpu.cpu_percent}%</span>
            </div>

            <div class="metric-row">
                <span class="metric-label">GPUs</span>
                <span class="gpu-avail-badge ${availLevel}">
                    ${summary.free_gpus}/${summary.total_gpus} free
                </span>
            </div>

            <div class="metric-row">
                <span class="metric-label">Avg GPU Mem</span>
                <span class="metric-value">${summary.avg_gpu_memory_percent}%</span>
            </div>
        </div>
    `;

    return col;
}
