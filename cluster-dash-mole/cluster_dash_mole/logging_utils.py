import logging

_mole_logger = None


def get_log():
    """
    Returns a Python logger object to use for logging system events.
    """
    global _mole_logger
    if _mole_logger is None:
        logger = logging.getLogger('cluster-dash-mole-log')
        logger.setLevel(logging.DEBUG)

        channel_stream = logging.StreamHandler()
        channel_stream.setLevel(logging.DEBUG)

        # create formatters
        formatter_stream = logging.Formatter('ClusterDashMole: %(asctime)s - %(levelname)s - %(message)s')

        # add formatter to ch
        channel_stream.setFormatter(formatter_stream)

        # add ch to logger
        logger.addHandler(channel_stream)
        _mole_logger = logger

    return _mole_logger
