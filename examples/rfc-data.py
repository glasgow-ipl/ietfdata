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

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pathlib              import Path
from ietfdata.datatracker import *
from ietfdata.rfcindex    import *

# =============================================================================

def print_submission(draft):
    for submission_uri in draft.submissions:
        submission = dt.submission(submission_uri)
        if submission.replaces is not "":
            replaces = dt.document_from_draft(submission.replaces)
            if replaces.name == draft.name:
                # draft-ietf-mpls-tp-temporal-hitless-psm replaces itself...
                return
            if replaces is not None:
                print_submission(replaces)
        print("   dt.submission   | {} | {} | {} | {}".format(rfc.doc_id, submission.name, submission.rev, submission.document_date))


dt = DataTracker(cache_dir=Path("cache"))
ri = RFCIndex()

for rfc in ri.rfcs():
    print(rfc.doc_id)
    print("  rfc.title        | {} | {}".format(rfc.doc_id, rfc.title))
    print("  rfc.draft        | {} | {}".format(rfc.doc_id, rfc.draft))
    for kw in rfc.keywords:
        print("  rfc.keyword      | {} | {}".format(rfc.doc_id, kw))
    print("  rfc.date         | {} | {} {}".format(rfc.doc_id, rfc.month, rfc.year))
    print("  rfc.stream       | {} | {}".format(rfc.doc_id, rfc.stream))
    print("  rfc.wg           | {} | {}".format(rfc.doc_id, rfc.wg))
    print("  rfc.area         | {} | {}".format(rfc.doc_id, rfc.area))
    print("  rfc.publ_status  | {} | {}".format(rfc.doc_id, rfc.publ_status))
    print("  rfc.curr_status  | {} | {}".format(rfc.doc_id, rfc.curr_status))
    print("  rfc.april_fool   | {} | {}".format(rfc.doc_id, rfc.day is not None))
    print("  rfc.page_count   | {} | {}".format(rfc.doc_id, rfc.page_count))
    for doc in rfc.updates:
        print("  rfc.updates      | {} | {}".format(rfc.doc_id, doc))
    for doc in rfc.updated_by:
        print("  rfc.updated-by   | {} | {}".format(rfc.doc_id, doc))
    for doc in rfc.obsoletes:
        print("  rfc.obsoletes    | {} | {}".format(rfc.doc_id, doc))
    for doc in rfc.obsoleted_by:
        print("  rfc.obsoleted-by | {} | {}".format(rfc.doc_id, doc))
    for a in rfc.authors:
        print("  rfc.author       | {} | {} ".format(rfc.doc_id, a))
    if rfc.draft is not None:
        draft = dt.document_from_draft(rfc.draft[:-3])
        if draft is not None:
            print("   dt.date         | {} | {}".format(rfc.doc_id, draft.time))
            for author in dt.document_authors(draft):
                person = dt.person(author.person)
                print("   dt.author       | {} | {:6d} | {} | {} | {}".format(rfc.doc_id, person.id, person.name, author.country, author.affiliation))
            print("   dt.revision     | {} | {}".format(rfc.doc_id, draft.rev))
            print_submission(draft)




# =============================================================================
