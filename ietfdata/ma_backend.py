# Copyright (C) 2026 University of Glasgow
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from abc    import ABC, abstractmethod
from typing import List

class MailArchiveBackend(ABC):
    @abstractmethod
    def connect(self) -> None:
        """
        Connect to the mail server.
        """
        pass


    @abstractmethod
    def disconnect(self) -> None:
        """
        Disconnect from the mail server.
        """
        pass


    @abstractmethod
    def mailboxes(self) -> List[str]:
        """
        Return the list of mailboxes available on the server.
        """
        pass


    @abstractmethod
    def select_mailbox(self, mailbox: str) -> None:
        """
        Select a mailbox. 

        The selected mailbox is used by calls to the `validity()`,
        `message_ids()`, and `fetch()` methods.
        """
        pass


    @abstractmethod
    def validity(self) -> int:
        """
        Return the validity of the selected mailbox.

        The validity is an integer that denotes the validity of messages
        identifiers in this mailbox. If this value changes it indicates
        that the contents of the mailbox must be redownloaded from scratch.
        """
        pass


    @abstractmethod
    def messages_ids(self) -> List[int]:
        """
        Return the list of valid message identifiers for this mailbox.
        """
        pass


    @abstractmethod
    def fetch(self, message_ids: List[int]) -> Iterator[(int, str)]:
        """
        Return messages from the mailbox.

        The return values are tuples of the message identifier and its
        contents. The contents are the raw RFC 822-style message text.
        """
        pass

