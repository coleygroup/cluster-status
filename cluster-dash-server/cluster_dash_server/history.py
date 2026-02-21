"""GPU snapshot history — SQLite persistence for tracking usage over time."""

import os
import sqlite3
import time

_db_path = None
_last_snapshot_times = {}

SNAPSHOT_MIN_INTERVAL_SECS = 300

_CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS gpu_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    hostname TEXT NOT NULL,
    total_gpus INTEGER NOT NULL,
    free_gpus INTEGER NOT NULL,
    avg_gpu_memory_percent REAL NOT NULL,
    avg_gpu_util REAL NOT NULL,
    cpu_percent REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_snapshots_timestamp ON gpu_snapshots(timestamp);
CREATE INDEX IF NOT EXISTS idx_snapshots_hostname ON gpu_snapshots(hostname);
"""

# bucket sizes tuned to keep chart point counts reasonable
_BUCKET_THRESHOLDS = [
    (24, 300),        # <= 24h: 5-min buckets
    (168, 900),       # <= 7d: 15-min buckets
    (720, 3600),      # <= 30d: 1-hour buckets
    (float("inf"), 14400),  # > 30d: 4-hour buckets
]


def _get_connection():
    conn = sqlite3.connect(_db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(app):
    """Create the history database and tables if they don't exist."""
    global _db_path
    os.makedirs(app.instance_path, exist_ok=True)
    _db_path = os.path.join(app.instance_path, "gpu_history.db")

    with _get_connection() as conn:
        conn.executescript(_CREATE_TABLES_SQL)


def record_snapshot(hostname, results):
    """Record a summary snapshot, throttled to one per host per interval."""
    now = time.time()

    last_time = _last_snapshot_times.get(hostname, 0)
    if now - last_time < SNAPSHOT_MIN_INTERVAL_SECS:
        return

    gpu_data = results.get("gpu", {})
    if not gpu_data:
        return

    total_gpus = len(gpu_data)
    memory_pcts = []
    util_pcts = []

    for gpu_info in gpu_data.values():
        total_mem = gpu_info.get("total_mem", 0)
        used_mem = gpu_info.get("used_mem", 0)
        mem_pct = (used_mem / total_mem) * 100 if total_mem > 0 else 0
        memory_pcts.append(mem_pct)
        util_pcts.append(gpu_info.get("gpu_util", 0))

    free_gpus = sum(
        1 for mem, util in zip(memory_pcts, util_pcts)
        if mem < 30 and util < 30
    )
    avg_mem = sum(memory_pcts) / len(memory_pcts)
    avg_util = sum(util_pcts) / len(util_pcts)
    cpu_percent = results.get("cpu", {}).get("cpu_percent", 0)

    with _get_connection() as conn:
        conn.execute(
            """INSERT INTO gpu_snapshots
               (timestamp, hostname, total_gpus, free_gpus,
                avg_gpu_memory_percent, avg_gpu_util, cpu_percent)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (now, hostname, total_gpus, free_gpus,
             round(avg_mem, 1), round(avg_util, 1), round(cpu_percent, 1)),
        )

    _last_snapshot_times[hostname] = now


def _bucket_size_for_hours(hours):
    for threshold, bucket in _BUCKET_THRESHOLDS:
        if hours <= threshold:
            return bucket
    return _BUCKET_THRESHOLDS[-1][1]


def query_cluster_history(hours=24):
    """Return time-bucketed series of cluster-wide GPU stats."""
    cutoff = time.time() - (hours * 3600)
    bucket_secs = _bucket_size_for_hours(hours)

    with _get_connection() as conn:
        rows = conn.execute(
            """SELECT
                 CAST(timestamp / ? AS INTEGER) * ? AS bucket_ts,
                 hostname,
                 AVG(total_gpus) AS total_gpus,
                 AVG(free_gpus) AS free_gpus,
                 AVG(avg_gpu_memory_percent) AS avg_gpu_memory_percent,
                 AVG(avg_gpu_util) AS avg_gpu_util
               FROM gpu_snapshots
               WHERE timestamp >= ?
               GROUP BY bucket_ts, hostname
               ORDER BY bucket_ts""",
            (bucket_secs, bucket_secs, cutoff),
        ).fetchall()

    # aggregate per-server rows into cluster-wide time points
    buckets = {}
    for row in rows:
        ts = row["bucket_ts"]
        if ts not in buckets:
            buckets[ts] = {
                "timestamp": ts,
                "total_gpus": 0,
                "free_gpus": 0,
                "avg_gpu_util": [],
                "avg_gpu_memory_percent": [],
                "servers": {},
            }
        b = buckets[ts]
        b["total_gpus"] += round(row["total_gpus"])
        b["free_gpus"] += round(row["free_gpus"])
        b["avg_gpu_util"].append(row["avg_gpu_util"])
        b["avg_gpu_memory_percent"].append(row["avg_gpu_memory_percent"])
        b["servers"][row["hostname"]] = {
            "free_gpus": round(row["free_gpus"]),
            "total_gpus": round(row["total_gpus"]),
            "avg_gpu_util": round(row["avg_gpu_util"], 1),
        }

    series = []
    for ts in sorted(buckets):
        b = buckets[ts]
        b["avg_gpu_util"] = round(
            sum(b["avg_gpu_util"]) / len(b["avg_gpu_util"]), 1
        )
        b["avg_gpu_memory_percent"] = round(
            sum(b["avg_gpu_memory_percent"]) / len(b["avg_gpu_memory_percent"]), 1
        )
        series.append(b)

    return series


def query_waste_stats(hours=24):
    """Return aggregate waste statistics for the given time window."""
    cutoff = time.time() - (hours * 3600)

    with _get_connection() as conn:
        # per-bucket cluster totals, then aggregate
        row = conn.execute(
            """SELECT
                 AVG(total_gpus) AS avg_total_gpus,
                 AVG(free_gpus) AS avg_free_gpus,
                 MAX(free_gpus) AS peak_free_gpus,
                 MIN(free_gpus) AS min_free_gpus,
                 AVG(avg_gpu_util) AS avg_cluster_util,
                 AVG(avg_gpu_memory_percent) AS avg_cluster_mem,
                 COUNT(*) AS total_snapshots
               FROM (
                 SELECT
                   CAST(timestamp / 300 AS INTEGER) AS bucket,
                   SUM(total_gpus) AS total_gpus,
                   SUM(free_gpus) AS free_gpus,
                   AVG(avg_gpu_util) AS avg_gpu_util,
                   AVG(avg_gpu_memory_percent) AS avg_gpu_memory_percent
                 FROM gpu_snapshots
                 WHERE timestamp >= ?
                 GROUP BY bucket
               )""",
            (cutoff,),
        ).fetchone()

    if row is None or row["total_snapshots"] == 0:
        return {
            "avg_total_gpus": 0,
            "avg_free_gpus": 0,
            "peak_free_gpus": 0,
            "min_free_gpus": 0,
            "avg_cluster_util": 0,
            "avg_cluster_mem": 0,
            "waste_percent": 0,
            "total_snapshots": 0,
        }

    avg_total = row["avg_total_gpus"] or 0
    avg_free = row["avg_free_gpus"] or 0
    waste_pct = (avg_free / avg_total * 100) if avg_total > 0 else 0

    return {
        "avg_total_gpus": round(avg_total),
        "avg_free_gpus": round(avg_free, 1),
        "peak_free_gpus": row["peak_free_gpus"] or 0,
        "min_free_gpus": row["min_free_gpus"] or 0,
        "avg_cluster_util": round(row["avg_cluster_util"] or 0, 1),
        "avg_cluster_mem": round(row["avg_cluster_mem"] or 0, 1),
        "waste_percent": round(waste_pct, 1),
        "total_snapshots": row["total_snapshots"],
    }
