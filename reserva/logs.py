import logging

logger = logging.getLogger('hotel')

logger.setLevel(logging.DEBUG)

formatter = logging.Formatter(
    "%(asctime)s | %(levelname)s | %(message)s"
)

arquivo = logging.FileHandler("Hotel.log", encoding="utf-8")
arquivo.setFormatter(formatter)

logger.addHandler(arquivo)