export async function fetchHistoryData(hours = 24) {
    const response = await fetch(`/api/history-data?hours=${hours}`);

    if (!response.ok) {
        throw new Error(`API request failed: ${response.status} ${response.statusText}`);
    }

    return response.json();
}
