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

import logging
import ietfdata.datatracker as dt

from ietfdata.mailarchive import *

class DatatrackerMailHelper(MailArchiveHelper):
    name    = "Datatracker"
    version = "r1"
    provided_fields = ["from_person", "related_docs"]

    def __init__(self, datatracker: dt.DataTracker):
        logging.basicConfig(level=os.environ.get("IETFDATA_LOGLEVEL", "INFO"))
        self.log = logging.getLogger("ietfdata")
        self.dt = datatracker


    def scan_message(self, msg: Message) -> Dict[str, Any]:
        from_name, from_addr = email.utils.parseaddr(str(msg["From"]).replace("\uFFFD", "?"))
        try:
            from_name = str(email.header.make_header(email.header.decode_header(from_name)))
        except:
            pass
        from_person = self.dt.person_from_email(from_addr)
        docs = []

        try:
            msg_str = msg.as_string()
        except:
            self.log.error(f"DatatrackerMailHelper: could not parse message as string")
            msg_str = ""

        # FIXME: Does this find messages with a document in the subject line?
        # FIXME: It would be interesting to also find people mentioned in messages
        draft_matches = re.findall(r'draft-(?P<name>[a-zA-Z0-9_\-]+)-(?P<revision>[0-9_\-]+)', msg_str)
        for draft_match in draft_matches:
            doc = self.dt.document_from_draft(f"draft-{draft_match[0]}")
            if doc is not None and doc not in docs:
                docs.append(doc)
        rfc_matches = re.findall(r'(rfc|RFC)(\s)?(?P<number>[0-9]+)', msg_str)
        for rfc_match in rfc_matches:
            doc = self.dt.document_from_rfc(f"rfc{rfc_match[-1]}")
            if doc is not None and doc not in docs:
                docs.append(doc)
        return {"from_person": from_person, "related_docs": docs}


    def filter(self,
               metadata    : Dict[str, Any],
               from_person : Optional[dt.Person] = None,
               related_doc : Optional[dt.Document] = None,
               **kwargs) -> bool:
        return (from_person is None or metadata["from_person"] == from_person) and (related_doc is None or related_doc in metadata["related_docs"])


    def serialise(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        return {"from_person"  : metadata["from_person"].resource_uri.uri if metadata["from_person"] is not None else "",
                "related_docs" : [str(doc.resource_uri.uri) for doc in metadata["related_docs"]]}


    def deserialise(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        from_person = self.dt.person(dt.PersonURI(metadata["from_person"])) if metadata["from_person"] != "" else None
        related_docs = [self.dt.document(dt.DocumentURI(doc_uri)) for doc_uri in metadata["related_docs"]]
        return {"from_person" : from_person, "related_docs" : related_docs}
