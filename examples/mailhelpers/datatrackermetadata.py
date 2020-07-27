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

import ietfdata.datatracker as dt

from ietfdata.mailarchive        import *
from ietfdata.mailarchive_helper import *

class DatatrackerMetadata(MailArchiveHelper):
    def __init__(self):
        self.dt = dt.DataTracker(cache_dir=Path("cache"))
        
    def scan_message(self, msg: MailingListMessage) -> None:
        from_name, from_addr = email.utils.parseaddr(msg.message["From"])
        from_person = self.dt.person_from_email(from_addr)
        docs = []
        # FIXME: Does this find messages with a document in the subject line?
        # FIXME: It would be interesting to also find people mentioned in messages
        draft_matches = re.findall(r'draft-(?P<name>[a-zA-Z0-9_\-]+)-(?P<revision>[0-9_\-]+)', msg.message.as_string())
        for draft_match in draft_matches:
            doc = self.dt.document_from_draft(f"draft-{draft_match[0]}")
            if doc is not None and doc not in docs:
                docs.append(doc)
        rfc_matches = re.findall(r'(rfc|RFC)(\s)?(?P<number>[0-9]+)', msg.message.as_string())
        for rfc_match in rfc_matches:
            doc = self.dt.document_from_rfc(f"rfc{rfc_match[-1]}")
            if doc is not None and doc not in docs:
                docs.append(doc)
        msg.add_metadata("from_person", from_person)
        msg.add_metadata("related_docs", docs)


    def filter(self,
               message : MailingListMessage,
               from_person : Optional[dt.Person] = None,
               related_doc : Optional[dt.Document] = None,
               **kwargs) -> bool:
        return (from_person is None or message.metadata("from_person") == from_person) and (related_doc is None or related_doc in message.metadata("related_docs"))


    def serialise(self, msg: MailingListMessage) -> Dict[str, str]:
        if not msg.has_metadata("from_person"):
            self.scan_message(msg)
        return {"from_person"  : msg.metadata("from_person").resource_uri.uri if msg.metadata("from_person") is not None else "",
                "related_docs" : [doc.resource_uri.uri for doc in msg.metadata("related_docs")]}


    def deserialise(self, msg: MailingListMessage, cache_data: Dict[str, str]) -> None:
        msg.add_metadata("from_person", self.dt.person(dt.PersonURI(cache_data["from_person"])) if cache_data["from_person"] != "" else None)
        msg.add_metadata("related_docs", [self.dt.document(dt.DocumentURI(doc_uri)) for doc_uri in cache_data["related_docs"]])