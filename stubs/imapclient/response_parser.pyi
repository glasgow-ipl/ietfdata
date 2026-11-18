from .response_types import SearchIds
from .typing_imapclient import _Atom

__all__ = ['parse_response', 'parse_message_list']

def parse_response(data: list[bytes]) -> tuple[_Atom, ...]: ...
def parse_message_list(data: list[bytes | str]) -> SearchIds: ...
