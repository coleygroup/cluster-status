/**
 * gpuDetails.js - Render the per-server GPU detail panels
 *
 * This module creates the bottom section of the dashboard showing
 * detailed GPU information for each server, including memory bars,
 * utilization bars, and user lists.
 */

import { formatMemory, getUsageLevel, escapeHtml } from './utils.js';

/**
 * Render GPU detail panels for all servers.
 * Uses fade transition to avoid jarring refresh.
 *
 * @param {HTMLElement} container - The DOM element to render panels into
 * @param {Object} servers - Server data from the API
 */
export function renderGpuDetails(container, servers) {
    const serverNames = Object.keys(servers).sort();

    if (serverNames.length === 0) {
        container.innerHTML = `
            <div class="text-center text-muted py-3">
                No GPU data available.
            </div>
        `;
        return;
    }

    // Build new content
    const fragment = document.createDocumentFragment();
    serverNames.forEach(hostname => {
        const server = servers[hostname];
        const panel = createServerPanel(hostname, server);
        fragment.appendChild(panel);
    });

    // Fade out, swap content, fade in
    container.classList.add('fade-container');
    container.classList.add('fade-out');

    setTimeout(() => {
        container.innerHTML = '';
        container.appendChild(fragment);
        container.classList.remove('fade-out');
    }, 150);
}

/**
 * Create a detail panel for one server showing all its GPUs.
 *
 * @param {string} hostname - Server hostname
 * @param {Object} server - Server data with gpus array
 * @returns {HTMLElement} - The panel element
 */
function createServerPanel(hostname, server) {
    const panel = document.createElement('div');
    panel.className = `server-detail-panel status-${server.status}`;
    panel.id = `server-${hostname}`;

    const statusBadge = server.status === 'online'
        ? '<span class="badge bg-success">Online</span>'
        : '<span class="badge bg-secondary">Offline</span>';

    // Panel header
    panel.innerHTML = `
        <div class="panel-header">
            <span class="panel-title">${escapeHtml(hostname)}</span>
            ${statusBadge}
        </div>
        <div class="row g-2 gpu-grid"></div>
    `;

    // Add a card for each GPU
    const gpuGrid = panel.querySelector('.gpu-grid');
    server.gpus.forEach(gpu => {
        const gpuCol = createGpuCard(gpu);
        gpuGrid.appendChild(gpuCol);
    });

    // If no GPUs, show message
    if (server.gpus.length === 0) {
        gpuGrid.innerHTML = '<div class="col-12 text-muted ps-2">No GPU data</div>';
    }

    return panel;
}

/**
 * Create a card for a single GPU showing memory bar, utilization bar,
 * and user info.
 *
 * @param {Object} gpu - GPU data object
 * @returns {HTMLElement} - Column element wrapping the GPU card
 */
function createGpuCard(gpu) {
    const col = document.createElement('div');
    col.className = 'col-12 col-sm-6 col-lg-4 col-xl-3';

    // Memory bar level
    const memLevel = getUsageLevel(gpu.memory_percent);
    const utilLevel = getUsageLevel(gpu.gpu_util);

    // Format memory usage text for the bar label
    const memUsedStr = formatMemory(gpu.used_mem_mb);
    const memTotalStr = formatMemory(gpu.total_mem_mb);
    const memLabel = `${memUsedStr} / ${memTotalStr} (${gpu.memory_percent}%)`;

    // Build user list HTML
    const userHtml = buildUserList(gpu.users);

    col.innerHTML = `
        <div class="gpu-card">
            <div class="gpu-name">
                <span class="gpu-index">GPU ${gpu.index}</span>
                &middot; ${escapeHtml(gpu.name)}
            </div>

            <!-- Memory usage bar -->
            <div class="memory-bar-container" title="${memLabel}">
                <div class="memory-bar-fill level-${memLevel}"
                     style="width: ${gpu.memory_percent}%">
                </div>
                <span class="memory-bar-label">${memLabel}</span>
            </div>

            <!-- GPU utilization bar (thin) -->
            <div class="util-bar-container" title="GPU Util: ${gpu.gpu_util}%">
                <div class="util-bar-fill level-${utilLevel}"
                     style="width: ${gpu.gpu_util}%">
                </div>
            </div>
            <div class="bar-label-row">
                <span class="bar-label-title">GPU Util</span>
                <span class="bar-label-value">${gpu.gpu_util}%</span>
            </div>

            <!-- User list -->
            ${userHtml}
        </div>
    `;

    return col;
}

/**
 * Build HTML for the list of users running processes on a GPU.
 *
 * @param {Object} users - Users dict from API, e.g. { "alice": { "pid": 1234, "used_mem": 8192 } }
 * @returns {string} - HTML string for the user list
 */
function buildUserList(users) {
    const userEntries = Object.entries(users || {});

    if (userEntries.length === 0) {
        return `<div class="user-list"><span class="no-users">&mdash; idle</span></div>`;
    }

    const items = userEntries.map(([username, info]) => {
        // The user info structure may vary - handle both formats
        const mem = info.used_mem ? formatMemory(info.used_mem) : '';
        const pid = info.pid ? `PID ${info.pid}` : '';
        const detail = [pid, mem].filter(Boolean).join(' · ');

        return `
            <div class="user-entry">
                <span class="username">${escapeHtml(username)}</span>
                <span>${escapeHtml(detail)}</span>
            </div>
        `;
    }).join('');

    return `<div class="user-list">${items}</div>`;
}
