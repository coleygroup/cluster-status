/**
 * summaryCards.js - Render the server summary cards
 *
 * This module creates the top section of the dashboard showing
 * a card for each server with quick status info.
 */

import { formatDuration, getAvailabilityLevel, escapeHtml } from './utils.js';

// Track currently selected server for highlight state
let selectedHostname = null;

/**
 * Render all server summary cards into the container.
 * Uses fade transition to avoid jarring refresh.
 *
 * @param {HTMLElement} container - The DOM element to render cards into
 * @param {Object} servers - Server data from the API
 */
export function renderSummaryCards(container, servers) {
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

    // Build new content
    const fragment = document.createDocumentFragment();
    serverNames.forEach(hostname => {
        const server = servers[hostname];
        const card = createServerCard(hostname, server);
        fragment.appendChild(card);
    });

    // Fade out, swap content, fade in
    container.classList.add('fade-container');
    container.classList.add('fade-out');

    setTimeout(() => {
        container.innerHTML = '';
        container.appendChild(fragment);
        // Re-apply selected state if applicable
        if (selectedHostname) {
            const selectedCard = container.querySelector(`[data-hostname="${selectedHostname}"]`);
            if (selectedCard) {
                selectedCard.classList.add('is-selected');
            }
        }
        container.classList.remove('fade-out');
    }, 150);
}

/**
 * Create a single server summary card element.
 *
 * @param {string} hostname - Server hostname (e.g., "molgpu01")
 * @param {Object} server - Server data object
 * @returns {HTMLElement} - The card wrapper element (col div)
 */
function createServerCard(hostname, server) {
    const { status, last_seen_mins, cpu, summary, gpu_error } = server;

    // Determine GPU availability class
    const availLevel = gpu_error ? 'level-error' : getAvailabilityLevel(summary.free_gpus, summary.total_gpus);

    // Create wrapper column
    const col = document.createElement('div');
    col.className = 'col-6 col-sm-4 col-md-3 col-xl-2';

    // GPU metrics section - show error or normal stats
    const gpuMetrics = gpu_error
        ? `
            <div class="metric-row">
                <span class="metric-label">GPUs</span>
                <span class="gpu-avail-badge level-error">ERROR</span>
            </div>
            <div class="metric-row">
                <span class="metric-label gpu-error-text">Driver error</span>
            </div>
        `
        : `
            <div class="metric-row">
                <span class="metric-label">GPUs</span>
                <span class="gpu-avail-badge ${availLevel}">
                    ${summary.free_gpus}/${summary.total_gpus} free
                </span>
            </div>

            <div class="metric-row">
                <span class="metric-label">Avg GPU Util</span>
                <span class="metric-value">${summary.avg_gpu_util ?? 0}%</span>
            </div>

            <div class="metric-row">
                <span class="metric-label">Avg GPU Mem</span>
                <span class="metric-value">${summary.avg_gpu_memory_percent}%</span>
            </div>
        `;

    // Build the card HTML with divider separating identity from metrics
    col.innerHTML = `
        <div class="server-card status-${status}${gpu_error ? ' has-gpu-error' : ''}" data-hostname="${escapeHtml(hostname)}">
            <div class="server-name">${escapeHtml(hostname)}</div>
            <div class="server-status">
                ${status === 'online'
                    ? `<span class="text-success">Online</span> &middot; ${formatDuration(last_seen_mins)}`
                    : `<span class="text-secondary">Offline</span> &middot; ${formatDuration(last_seen_mins)}`
                }
            </div>

            <div class="card-divider"></div>

            <div class="metric-row">
                <span class="metric-label">CPU</span>
                <span class="metric-value">${cpu.cpu_percent}%</span>
            </div>

            ${gpuMetrics}
        </div>
    `;

    const cardEl = col.querySelector('.server-card');

    // Make card clickable - scroll to detail panel with proper offset
    cardEl.addEventListener('click', () => {
        const detailPanel = document.getElementById(`server-${hostname}`);
        if (detailPanel) {
            // Clear previous selection
            document.querySelectorAll('.server-card.is-selected').forEach(el => {
                el.classList.remove('is-selected');
            });
            document.querySelectorAll('.server-detail-panel.is-target').forEach(el => {
                el.classList.remove('is-target');
            });

            // Set new selection
            cardEl.classList.add('is-selected');
            detailPanel.classList.add('is-target');
            selectedHostname = hostname;

            // Calculate the actual height of sticky elements
            const header = document.querySelector('.dashboard-header');
            const summarySection = document.getElementById('summary-section');
            const headerHeight = header ? header.offsetHeight : 60;
            const summaryHeight = summarySection ? summarySection.offsetHeight : 200;
            const totalOffset = headerHeight + summaryHeight + 16; // 16px extra padding

            // Calculate target scroll position
            const targetY = detailPanel.getBoundingClientRect().top + window.scrollY - totalOffset;

            // Smooth scroll to calculated position
            window.scrollTo({
                top: targetY,
                behavior: 'smooth'
            });
        }
    });

    return col;
}

/**
 * Clear the selected state (useful when refreshing data).
 */
export function clearSelection() {
    selectedHostname = null;
    document.querySelectorAll('.server-card.is-selected').forEach(el => {
        el.classList.remove('is-selected');
    });
    document.querySelectorAll('.server-detail-panel.is-target').forEach(el => {
        el.classList.remove('is-target');
    });
}
