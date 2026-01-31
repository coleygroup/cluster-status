/**
 * utils.js - Helper functions for the GPU Cluster Dashboard
 *
 * This module provides utility functions for formatting data
 * in a human-readable way.
 */

/**
 * Format bytes/megabytes into a human-readable string.
 * Since GPU memory is typically in MB from the API, we handle that case.
 *
 * @param {number} mb - Value in megabytes
 * @returns {string} - Formatted string like "24.2 GB" or "512 MB"
 *
 * @example
 * formatMemory(24265)  // "24.3 GB"
 * formatMemory(512)    // "512 MB"
 */
export function formatMemory(mb) {
    if (mb >= 1024) {
        return `${(mb / 1024).toFixed(1)} GB`;
    }
    return `${Math.round(mb)} MB`;
}

/**
 * Format a duration in minutes to a human-readable string.
 *
 * @param {number} minutes - Duration in minutes
 * @returns {string} - Formatted string like "5m ago", "2h ago", "3d ago"
 *
 * @example
 * formatDuration(2)   // "2m ago"
 * formatDuration(90)  // "1h ago"
 * formatDuration(1500) // "1d ago"
 */
export function formatDuration(minutes) {
    if (minutes < 1) {
        return "just now";
    }
    if (minutes < 60) {
        return `${minutes}m ago`;
    }
    if (minutes < 1440) {  // Less than 24 hours
        const hours = Math.floor(minutes / 60);
        return `${hours}h ago`;
    }
    const days = Math.floor(minutes / 1440);
    return `${days}d ago`;
}

/**
 * Determine the status level based on a percentage value.
 * Used for coloring memory bars and utilization badges.
 *
 * @param {number} percent - Percentage value (0-100)
 * @returns {string} - Level: "free" (<30%), "partial" (30-80%), "busy" (>80%)
 *
 * @example
 * getUsageLevel(15)  // "free"
 * getUsageLevel(50)  // "partial"
 * getUsageLevel(95)  // "busy"
 */
export function getUsageLevel(percent) {
    if (percent < 30) {
        return "free";
    }
    if (percent < 80) {
        return "partial";
    }
    return "busy";
}

/**
 * Determine the GPU availability level for a server summary.
 *
 * @param {number} freeGpus - Number of GPUs with <30% memory usage
 * @param {number} totalGpus - Total number of GPUs
 * @returns {string} - Level: "all-free", "some-free", or "none-free"
 *
 * @example
 * getAvailabilityLevel(2, 2)  // "all-free"
 * getAvailabilityLevel(1, 2)  // "some-free"
 * getAvailabilityLevel(0, 2)  // "none-free"
 */
export function getAvailabilityLevel(freeGpus, totalGpus) {
    if (freeGpus === totalGpus) {
        return "all-free";
    }
    if (freeGpus > 0) {
        return "some-free";
    }
    return "none-free";
}

/**
 * Escape HTML to prevent XSS when rendering user-provided data.
 *
 * @param {string} str - Input string
 * @returns {string} - HTML-escaped string
 */
export function escapeHtml(str) {
    if (typeof str !== 'string') {
        return String(str);
    }
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}
