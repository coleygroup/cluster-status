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


if __name__ == "__main__":
    main()
