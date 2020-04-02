import datetime
from decimal import Decimal
from enum import Enum
import inspect
import typing
from typing import (
    Any, Dict, Type, TypeVar, Union, Generic, List, Mapping, Optional, Tuple
)
import sys

import dataclasses

from pavlova.base import BasePavlova
from pavlova.parsers import PavlovaParser
import pavlova.parsers

T = TypeVar('T')  # pylint: disable=invalid-name


class PavlovaParsingError(Exception):
    """The exception that will be thrown if there is a ValueError or TypeError
    encountered when parsing a mapping."""
    def __init__(self,
                 message: str,
                 original_exception: Exception,
                 path: Tuple[str, ...],
                 expected_type: Type) -> None:
        ...


class Pavlova(BasePavlova):
    "The main Pavlova class that handles parsing dictionaries"

    parsers: Dict[Any, PavlovaParser] = {}

    def __init__(self) -> None:
        ...

    def register_parser(
            self,
            parser_type: Type[Any],
            parser: pavlova.parsers.PavlovaParser,
    ) -> None:
        ...

    def from_mapping(self,
                     input_mapping: Mapping[Any, Any],
                     model_class: Type[T],
                     path: Optional[Tuple[str, ...]] = None) -> T:
        ...

    def parse_field(self,
                    input_value: Any,
                    field_type: Type,
                    path: Tuple[str, ...]) -> Any:
        ...