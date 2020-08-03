# Copyright (C) 2020 University of Glasgow
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

import email.utils
import time

from ietfdata.mailarchive        import *

class SimpleMetadata(MailArchiveHelper):
    metadata_fields = ["from_name", "from_addr", "timestamp"]

    def scan_message(self, msg: "MailingListMessage") -> None:
        from_name, from_addr = email.utils.parseaddr(msg.message["From"])
        timestamp            = datetime.fromtimestamp(time.mktime(email.utils.parsedate(msg.message["Date"])))
        msg.add_metadata("from_name", from_name)
        msg.add_metadata("from_addr", from_addr)
        msg.add_metadata("timestamp", timestamp)


    def filter(self,
               message   : "MailingListMessage",
               from_name : Optional[str] = None,
               from_addr : Optional[str] = None,
               timestamp : Optional[str] = None,
               **kwargs) -> bool:
        return ((from_name is None or message.metadata("from_name") == from_name) and
               (from_addr is None or message.metadata("from_addr") == from_addr) and
               (timestamp is None or message.metadata("timestamp") == timestamp))


    def serialise(self, msg: "MailingListMessage") -> Dict[str, str]:
        if not msg.has_metadata("from_name"):
            self.scan_message(msg)
        return {"from_name"  : msg.metadata("from_name"),
                "from_addr" : msg.metadata("from_addr"),
                "timestamp" : msg.metadata("timestamp").isoformat()}


    def deserialise(self, msg: "MailingListMessage", cache_data: Dict[str, str]) -> None:
        msg.add_metadata("from_name", cache_data["from_name"])
        msg.add_metadata("from_addr", cache_data["from_addr"])
        msg.add_metadata("timestamp", datetime.fromisoformat(cache_data["timestamp"]))
        