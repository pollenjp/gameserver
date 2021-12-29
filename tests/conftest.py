# Standard Library
from logging import getLogger
from logging.config import dictConfig
from pathlib import Path

# Third Party Library
import yaml

filepath = Path(__file__).parents[1] / "conf" / "logging.yml"
with open(file=str(filepath), mode="rt") as f:
    config_dict = yaml.safe_load(f)
dictConfig(config=config_dict)
del filepath, config_dict


logger = getLogger(__name__)
