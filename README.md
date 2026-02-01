# Cluster Monitoring System - Deployment Guide

A step-by-step guide to deploy the GPU cluster monitoring dashboard.

## What You're Deploying

- **Dashboard Server** (`cluster-dash-server`): A Flask web app that displays GPU usage across your cluster. Runs on ONE machine (your dashboard host).
- **Mole Clients** (`cluster-dash-mole`): Agents that collect GPU/CPU data. Runs on EACH GPU server you want to monitor.

```
GPU Servers (run mole)              Dashboard Host (run server)
┌─────────────────────┐             ┌─────────────────────────┐
│ molgpu01 (mole) ────┼──POST──────▶│                         │
│ molgpu02 (mole) ────┼──POST──────▶│  Dashboard Server       │
│ molgpu03 (mole) ────┼──POST──────▶│  http://host:8080       │
│ ...                 │             │                         │
└─────────────────────┘             └─────────────────────────┘
```

---

## Part 1: Deploy the Dashboard Server

Do this on the machine that will host your dashboard web interface.

### Step 1.1: Clone and Install Dependencies

```bash
# Clone the repo (or copy it to your server)
cd /path/to/your/projects
git clone <repo-url> server_status
cd server_status/cluster-dash-server

# Install dependencies with uv
uv sync
```

This creates a `.venv` folder with all Python dependencies.

### Step 1.2: Test the Server Manually

Before setting up systemd, verify everything works by running it directly:

```bash
cd /path/to/server_status/cluster-dash-server

# Run the production server in foreground
uv run waitress-serve --host=0.0.0.0 --port=8080 --call cluster_dash_server:create_app
```

You should see output like:
```
INFO:waitress:Serving on http://0.0.0.0:8080
```

**Verification:**

1. Open `http://YOUR_SERVER_IP:8080` in a browser - you should see the dashboard (empty, no data yet)
2. In another terminal, send test data:
   ```bash
   cd /path/to/server_status/cluster-dash-server
   curl -d "@etc/example_data1.json" -H "Content-Type: application/json" -X POST http://localhost:8080
   ```
3. Refresh the browser - you should see the test server appear

If both work, press `Ctrl+C` to stop the manual server. Now you're ready for the real deployment.

### Step 1.3: Create the Systemd Service File

Systemd keeps the server running in the background, auto-restarts on crashes, and starts on boot.

Create the service file:

```bash
sudo nano /etc/systemd/system/cluster-dash-server.service
```

Paste this content (adjust paths and username to match your setup):

```ini
[Unit]
Description=Cluster Dashboard Server
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/path/to/server_status/cluster-dash-server
Environment=VIRTUAL_ENV=/path/to/server_status/cluster-dash-server/.venv
Environment=PYTHONPATH=/path/to/server_status/cluster-dash-server
ExecStart=/path/to/server_status/cluster-dash-server/.venv/bin/waitress-serve --host=0.0.0.0 --port=8080 --call cluster_dash_server:create_app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**What to change:**
- `YOUR_USERNAME`: Your Linux username (e.g., `xiaoqis`)
- `/path/to/server_status`: The actual path where you cloned the repo

### Step 1.4: Start the Service

```bash
# Reload systemd to recognize the new service
sudo systemctl daemon-reload

# Start the service
sudo systemctl start cluster-dash-server

# Check if it's running
sudo systemctl status cluster-dash-server
```

You should see `Active: active (running)`. If not, check the logs:

```bash
sudo journalctl -u cluster-dash-server -n 30
```

### Step 1.5: Enable Auto-Start on Boot

```bash
sudo systemctl enable cluster-dash-server
```

**Verification:**
- Open `http://YOUR_SERVER_IP:8080` in a browser
- The dashboard should be accessible

The dashboard server is now deployed. It will run even after you log out, and restart automatically on reboot.

---

## Part 2: Deploy Mole Clients on GPU Servers

Repeat these steps on EACH GPU server you want to monitor.

### Step 2.1: Clone and Install Dependencies

```bash
cd /path/to/your/projects
git clone <repo-url> server_status   # or copy the existing folder
cd server_status/cluster-dash-mole

uv sync
```

### Step 2.2: Create Your Config File

Each server needs its own config file named `config_<hostname>.toml`. The `smart_startup.py` script automatically picks the right one based on hostname.

Check your hostname:
```bash
hostname
# Example output: molgpu01
```

Create/edit the config file for this server:

```bash
nano config_$(hostname).toml
```

Paste this content:

```toml
[Poll_Settings]
poll_interval_in_secs = 300

[Json_Sender_Logger]
use = true
min_interval_in_secs = 5
address_in = "http://YOUR_DASHBOARD_SERVER:8080"
auth_code = "lab_cluster_2025"

[Google_Sheets_Logger]
use = false

[StdOut_Logger]
use = false
```

**What to change:**
- `YOUR_DASHBOARD_SERVER`: The hostname or IP of your dashboard server (e.g., `molgpu07.mit.edu` or `192.168.1.100`)
- `8080`: Change if your dashboard uses a different port
- `auth_code`: Must match `PASSCODE` in `cluster-dash-server/cluster_dash_server/config.py`

### Step 2.3: Test the Client Manually

Before systemd, verify it works:

```bash
cd /path/to/server_status/cluster-dash-mole

PYTHONPATH=$(pwd):$PYTHONPATH python smart_startup.py
```

You should see output showing data being collected and sent:
```
Starting polling loop...
Sending data to http://YOUR_DASHBOARD_SERVER:8080
Response: 200 OK
```

Check the dashboard in your browser - this server should now appear.

Press `Ctrl+C` to stop the manual run.

### Step 2.4: Create the Systemd Service File

```bash
sudo nano /etc/systemd/system/cluster-dash-mole.service
```

Paste this content (adjust paths and username):

```ini
[Unit]
Description=Cluster Dashboard Mole Client
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/path/to/server_status/cluster-dash-mole
Environment=VIRTUAL_ENV=/path/to/server_status/cluster-dash-mole/.venv
Environment=PYTHONPATH=/path/to/server_status/cluster-dash-mole
ExecStart=/path/to/server_status/cluster-dash-mole/.venv/bin/python smart_startup.py
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
```

### Step 2.5: Start and Enable the Service

```bash
sudo systemctl daemon-reload
sudo systemctl start cluster-dash-mole
sudo systemctl status cluster-dash-mole

# Enable auto-start on boot
sudo systemctl enable cluster-dash-mole
```

### Step 2.6: Verify on Dashboard

Open the dashboard in your browser. Within 30 seconds, this server should appear with real GPU data.

Repeat Part 2 on all remaining GPU servers.

---

## Part 3: Verification & Maintenance

### Check Everything is Running

On dashboard server:
```bash
sudo systemctl status cluster-dash-server
curl http://localhost:8080/api/gpu-summary
```

On each GPU server:
```bash
sudo systemctl status cluster-dash-mole
```

### Common Commands

```bash
# View live logs
sudo journalctl -u cluster-dash-server -f
sudo journalctl -u cluster-dash-mole -f

# Restart after code changes
sudo systemctl restart cluster-dash-server
sudo systemctl restart cluster-dash-mole

# Stop a service
sudo systemctl stop cluster-dash-server

# Check last 50 log lines
sudo journalctl -u cluster-dash-mole -n 50
```

### API Endpoints (Dashboard)

| Endpoint | Description |
|----------|-------------|
| `http://host:8080/` | Web dashboard |
| `http://host:8080/api/dashboard-data` | JSON data for all servers |
| `http://host:8080/api/gpu-summary` | Text summary (good for terminal) |

---

## Troubleshooting

### Dashboard shows "offline" for a server

1. Check if mole is running on that server:
   ```bash
   sudo systemctl status cluster-dash-mole
   ```

2. Check mole logs for errors:
   ```bash
   sudo journalctl -u cluster-dash-mole -n 50
   ```

3. Verify network connectivity from mole to dashboard:
   ```bash
   curl http://YOUR_DASHBOARD_SERVER:8080
   ```

4. Check `address_in` in the config file points to the correct dashboard URL

### Service fails to start

```bash
# Check detailed error
sudo journalctl -u cluster-dash-server -n 30

# Common fixes:
# - Wrong paths in service file
# - Missing .venv (run `uv sync` again)
# - Permission issues (check User= matches actual owner)
```

### Auth code mismatch

The client's `auth_code` in config must match the server's `PASSCODE` in `cluster-dash-server/cluster_dash_server/config.py`.

### Port already in use

```bash
# Find what's using port 8080
sudo lsof -i :8080

# Kill it or use a different port
```

---

## Configuration Reference

### Server Auth (`cluster-dash-server/cluster_dash_server/config.py`)

```python
PASSCODE = "lab_cluster_2025"  # Change this for security
```

### Client Config (`cluster-dash-mole/config_<hostname>.toml`)

| Setting | Description | Default |
|---------|-------------|---------|
| `poll_interval_in_secs` | How often to collect system data | 300 |
| `min_interval_in_secs` | Minimum time between sends to server | 5 |
| `address_in` | Dashboard server URL | - |
| `auth_code` | Must match server's PASSCODE | - |
