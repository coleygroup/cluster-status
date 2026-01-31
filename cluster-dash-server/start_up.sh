#!/usr/bin/env bash
source activate cluster-dash-server
export PYTHONPATH=${PYTHONPATH}:$(pwd)
waitress-serve --host 0.0.0.0 --call cluster_dash_server:create_app