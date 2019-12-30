import pathlib

from typing import List, Dict, Any, Tuple

from apptools.entity.navajo import Entity, Message
from apptools.entity.io import IndentedWriter
from apptools.entity.text import camelcase


def write(entities: List[Entity], options: Dict[str, Any]) -> None:
    print("Hello world")
