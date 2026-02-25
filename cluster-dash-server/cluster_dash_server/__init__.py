"""
GPU Cluster Dashboard - Flask Application

A monitoring dashboard for GPU servers with live status and usage history.
Receives data via POST from cluster-dash-mole agents, stores snapshots
in SQLite for historical tracking, and displays everything in a web UI.

Routes:
    POST /              - Data ingestion endpoint (from mole agents)
    GET  /              - Serve the live dashboard
    GET  /history       - GPU usage history / waste report
    GET  /api/dashboard-data   - JSON API for live dashboard data
    GET  /api/history-data     - JSON API for historical time-series
    GET  /api/gpu-summary      - CLI-friendly text summary (with ANSI colors)
    GET  /data-out/gpu-data-simple - Legacy API (kept for compatibility)
"""

import copy
from os import path as osp
import json
import time

import jsonschema
from flask import (
    Flask,
    render_template,
    current_app,
    jsonify,
    abort,
    request,
)
from werkzeug.exceptions import BadRequest

from . import history

_machine_post_schema = None


def get_machine_post_schema():
    """Load and cache the JSON schema for validating incoming data."""
    global _machine_post_schema
    if _machine_post_schema is None:
        pth = osp.join(osp.dirname(__file__), "machine-post-schema.json")
        with open(pth, "r") as fo:
            _machine_post_schema = json.load(fo)
    return _machine_post_schema


def create_app(test_config=None):
    """Create and configure an instance of the Flask application."""
    app = Flask(__name__)
    app.config.from_mapping(
        PASSCODE="pass",
    )

    # In-memory storage for server data
    # Key: hostname, Value: data dict with received_timestamp
    stored_results_ = {}

    if test_config is None:
        app.config.from_pyfile("config.py", silent=True)
        print(app.config)
    else:
        app.config.from_mapping(test_config)

    history.init_db(app)

    @app.errorhandler(400)
    def resource_not_found(e):
        return jsonify(dict(success=False, msg=str(e))), 400

    @app.route("/", methods=("GET", "POST"))
    def index():
        """
        Main endpoint:
        - POST: Receive data from mole agents
        - GET: Serve the dashboard HTML
        """
        if request.method == "POST":
            # Data ingestion from mole agents
            try:
                json_back = request.json
            except BadRequest as ex:
                print(f"Bad request: {ex}")
                abort(400, "no json posted")
            else:
                schema = get_machine_post_schema()
                try:
                    jsonschema.validate(json_back, schema)
                except jsonschema.ValidationError as ex:
                    print(f"Schema validation error: {ex}")
                    abort(400, "schema validation error")

            if json_back["auth_code"] != current_app.config["PASSCODE"]:
                abort(400, "invalid auth code")
            json_back.pop("auth_code")

            json_back["received_timestamp"] = time.time()
            stored_results_[json_back["hostname"]] = json_back

            try:
                history.record_snapshot(json_back["hostname"], json_back)
            except Exception as e:
                print(f"History recording error: {e}")

            return jsonify({"success": True, "msg": "stored result"})

        else:
            # Serve the single-page dashboard
            return render_template("dashboard.html")

    @app.route("/data-out/gpu-data-simple")
    def gpu_data_simple():
        """
        Legacy API endpoint for GPU data.
        Kept for backwards compatibility with existing integrations.
        """
        out = {}
        for name, results in sorted(stored_results_.items(), key=lambda x: x[0]):
            out[name] = copy.deepcopy(results.get("gpu", {}))
            for gpu_name, gpu_res in out[name].items():
                gpu_res["received_timestamp"] = (
                    time.time() - results["received_timestamp"]
                )
                gpu_res["time_received_mins"] = round(
                    gpu_res["received_timestamp"] / 60
                )
        return jsonify(out)

    @app.route("/api/gpu-summary")
    def gpu_summary():
        """
        CLI-friendly text summary with ANSI color codes.
        Useful for quick terminal checks: curl http://server:8080/api/gpu-summary
        """
        servers = []

        for name, results in sorted(stored_results_.items(), key=lambda x: x[0]):
            time_diff_mins = round((time.time() - results["received_timestamp"]) / 60)
            status = "online" if time_diff_mins <= 10 else "offline"

            gpu_data = results.get("gpu", {})
            total_gpus = len(gpu_data)

            gpu_memory_percentages = []
            for gpu_info in gpu_data.values():
                total_mem = gpu_info.get("total_mem", 0)
                used_mem = gpu_info.get("used_mem", 0)
                memory_percent = (used_mem / total_mem) * 100 if total_mem > 0 else 0
                gpu_memory_percentages.append(memory_percent)

            gpu_utils = [
                gpu_info.get("gpu_util", 0) for gpu_info in gpu_data.values()
            ]
            free_gpus = sum(
                1 for mem_pct, util_pct in zip(gpu_memory_percentages, gpu_utils)
                if mem_pct < 30 and util_pct < 30
            )
            avg_gpu_usage = (
                round(sum(gpu_memory_percentages) / len(gpu_memory_percentages))
                if gpu_memory_percentages
                else 0
            )
            cpu_usage = round(results.get("cpu", {}).get("cpu_percent", 0))

            servers.append({
                "name": name,
                "total_gpus": total_gpus,
                "free_gpus": free_gpus,
                "avg_gpu_usage": avg_gpu_usage,
                "cpu_usage": cpu_usage,
                "status": status,
            })

        # ANSI color codes for terminal output
        BOLD = "\033[1m"
        GREEN = "\033[92m"
        RED = "\033[91m"
        YELLOW = "\033[93m"
        RESET = "\033[0m"

        lines = [f"{BOLD}Server\t\tGPUs\tFree\tGPU%\tCPU%\tStatus{RESET}"]

        for server in servers:
            status_color = GREEN if server["status"] == "online" else RED
            gpu_color = (
                GREEN if server["avg_gpu_usage"] < 50
                else (YELLOW if server["avg_gpu_usage"] < 80 else RED)
            )
            cpu_color = (
                GREEN if server["cpu_usage"] < 50
                else (YELLOW if server["cpu_usage"] < 80 else RED)
            )

            lines.append(
                f"{server['name']}\t{server['total_gpus']}\t{server['free_gpus']}\t"
                f"{gpu_color}{server['avg_gpu_usage']}%{RESET}\t"
                f"{cpu_color}{server['cpu_usage']}%{RESET}\t"
                f"{status_color}{server['status']}{RESET}"
            )

        return "\n".join(lines), 200, {"Content-Type": "text/plain"}

    @app.route("/api/dashboard-data")
    def dashboard_data():
        """
        Main API endpoint for the single-page dashboard.

        Returns all server data in a structured format optimized for
        frontend rendering with summary cards and GPU detail panels.
        """
        current_time = time.time()
        servers = {}

        for hostname, results in sorted(stored_results_.items(), key=lambda x: x[0]):
            # Calculate time since last update
            time_diff = current_time - results.get("received_timestamp", current_time)
            last_seen_mins = round(time_diff / 60)

            # Server is "offline" if no update in 10+ minutes
            status = "online" if last_seen_mins <= 10 else "offline"

            # CPU data
            cpu_data = results.get("cpu", {})
            cpu_info = {
                "cpu_percent": round(cpu_data.get("cpu_percent", 0)),
                "num_cpus": cpu_data.get("num_cpus", 0)
            }

            # GPU data - transform from dict to sorted list
            gpu_dict = results.get("gpu", {})
            gpus = []
            memory_percentages = []
            gpu_error = None

            for gpu_key, gpu_info in gpu_dict.items():
                # Check if this entry is an error report
                if gpu_info.get("error") or gpu_info.get("name") == "error":
                    gpu_error = gpu_info.get("error", "Unknown GPU error")
                    continue

                total_mem = gpu_info.get("total_mem", 0)
                used_mem = gpu_info.get("used_mem", 0)
                memory_percent = round((used_mem / total_mem) * 100) if total_mem > 0 else 0
                memory_percentages.append(memory_percent)

                gpus.append({
                    "index": gpu_info.get("index", 0),
                    "name": gpu_info.get("name", "Unknown GPU"),
                    "total_mem_mb": round(total_mem),
                    "used_mem_mb": round(used_mem),
                    "memory_percent": memory_percent,
                    "gpu_util": gpu_info.get("gpu_util", 0),
                    "users": gpu_info.get("users", {})
                })

            # Sort GPUs by index
            gpus.sort(key=lambda x: x["index"])

            # Summary calculations
            total_gpus = len(gpus)
            free_gpus = sum(
                1 for gpu in gpus if gpu["memory_percent"] < 30 and gpu["gpu_util"] < 30
            )
            avg_memory_percent = (
                round(sum(memory_percentages) / len(memory_percentages))
                if memory_percentages else 0
            )
            gpu_utils = [gpu["gpu_util"] for gpu in gpus]
            avg_gpu_util = (
                round(sum(gpu_utils) / len(gpu_utils))
                if gpu_utils else 0
            )

            server_data = {
                "status": status,
                "last_seen_mins": last_seen_mins,
                "cpu": cpu_info,
                "gpus": gpus,
                "summary": {
                    "total_gpus": total_gpus,
                    "free_gpus": free_gpus,
                    "avg_gpu_memory_percent": avg_memory_percent,
                    "avg_gpu_util": avg_gpu_util
                }
            }
            if gpu_error:
                server_data["gpu_error"] = gpu_error

            servers[hostname] = server_data

        return jsonify({
            "timestamp": current_time,
            "servers": servers
        })

    @app.route("/history")
    def history_page():
        """Serve the GPU usage history page."""
        return render_template("history.html")

    @app.route("/api/history-data")
    def history_data():
        """JSON API for historical GPU usage time-series."""
        hours = request.args.get("hours", 24, type=int)

        series = history.query_cluster_history(hours=hours)
        stats = history.query_waste_stats(hours=hours)

        return jsonify({
            "hours": hours,
            "series": series,
            "stats": stats,
            "generated_at": time.time(),
        })

    return app
