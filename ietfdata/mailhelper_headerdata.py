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

import email.header
import email.utils
import time

from ietfdata.mailarchive        import *

class HeaderDataMailHelper(MailArchiveHelper):
    metadata_fields = ["from_name", "from_addr", "timestamp"]

    def scan_message(self, msg: Message) -> Dict[str, Any]:
        from_name, from_addr = email.utils.parseaddr(msg["From"])
        try:
            from_name = str(email.header.make_header(email.header.decode_header(from_name)))
        except:
            pass
        msg_date = email.utils.parsedate(msg["Date"])
        if msg_date is not None:
            timestamp = datetime.fromtimestamp(time.mktime(msg_date))
        else:
            timestamp = datetime.now()
        return {"from_name": from_name, "from_addr": from_addr, "timestamp": timestamp}


    def filter(self,
               metadata   : Dict[str, Any],
               from_name  : Optional[str] = None,
               from_addr  : Optional[str] = None,
               timestamp  : Optional[str] = None,
               **kwargs) -> bool:
        return ((from_name is None or metadata["from_name"] == from_name) and
               (from_addr is None or metadata["from_addr"] == from_addr) and
               (timestamp is None or metadata["timestamp"] == timestamp))


    def serialise(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        return {"from_name"  : metadata["from_name"],
                "from_addr" : metadata["from_addr"],
                "timestamp" : metadata["timestamp"].isoformat()}


    def deserialise(self, metadata: Dict[str, str]) -> Dict[str, Any]:
        return {"from_name": metadata["from_name"], "from_addr": metadata["from_addr"], "timestamp": datetime.fromisoformat(metadata["timestamp"])}
