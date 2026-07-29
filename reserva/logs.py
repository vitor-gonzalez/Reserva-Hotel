import logging
import sys

logger = logging.getLogger("hotel")
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter(
    "%(asctime)s | %(levelname)s | %(message)s"
)

if not logger.handlers:

    arquivo = logging.FileHandler("Hotel.log", encoding="utf-8")
    arquivo.setFormatter(formatter)

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)

    logger.addHandler(arquivo)
    logger.addHandler(console)
