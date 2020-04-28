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

import sys
import os
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ietfdata.datatracker import *

dt = DataTracker(cache_dir=Path("cache"))
replaces = dt.relationship_type(RelationshipTypeURI("/api/v1/name/docrelationshipname/replaces/"))

docname = "rfc8280"

def print_revisions(document):
    revisions = list(dt.document_events(doc=document, event_type="new_revision"))[::-1]
    for revision in revisions:
        print("    {0: <50} | {1} | {2}".format(document.name, revision.rev, revision.time.strftime("%Y-%m-%d")))

def replacements(doc, docs_seen):
    replaced_docs = list(dt.related_documents(source=doc, relationship_type=replaces))
    replaced_docs = [dt.document_alias(replaced_doc.target) for replaced_doc in replaced_docs]
    for replaced_doc in replaced_docs:
        if replaced_doc not in docs_seen:
            replacements(dt.document(replaced_doc.document), docs_seen)
            docs_seen.append(replaced_doc)
    return replaced_docs

def get_replacement_chain(doc):
    docs_seen = []
    replacements(doc, docs_seen)
    return docs_seen

docs = list(dt.document_aliases(name=docname))
if len(docs) == 1:
    doc = dt.document(docs[0].document)
    replacement_aliases = get_replacement_chain(doc)
    for replacement_alias in replacement_aliases:
        replacement_doc = dt.document(replacement_alias.document)
        print(replacement_doc.name)
        print_revisions(replacement_doc)
    print(doc.name)
    print_revisions(doc)
    if docname[:3] == "rfc":
        published_rfc_event = list(dt.document_events(doc=doc, event_type="published_rfc"))[0]
        print("{0: <54} | -- | {1}".format(docname, published_rfc_event.time.strftime("%Y-%m-%d")))
