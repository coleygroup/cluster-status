# Cluster Dash Server

_The corresponding server component of the cluster dash monitor._

**NEW: Updated this to use Flask which means that one can do plotting completely in Python if one so desires! (see
CPU utilization as an example).**

# 1. Installation

Install the packages using uv:

If you don't have uv, you can install it via:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then install the packages:

```bash
uv sync
```

Add this directory to the PYTHONPATH:

```bash
export PYTHONPATH=${PYTHONPATH}:$(pwd)
```

# 2. Configuration

Overwrite the PASSCODE if you want (by creating a `config.py` in the `cluster_dash_server` folder.)

# 3. Starting

## 3a. Dev Mode

To run the flask development server (for dev work):

```bash
export FLASK_APP=cluster_dash_server
export FLASK_ENV=development
flask run
```

## 3b. Via Waitress

To run in production (using Waitress):

```bash
waitress-serve --host 127.0.0.1 --call cluster_dash_server:create_app
```

# 4. To Test

Can test by sending a POST request to the server, e.g.:

```bash
cd etc
curl -d "@example_data1.json" -H "Content-Type: application/json" -X POST http://0.0.0.0:5000
```
