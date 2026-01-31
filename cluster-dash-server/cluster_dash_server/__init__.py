import collections
import copy
import os
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
import pandas as pd
import plotly
import plotly.io as pio
import plotly.express as px
import plotly.graph_objects as go
import base64
import numpy as np

_machine_post_schema = None


def get_machine_post_schema():
    global _machine_post_schema
    if _machine_post_schema is None:
        pth = osp.join(osp.dirname(__file__), "machine-post-schema.json")
        with open(pth, "r") as fo:
            _machine_post_schema = json.load(fo)
    return _machine_post_schema


def fix_plotly_binary_data(graph_json_str):
    """Convert binary encoded data back to regular arrays in Plotly JSON"""
    graph_dict = json.loads(graph_json_str)

    for trace in graph_dict.get("data", []):
        # Fix y-axis data
        if "y" in trace and isinstance(trace["y"], dict) and "bdata" in trace["y"]:
            binary_data = base64.b64decode(trace["y"]["bdata"])
            dtype = trace["y"].get("dtype", "f8")  # default to float64

            if dtype == "f8":  # float64
                y_values = np.frombuffer(binary_data, dtype=np.float64).tolist()
            elif dtype == "f4":  # float32
                y_values = np.frombuffer(binary_data, dtype=np.float32).tolist()
            else:
                # Handle other dtypes as needed
                y_values = np.frombuffer(binary_data, dtype=dtype).tolist()

            trace["y"] = y_values

        # Fix x-axis data if needed (though usually it's strings)
        if "x" in trace and isinstance(trace["x"], dict) and "bdata" in trace["x"]:
            binary_data = base64.b64decode(trace["x"]["bdata"])
            dtype = trace["x"].get("dtype", "f8")
            x_values = np.frombuffer(binary_data, dtype=dtype).tolist()
            trace["x"] = x_values

        # Fix text data if needed
        if (
            "text" in trace
            and isinstance(trace["text"], dict)
            and "bdata" in trace["text"]
        ):
            binary_data = base64.b64decode(trace["text"]["bdata"])
            dtype = trace["text"].get("dtype", "f8")
            text_values = np.frombuffer(binary_data, dtype=dtype).tolist()
            trace["text"] = text_values

    return json.dumps(graph_dict)


def create_app(test_config=None):
    """Create and configure an instance of the Flask application."""
    app = Flask(__name__)
    app.config.from_mapping(
        PASSCODE="pass",
    )
    stored_results_ = {}

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile("config.py", silent=True)
        print(app.config)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    @app.errorhandler(400)
    def resource_not_found(e):
        return jsonify(dict(success=False, msg=str(e))), 400

    @app.route("/", methods=("GET", "POST"))
    def index():
        if request.method == "POST":

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
            return jsonify({"success": True, "msg": "stored result"})

        else:
            status_list = []
            for name, results in sorted(stored_results_.items(), key=lambda x: x[0]):
                time_diff = time.time() - results["received_timestamp"]
                time_diff_mins = round(time_diff / 60)
                if time_diff_mins > 10:
                    status_color = "#ff9999"
                else:
                    status_color = "#b3e6b3"
                status_list.append(
                    dict(
                        name=name,
                        time_diff_mins=time_diff_mins,
                        status_color=status_color,
                    )
                )
            return render_template("index.html", status_list=status_list)

    @app.route("/demo-plot")
    def demo_plot():
        return render_template(
            "simple_chart.html", name="demo", render_src="scripts/renderDemoData.js"
        )

    @app.route("/gpu-data")
    def gpu_mem_plot():
        name = "GPU Memory"
        if len(stored_results_) == 0:
            return render_template("no-data.html", name=name)

        return render_template(
            "simple_chart.html", name=name, render_src="scripts/renderGpuData.js"
        )

    @app.route("/cpu-data")
    def cpu_plot():
        """
        CPU utilization as a percentage -- demonstrating how one can do all of the plotting in Python.
        """
        out = collections.defaultdict(list)
        for name, results in sorted(stored_results_.items(), key=lambda x: x[0]):
            out["names"].append(name)
            # Ensure numeric type so Plotly treats y as continuous, not categorical
            try:
                cpu_val = float(results["cpu"]["cpu_percent"])
            except (TypeError, ValueError, KeyError):
                cpu_val = 0.0
            out["cpu_percent"].append(cpu_val)
        if len(out) == 0:
            return render_template("no-data.html", name="CPU Util")
        df = pd.DataFrame(out)

        fig = px.bar(df, x="names", y="cpu_percent", range_y=[0, 100])
        graph_json = fix_plotly_binary_data(fig.to_json())
        return render_template(
            "plotly_express.html", name="CPU Util", graph_json=graph_json
        )

    @app.route("/root_drive")
    def root_storage():
        """
        Percentage of storage of the root drive used.
        """
        title = "Percent of '/' drive used."
        out = collections.defaultdict(list)
        for name, results in sorted(stored_results_.items(), key=lambda x: x[0]):

            for drive, drive_details in results["disk"].items():
                if drive_details["mount_point"] == "/":
                    out["names"].append(name)
                    out["percent_used"].append(drive_details["percent_used"])
        if len(out) == 0:
            return render_template("no-data.html", name=title)
        df = pd.DataFrame(out)
        fig = px.bar(df, x="names", y="percent_used")

        graph_json = fix_plotly_binary_data(fig.to_json())
        return render_template("plotly_express.html", name=title, graph_json=graph_json)

    @app.route("/memory")
    def memory_plot():
        """
        Available and used mnemory in GB
        """
        title = "Available and Used Memory (GB)"
        out = collections.defaultdict(list)
        for name, results in sorted(stored_results_.items(), key=lambda x: x[0]):
            out["names"].append(name)
            out["names"].append(name)
            out["memory"].append(results["memory"]["used_gb"])
            out["memory"].append(results["memory"]["available_gb"])
            out["memory_type"].append("used")
            out["memory_type"].append("available")

        if len(out) == 0:
            return render_template("no-data.html", name=title)
        df = pd.DataFrame(out)

        fig = px.bar(
            df,
            x="names",
            y="memory",
            color="memory_type",
            text_auto=True,
            color_discrete_map={"used": "#003d66", "available": "#ccebff"},
        )
        graph_json = fix_plotly_binary_data(fig.to_json())
        return render_template("plotly_express.html", name=title, graph_json=graph_json)

    @app.route("/load-data-1")
    def loadavg1_plot():
        """
        Load plot.
        """
        out = collections.defaultdict(list)
        for name, results in sorted(stored_results_.items(), key=lambda x: x[0]):
            out["names"].append(name)
            out["load"].append(results["cpu"]["load_avgs"][0])
            out["total_num_processors"].append(results["cpu"]["num_cpus"])
            out["load_diff"].append(
                results["cpu"]["num_cpus"] - results["cpu"]["load_avgs"][0]
            )
        if len(out) == 0:
            return render_template("no-data.html", name="Load Avg (1 minute)")
        df = pd.DataFrame(out)

        fig = px.bar(
            df,
            x="names",
            y="load",
            color="load_diff",
            labels={
                "load_diff": "Difference between number\n of processors and load\n average (higher better)"
            },
            hover_data=["total_num_processors"],
            color_continuous_scale="rdylgn",
        )

        graph_json = fix_plotly_binary_data(fig.to_json())
        desc = """The plot below shows the 1 minute load average (bar height) and the difference between the number of
            processors and the load average (bar color).
             Typically you want the 1 minute load average to be less than the number of processors.
             If it is higher, it means that the system is overloaded.
             If it is much higher, it means that the system is under heavy load.
             If it is much lower, it means that the system is underutilized.
         """
        return render_template(
            "plotly_express.html",
            name="Load Avg (1 minute)",
            graph_json=graph_json,
            desc_=desc,
        )

    @app.route("/data-out/gpu-data-simple")
    def gpu_data_simple():
        out = {}

        for name, results in sorted(stored_results_.items(), key=lambda x: x[0]):
            # Deep copy to avoid mutating stored state
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
        servers = []

        for name, results in sorted(stored_results_.items(), key=lambda x: x[0]):
            # Check if server is online
            time_diff_mins = round((time.time() - results["received_timestamp"]) / 60)
            status = "online" if time_diff_mins <= 10 else "offline"

            # Analyze GPU data - using same approach as gpu_mem_plot()
            gpu_data = results.get("gpu", {})
            total_gpus = len(gpu_data)

            # Calculate GPU memory usage using total_mem and used_mem (same as renderGpuData.js)
            gpu_memory_percentages = []
            for gpu_info in gpu_data.values():
                total_mem = gpu_info.get("total_mem", 0)
                used_mem = gpu_info.get("used_mem", 0)

                if total_mem > 0:
                    memory_percent = (used_mem / total_mem) * 100
                else:
                    memory_percent = 0

                gpu_memory_percentages.append(memory_percent)

            free_gpus = sum(1 for percent in gpu_memory_percentages if percent < 30)
            avg_gpu_usage = (
                round(sum(gpu_memory_percentages) / len(gpu_memory_percentages))
                if gpu_memory_percentages
                else 0
            )
            cpu_usage = round(results.get("cpu", {}).get("cpu_percent", 0))

            servers.append(
                {
                    "name": name,
                    "total_gpus": total_gpus,
                    "free_gpus": free_gpus,
                    "avg_gpu_usage": avg_gpu_usage,
                    "cpu_usage": cpu_usage,
                    "status": status,
                }
            )

        # ANSI color codes
        BOLD = "\033[1m"
        GREEN = "\033[92m"
        RED = "\033[91m"
        YELLOW = "\033[93m"
        RESET = "\033[0m"

        # Format as colored text table
        lines = [f"{BOLD}Server\t\tGPUs\tFree\tGPU%\tCPU%\tStatus{RESET}"]

        for server in servers:
            # Color coding based on status and usage
            status_color = GREEN if server["status"] == "online" else RED
            gpu_color = (
                GREEN
                if server["avg_gpu_usage"] < 50
                else (YELLOW if server["avg_gpu_usage"] < 80 else RED)
            )
            cpu_color = (
                GREEN
                if server["cpu_usage"] < 50
                else (YELLOW if server["cpu_usage"] < 80 else RED)
            )

            lines.append(
                f"{server['name']}\t{server['total_gpus']}\t{server['free_gpus']}\t"
                f"{gpu_color}{server['avg_gpu_usage']}%{RESET}\t"
                f"{cpu_color}{server['cpu_usage']}%{RESET}\t"
                f"{status_color}{server['status']}{RESET}"
            )

        return "\n".join(lines), 200, {"Content-Type": "text/plain"}

    return app
