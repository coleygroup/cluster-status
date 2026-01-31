/**
 * api.js - Data fetching for the GPU Cluster Dashboard
 *
 * This module handles all communication with the server's API.
 * It uses the modern fetch() API instead of XMLHttpRequest.
 */

/**
 * Fetch the unified dashboard data from the server.
 *
 * The response includes all server statuses, CPU data, GPU data,
 * and computed summaries - everything the dashboard needs in one call.
 *
 * @returns {Promise<Object>} Dashboard data with structure:
 *   {
 *     timestamp: number,
 *     servers: {
 *       [hostname]: {
 *         status: "online" | "offline",
 *         last_seen_mins: number,
 *         cpu: { cpu_percent, num_cpus },
 *         gpus: [ { index, name, total_mem_mb, used_mem_mb, memory_percent, gpu_util, users } ],
 *         summary: { total_gpus, free_gpus, avg_gpu_memory_percent }
 *       }
 *     }
 *   }
 *
 * @throws {Error} If the network request fails
 */
export async function fetchDashboardData() {
    const response = await fetch("/api/dashboard-data");

    if (!response.ok) {
        throw new Error(`API request failed: ${response.status} ${response.statusText}`);
    }

    return response.json();
}
