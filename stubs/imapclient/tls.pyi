import imaplib
import socket
import ssl
from _typeshed import Incomplete

def create_default_context() -> ssl.SSLContext: ...
def wrap_socket(sock: socket.socket, ssl_context: ssl.SSLContext | None, host: str) -> socket.socket: ...

class IMAP4_TLS(imaplib.IMAP4):
    ssl_context: Incomplete
    def __init__(self, host: str, port: int = 993, ssl_context: ssl.SSLContext | None = None, timeout: float | None = None) -> None: ...
