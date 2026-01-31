
from os import path as osp

import toml

_config = None


def get_config_parser():
    global _config
    if _config is None:
        with open(osp.join(osp.dirname(__file__), "../config.toml")) as fo:
            _config = toml.load(fo)
    return _config
