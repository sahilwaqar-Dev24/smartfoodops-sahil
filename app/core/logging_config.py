import logging


def setup_logging() -> None:
    """Poore project ke liye ek jaisi logging setup (print() ki jagah)."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )