# Cluster Monitoring System Setup Guide

A complete guide to set up the cluster-dash monitoring system for GPU servers.

## Overview

This system consists of two components:

- **cluster-dash-server**: A web dashboard that displays monitoring data
- **cluster-dash-mole**: Client agents that collect and send data from each server

## Prerequisites

- Shared storage accessible from all servers
- Conda/Miniconda installed on all servers
- Sudo access for systemd service setup
- VPN access to the server network

## Phase 1: Initial Setup

### Step 1: Prepare the Code

```bash
# Navigate to your shared storage location
cd /shared/storage/path/server_status

# You should have two directories:
# - cluster-dash-server/
# - cluster-dash-mole/
```

### Step 2: Choose Your Dashboard Server

Pick one server to host the web dashboard (e.g., `molgpu01`). This server will run the web interface that displays data from all other servers.

**Note**: Don't use the same server for both dashboard and heavy GPU workloads for best performance.

## Phase 2: Set Up the Dashboard Server

### Step 3: Install Dashboard Dependencies

```bash
# SSH to your chosen dashboard server
ssh molgpu01  # Replace with your chosen server

# Navigate to the server directory
cd /shared/storage/path/server_status/cluster-dash-server

# Create conda environment
conda env create -f conda-env.yml
conda activate cluster-dash-server
```

### Step 4: Fix Version Compatibility Issues

**Known Issue**: You may encounter Flask/Werkzeug compatibility errors.

**Solution**: Update to compatible versions:

```bash
conda activate cluster-dash-server
pip install flask==2.3.3 werkzeug==2.3.7 jsonschema==4.19.0 waitress==2.1.2 pandas>=1.5.0 plotly>=5.15.0 numpy==1.23.5 --upgrade
```

### Step 5: Configure Dashboard Authentication

```bash
cd cluster_dash_server
cat > config.py << 'EOF'
PASSCODE = "lab_cluster_2025  # Choose your own password
EOF
cd ..
```

### Step 6: Test Dashboard

```bash
export PYTHONPATH=${PYTHONPATH}:$(pwd)
export FLASK_APP=cluster_dash_server

# Test in development mode first
flask run --host=0.0.0.0 --port=8080
```

Visit `http://YOUR_DASHBOARD_SERVER:8080` in a browser. You should see an empty dashboard.

**Stop the test server** (Ctrl+C) before proceeding.

## Phase 3: Set Up Client Agents

### Step 7: Install Client Dependencies

```bash
# Navigate to the mole directory (can be done on any server due to shared storage)
cd /shared/storage/path/server_status/cluster-dash-mole

# Create conda environment
conda env create -f conda-env.yml
conda activate cluster-dash-mole
```

### Step 8: Fix NVIDIA Compatibility Issues

**Known Issue**: You may encounter `nvidia-ml-py` version mismatches.

**Solution**: Install the newer version:

```bash
conda activate cluster-dash-mole
pip install nvidia-ml-py3 --upgrade
```

### Step 9: Create Smart Startup Script

Create a script that automatically selects the correct config based on hostname:

```bash
cd /shared/storage/path/server_status/cluster-dash-mole
nano smart_startup.py
```

Add this content:

```python
#!/usr/bin/env python3

import sys
import signal
import socket
import os
from os import path as osp
from cluster_dash_mole.main import MainRunner

def get_hostname_config():
    """Get config file based on hostname"""
    hostname = socket.gethostname()
    config_file = f"config_{hostname}.toml"

    if osp.exists(config_file):
        print(f"Using config for {hostname}: {config_file}")
        return config_file
    else:
        print(f"No specific config found for {hostname}, using default config.toml")
        return "config.toml"

def signal_term_handler(signal, frame):
    print("Signal termination:", signal)
    print("Exiting!")
    sys.exit(0)

def main():
    signal.signal(signal.SIGTERM, signal_term_handler)
    signal.signal(signal.SIGINT, signal_term_handler)

    # Set the config file based on hostname
    config_file = get_hostname_config()

    # Modify the settings loader to use our chosen config
    import cluster_dash_mole.settings_loader as settings_loader
    settings_loader._config = None  # Reset any cached config

    # Monkey patch the config path
    original_join = osp.join
    def patched_join(*args):
        if len(args) >= 2 and args[-1] == "../config.toml":
            return config_file
        return original_join(*args)
    osp.join = patched_join

    print(f"Starting cluster monitor with config: {config_file}")
    cdm = MainRunner()
    try:
        cdm.main()
    except Exception as ex:
        print("Exception occurred:")
        print(ex)
        raise ex

if __name__ == '__main__':
    main()
```

Make it executable:

```bash
chmod +x smart_startup.py
```

### Step 10: Create Configuration Files for Each Server

Create a config file for each server:

```bash
# Get list of your server hostnames first
# Run this on each server to see hostname: hostname

# Create config for each server (replace with your actual hostnames)
cp config.toml config_molgpu01.toml
cp config.toml config_molgpu02.toml
cp config.toml config_molgpu03.toml
# ... repeat for each server
```

### Step 11: Configure Each Server's Settings

Edit each config file:

```bash
nano config_molgpu01.toml  # Replace with actual hostname
```

Update the content:

```toml
[Poll_Settings]
poll_interval_in_secs = 300

[Json_Sender_Logger]
use = true
min_interval_in_secs = 30
address_in = "http://molgpu01.mit.edu:8080"  # Replace with your dashboard server
auth_code = "lab_cluster_2024"               # Must match dashboard password

[Google_Sheets_Logger]
use = false

[StdOut_Logger]
use = false
min_interval_in_secs = 300
```

**Important**: Use the same `address_in` (your dashboard server) in ALL config files.

### Step 12: Test Client Agents

Test on each server:

```bash
# SSH to each GPU server
ssh molgpu02  # Replace with actual server

cd /shared/storage/path/server_status/cluster-dash-mole
conda activate cluster-dash-mole
export PYTHONPATH=${PYTHONPATH}:$(pwd)

# Test the client (should run for a few minutes, then Ctrl+C)
python smart_startup.py
```

You should see:

- `Using config for molgpu02: config_molgpu02.toml`
- `Starting cluster monitor...`
- Connection success messages

Test this on 2-3 servers to ensure it works.

## Phase 4: Set Up Production Services

### Step 13: Create Dashboard Service

On your dashboard server:

```bash
sudo nano /etc/systemd/system/cluster-dash-server.service
```

Add this content (update paths for your setup):

```ini
[Unit]
Description=Cluster Dashboard Server
After=network.target

[Service]
Type=simple
User=magicsunxiaoqi
WorkingDirectory=/home/magicsunxiaoqi/cluster-dash-server
Environment=PATH=/home/magicsunxiaoqi/miniconda3/envs/cluster-dash-server/bin
Environment=PYTHONPATH=/home/magicsunxiaoqi/cluster-dash-server
ExecStart=/home/magicsunxiaoqi/miniconda3/envs/cluster-dash-server/bin/waitress-serve --host=0.0.0.0 --port=8080 --call cluster_dash_server:create_app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable cluster-dash-server
sudo systemctl start cluster-dash-server
sudo systemctl status cluster-dash-server
```

### Step 14: Create Client Service on Each Server

On **each GPU server**, create the client service:

```bash
sudo nano /etc/systemd/system/cluster-dash-mole.service
```

Add this content (same for all servers):

```ini
[Unit]
Description=Cluster Dashboard Mole Client
After=network.target

[Service]
Type=simple
User=xiaoqis
WorkingDirectory=/mnt/home/xiaoqis/projects/server_status/cluster-dash-mole
Environment=PATH=/home/xiaoqis/miniconda3/envs/cluster-dash-mole/bin
Environment=PYTHONPATH=/mnt/home/xiaoqis/projects/server_status/cluster-dash-mole
ExecStart=/home/xiaoqis/miniconda3/envs/cluster-dash-mole/bin/python smart_startup.py
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
```

To use venv instead of conda env

```ini
[Unit]
Description=Cluster Dashboard Mole Client
After=network.target

[Service]
Type=simple
User=xiaoqis
WorkingDirectory=/mnt/home/xiaoqis/projects/server_status/cluster-dash-mole
Environment=VIRTUAL_ENV=/mnt/home/xiaoqis/projects/server_status/cluster-dash-mole/.venv
Environment=PYTHONPATH=/mnt/home/xiaoqis/projects/server_status/cluster-dash-mole
ExecStart=/mnt/home/xiaoqis/projects/server_status/cluster-dash-mole/.venv/bin/python smart_startup.py
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
```

Enable and start on each server:

```bash
sudo systemctl daemon-reload
sudo systemctl enable cluster-dash-mole
sudo systemctl start cluster-dash-mole
sudo systemctl status cluster-dash-mole
```

## Phase 5: Verification and Management

### Step 15: Verify Everything Works

1. **Check dashboard**: Visit `http://YOUR_DASHBOARD_SERVER:8080`
2. **Check services**:

   ```bash
   # On dashboard server
   sudo systemctl status cluster-dash-server

   # On each client server
   sudo systemctl status cluster-dash-mole
   ```

3. **Check logs**:

   ```bash
   # Dashboard logs
   sudo journalctl -u cluster-dash-server -f

   # Client logs
   sudo journalctl -u cluster-dash-mole -f
   ```

### Service Management Commands

```bash
# Start/stop services
sudo systemctl start cluster-dash-mole
sudo systemctl stop cluster-dash-mole
sudo systemctl restart cluster-dash-mole

# Enable/disable auto-start on boot
sudo systemctl enable cluster-dash-mole
sudo systemctl disable cluster-dash-mole

# Check status
sudo systemctl status cluster-dash-mole

# View logs
sudo journalctl -u cluster-dash-mole -n 50
sudo journalctl -u cluster-dash-mole --since "1 hour ago"
```

## Troubleshooting

### Common Issues

1. **Flask/Werkzeug compatibility error**:

   ```bash
   pip install flask==2.3.3 werkzeug==2.3.7 --upgrade
   ```

2. **NVIDIA ML library mismatch**:

   ```bash
   pip install nvidia-ml-py3 --upgrade
   ```

3. **Service fails to start**:

   ```bash
   sudo journalctl -u cluster-dash-mole -n 20
   ```

4. **Dashboard shows no data**:

   - Check if clients are sending data: `sudo journalctl -u cluster-dash-mole -f`
   - Verify `address_in` in config files points to correct dashboard server
   - Check firewall settings on dashboard server

5. **Permission errors**:
   - Ensure the user in service files has access to the directories
   - Check conda environment paths are correct

### Testing Connectivity

```bash
# Test if dashboard server is reachable
curl http://YOUR_DASHBOARD_SERVER:8080

# Test manual client run
cd cluster-dash-mole
conda activate cluster-dash-mole
export PYTHONPATH=${PYTHONPATH}:$(pwd)
python smart_startup.py
```

## Dashboard Features

Once running, your dashboard provides:

- **Main page**: Overview of all servers with health status
- **GPU Data**: GPU memory usage visualization
- **CPU Data**: CPU utilization charts
- **Memory**: Available vs used memory
- **Storage**: Root drive usage
- **Load Average**: System load indicators

## Notes

- The system polls data every 5 minutes by default
- Services automatically restart if they crash
- All services start automatically on server reboot
- Data is sent over HTTP (secure enough behind VPN)
- The smart startup script automatically selects the correct config based on hostname

## Maintenance

- **Update configs**: Edit the `config_*.toml` files and restart services
- **Add new servers**: Create new config file and set up the mole service
- **Move dashboard**: Update `address_in` in all configs and restart services
