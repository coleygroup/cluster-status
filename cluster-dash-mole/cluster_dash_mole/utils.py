import re
import datetime

BYTES_TO_GB_CONV = 1024. * 1024. * 1024.
BYES_TO_MB_CONV = 1024.**2


def replace_spaces_with_char(string, char_to_use="_"):
    """
    Replace all runs of whitespace with `char_to_use`
    """
    s = re.sub(r"\s+", char_to_use, string)
    return s


def convert_bytes_to_giga_bytes(bytes_):
    return float(bytes_) / BYTES_TO_GB_CONV


def convert_bytes_to_mega_bytes(bytes_):
    return float(bytes_) / BYES_TO_MB_CONV


