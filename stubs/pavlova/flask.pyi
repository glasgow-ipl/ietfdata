from functools import wraps
from typing import Any, Callable, Dict, Type, TypeVar

import flask

from pavlova import Pavlova


T = TypeVar('T')  # pylint: disable=invalid-name


class FlaskPavlova(Pavlova):
    "The flask adaptor for Pavlova"

    def use(self, model_class: Type[T]) -> Callable:
        """Wraps a flask endpoint, parses the data coming in via json or form
        data, then passes it to the function as an argument.
        """
        def _wrapper(func: Callable) -> Callable:
           ...

    def _from_flask_request(self, model_class: Type[T]) -> T:
        ...