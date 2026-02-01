# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**cluster-status** is a distributed GPU cluster monitoring system with two components:
- **cluster-dash-server**: Flask web dashboard displaying real-time cluster metrics
- **cluster-dash-mole**: Client agents collecting and sending system/GPU data from each server

## Build & Run Commands

Both projects use **uv** for dependency management.

### Server (Dashboard)

```bash
cd cluster-dash-server
uv sync                                    # Install dependencies

# Development
FLASK_APP=cluster_dash_server PYTHONPATH=$(pwd):$PYTHONPATH uv run flask run --host=0.0.0.0 --port=8080

# Production
uv run waitress-serve --host=0.0.0.0 --port=8080 --call cluster_dash_server:create_app

# Test with sample data
curl -d "@etc/example_data1.json" -H "Content-Type: application/json" -X POST http://localhost:8080
```

### Mole (Client Agent)

```bash
cd cluster-dash-mole
uv sync                                    # Install dependencies

PYTHONPATH=$(pwd):$PYTHONPATH python smart_startup.py   # Auto-selects config based on hostname
```

## Architecture

```
cluster-dash-mole (8 GPU servers)           cluster-dash-server (Dashboard)
┌────────────────────────────┐              ┌──────────────────────────────┐
│ smart_startup.py           │              │ Flask App (create_app)       │
│   └─ MainRunner.main()     │──POST JSON──▶│   ├─ POST / (validate+store) │
│      ├─ gpu_data.py        │  (every 5s)  │   ├─ GET / (dashboard.html)  │
│      ├─ cpu_data.py        │              │   ├─ GET /api/dashboard-data │
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
4. Dashboard renders via single-page app with 30-second auto-refresh

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
| `cluster-dash-server/cluster_dash_server/templates/dashboard.html` | Single-page dashboard template |
| `cluster-dash-server/cluster_dash_server/static/styles/dashboard.css` | Dashboard styling |
| `cluster-dash-server/cluster_dash_server/static/scripts/dashboard/` | ES6 modules for frontend |

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Serve dashboard HTML |
| `/` | POST | Data ingestion from mole agents |
| `/api/dashboard-data` | GET | JSON API for dashboard (servers, GPUs, summaries) |
| `/api/gpu-summary` | GET | CLI-friendly text summary with ANSI colors |
| `/data-out/gpu-data-simple` | GET | Legacy API for backwards compatibility |

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

## Dashboard API Response (`/api/dashboard-data`)

```json
{
  "timestamp": 123456,
  "servers": {
    "molgpu01": {
      "status": "online|offline",
      "last_seen_mins": 2,
      "cpu": { "cpu_percent": 45, "num_cpus": 64 },
      "gpus": [{ "index": 0, "name": "RTX 3090", "total_mem_mb": 24266, "used_mem_mb": 20, "memory_percent": 0, "gpu_util": 0, "users": {} }],
      "summary": { "total_gpus": 2, "free_gpus": 2, "avg_gpu_memory_percent": 0 }
    }
  }
}
```

## Configuration

- Auth passcode: `cluster_dash_server/config.py` -> `PASSCODE = "lab_cluster_2025"`
- Mole configs: `config_[hostname].toml` files in `cluster-dash-mole/`
- Poll interval: `Poll_Settings.poll_interval_in_secs` (default 300)
- Min send interval: `Json_Sender_Logger.min_interval_in_secs` (default 5)

## Frontend Architecture

Single-page dashboard with:
- **Top section**: Summary cards (8 servers) with status, CPU %, GPU availability
- **Bottom section**: GPU detail panels per server with memory bars and user lists
- **Auto-refresh**: 30-second polling via ES6 modules
- **Styling**: CSS-based memory bars (no Plotly), dark theme, Bootstrap 5

JavaScript modules in `static/scripts/dashboard/`:
- `main.js` - Entry point, auto-refresh timer
- `api.js` - fetch() data fetching
- `summaryCards.js` - Server overview cards
- `gpuDetails.js` - GPU detail panels with memory bars
- `utils.js` - formatMemory, formatDuration helpers

## Systemd Services

Both components run as systemd services in production. See `setup.md` for service configs:
- `cluster-dash-server.service` on dashboard host
- `cluster-dash-mole.service` on each GPU server
