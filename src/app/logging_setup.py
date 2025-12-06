import logging
import sys


def setup_logging(level: str) -> None:
    """
    Configure root logger once with a simple stdout formatter.
    """
    root = logging.getLogger()
    if not root.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        )
        handler.setFormatter(formatter)
        root.addHandler(handler)
    root.setLevel(level.upper())
