# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**cluster-dash** is a distributed GPU cluster monitoring system with two components:
- **cluster-dash-server**: Flask web dashboard displaying real-time cluster metrics
- **cluster-dash-mole**: Client agents collecting and sending system/GPU data from each server

## Build & Run Commands

Both projects use **uv** for dependency management.

### Server (Dashboard)

```bash
cd cluster-dash-server
uv sync                                    # Install dependencies

# Development
export FLASK_APP=cluster_dash_server
export PYTHONPATH=${PYTHONPATH}:$(pwd)
flask run --host=0.0.0.0 --port=8080

# Production
waitress-serve --host=0.0.0.0 --port=8080 --call cluster_dash_server:create_app

# Test with sample data
curl -d "@etc/example_data1.json" -H "Content-Type: application/json" -X POST http://localhost:8080
```

### Mole (Client Agent)

```bash
cd cluster-dash-mole
uv sync                                    # Install dependencies

export PYTHONPATH=${PYTHONPATH}:$(pwd)
python smart_startup.py                    # Auto-selects config based on hostname
```

## Architecture

```
cluster-dash-mole (8 GPU servers)           cluster-dash-server (Dashboard)
┌────────────────────────────┐              ┌──────────────────────────────┐
│ smart_startup.py           │              │ Flask App (create_app)       │
│   └─ MainRunner.main()     │──POST JSON──▶│   ├─ POST / (validate+store) │
│      ├─ gpu_data.py        │  (every 5s)  │   ├─ GET / (status table)    │
│      ├─ cpu_data.py        │              │   ├─ GET /gpu-data (charts)  │
│      ├─ general_machine_   │              │   └─ stored_results_[host]   │
│      │  data.py            │              │      (in-memory dict)        │
│      └─ comms.py           │              └──────────────────────────────┘
│         (JsonSenderLogger) │
└────────────────────────────┘
```

**Data Flow**:
1. Mole polls system metrics every 300s (configurable)
2. Sends JSON to server every 5s minimum via `comms.py:JsonSenderLogger`
3. Server validates against `machine-post-schema.json`, stores in memory
4. Dashboard renders via server-side Plotly (CPU/memory/disk) or client-side Plotly.js (GPU)

## Key Files

| File | Purpose |
|------|---------|
| `cluster-dash-mole/smart_startup.py` | Entry point - auto-selects config by hostname |
| `cluster-dash-mole/cluster_dash_mole/main.py` | MainRunner - polling loop orchestration |
| `cluster-dash-mole/cluster_dash_mole/gpu_data.py` | NVIDIA NVML API for GPU metrics |
| `cluster-dash-mole/cluster_dash_mole/comms.py` | Communication backends (JSON, Google Sheets, stdout) |
| `cluster-dash-mole/config_molgpu*.toml` | Per-server configuration files |
| `cluster-dash-server/cluster_dash_server/__init__.py` | Flask app factory + all routes |
| `cluster-dash-server/cluster_dash_server/machine-post-schema.json` | JSON Schema for data validation |
| `cluster-dash-server/cluster_dash_server/static/scripts/renderGpuData.js` | Client-side GPU chart rendering |

## Data Schema (POST to server)

```json
{
  "hostname": "string",
  "timestamp": "number",
  "auth_code": "string",
  "cpu": { "cpu_percent", "load_avgs", "num_cpus" },
  "memory": { "total_gb", "available_gb", "used_gb" },
  "disk": { "[mount]": { "total_gb", "used_gb", "percent_used" } },
  "gpu": { "[id]": { "name", "total_mem", "used_mem", "gpu_util", "users" } }
}
```

## Configuration

- Auth passcode: `cluster_dash_server/config.py` → `PASSCODE = "lab_cluster_2025"`
- Mole configs: `config_[hostname].toml` files in `cluster-dash-mole/`
- Poll interval: `Poll_Settings.poll_interval_in_secs` (default 300)
- Min send interval: `Json_Sender_Logger.min_interval_in_secs` (default 5)

## Dual Rendering Strategy

- **Server-side Plotly** (`plotly_express.html`): CPU, memory, disk, load charts - Python generates JSON
- **Client-side Plotly.js** (`simple_chart.html`): GPU data - fetches from `/data-out/gpu-data-simple`

## Systemd Services

Both components run as systemd services in production. See `setup.md` for full deployment instructions:
- `cluster-dash-server.service` on dashboard host
- `cluster-dash-mole.service` on each GPU server
