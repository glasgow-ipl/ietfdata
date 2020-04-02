from abc import ABC, abstractmethod
import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, List, Dict, Union, Type, TypeVar, Generic, Tuple

from pavlova.base import BasePavlova


T = TypeVar('T')  # pylint: disable=invalid-name


class PavlovaParser(Generic[T], ABC):
    "The base pavlova parser for types"

    def __init__(self, pavlova_instance: BasePavlova) -> None:
        ...

    @abstractmethod
    def parse_input(self,
                    input_value: Any,
                    field_type: Type,
                    path: Tuple[str, ...]) -> T:
        "Given an input, return it's typed value"
        ...


class BoolParser(PavlovaParser[bool]):
    "Parses a Boolean"

    def parse_input(self,
                    input_value: Any,
                    field_type: Type,
                    path: Tuple[str, ...]) -> bool:
        ...


class ListParser(PavlovaParser[List[T]]):
    "Parses a List"

    def parse_input(self,
                    input_value: Any,
                    field_type: Type,
                    path: Tuple[str, ...]) -> List[T]:
        ...


class IntParser(PavlovaParser[int]):
    "Parses ints"

    def parse_input(self,
                    input_value: Any,
                    field_type: Type,
                    path: Tuple[str, ...]) -> int:
        ...


class FloatParser(PavlovaParser[float]):
    "Parses floats"

    def parse_input(self,
                    input_value: Any,
                    field_type: Type,
                    path: Tuple[str, ...]) -> float:
        ...


class DecimalParser(PavlovaParser[Decimal]):
    "Parses floats"

    def parse_input(self,
                    input_value: Any,
                    field_type: Type,
                    path: Tuple[str, ...]) -> Decimal:
        ...


class StringParser(PavlovaParser[str]):
    "Parses a String"

    def parse_input(self,
                    input_value: Any,
                    field_type: Type,
                    path: Tuple[str, ...]) -> str:
        ...


class DictParser(PavlovaParser[Dict]):
    "Parses a dictionary"

    def parse_input(self,
                    input_value: Any,
                    field_type: Type,
                    path: Tuple[str, ...]) -> Dict:
        ...


class DatetimeParser(PavlovaParser[datetime.datetime]):
    "Parses a datetime"

    def parse_input(self,
                    input_value: Any,
                    field_type: Type,
                    path: Tuple[str, ...]) -> datetime.datetime:
        ...


class UnionParser(PavlovaParser[Union[T]]):
    "Parses an Union"

    @staticmethod
    def _is_from_optional(field_type: Type) -> bool:
        ...

    def parse_input(self,
                    input_value: Any,
                    field_type: Type,
                    path: Tuple[str, ...]) -> T:
        ...


class EnumParser(PavlovaParser[Enum]):
    "Parses enums"

    def parse_input(self,
                    input_value: Any,
                    field_type: Type,
                    path: Tuple[str, ...]) -> Enum:
        ...


class GenericParser(PavlovaParser[T]):
    def __init__(self, pavlova: BasePavlova, parser_type: T) -> None:
        ...

    def parse_input(self,
                    input_value: Any,
                    field_type: Type,
                    path: Tuple[str, ...]) -> T:
        return self.parser_type(input_value)  # type: ignore