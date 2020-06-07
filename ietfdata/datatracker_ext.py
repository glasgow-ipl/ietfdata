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

from datetime             import datetime, timedelta
from ietfdata.datatracker import *
from ietfdata.rfcindex    import *

# =================================================================================================================================

@dataclass
class DraftRFC:
    rfc        : RfcEntry
    draft      : Document
    rev        : str
    date       : datetime
    submission : Optional[Submission]


class DataTrackerExt(DataTracker):
    """
    The `DataTrackerExt` class extends the `DataTracker` with methods that
    perform complex queries across multiple API endpoints.
    """

    def _drafts(self, rfc: RfcEntry, draft: Document) -> List[DraftRFC]:
        """
        This is a private helper function used by the `drafts_for_rfc()` method.
        Not for public use.
        """
        drafts : List[DraftRFC] = []

        # Step 1: Use document_events() to find previous versions of the draft.
        for event in self.document_events(doc=draft, event_type="new_revision"):
            drafts.append(DraftRFC(rfc, draft, event.rev, event.time, None))

        # Step 2: Find the submissions, and add them to the previously found
        # draft versions. Some versions of a draft may not have a submission.
        # While we're doing this, record any drafts the submissions are marked
        # as replacing.
        submissions : List[Submission]  = []
        replaces    : List[Document]    = []

        for submission_uri in draft.submissions:
            submission = self.submission(submission_uri)
            if submission is not None:
                submissions.append(submission)
                if submission.replaces is not "":
                    for replaces_draft in submission.replaces.split(","):
                        replaces_doc = self.document_from_draft(replaces_draft)
                        if replaces_doc is not None:
                            found = False
                            for r in replaces:
                                if r.name == replaces_doc.name:
                                    found = True
                                    break
                            if not found:
                                replaces.append(replaces_doc)

        for submission in submissions:
            found = False
            for d in drafts:
                if d.draft.resource_uri == submission.draft and d.rev == submission.rev:
                    d.submission = submission
                    found = True
                    break
            if not found:
                drafts.append(DraftRFC(rfc, draft, submission.rev, submission.document_date, submission))

        # Step 3: Use related_documents() to find additional drafts this replaces:
        for related in reversed(list(self.related_documents(source=draft, relationship_type=self.relationship_type_from_slug("replaces")))):
            alias  = self.document_alias(related.target)
            if alias is not None:
                reldoc = self.document(alias.document)
                if reldoc is not None:
                    found = False
                    for r in replaces:
                        if r.name == reldoc.name:
                            found = True
                            break
                    if not found:
                        replaces.append(reldoc)

        # Step 4: Process the drafts this replaces, to find earlier versions:
        for r in replaces:
            if r.name != draft.name:
                drafts.extend(self._drafts(rfc, r))

        return drafts



    def drafts_for_rfc(self, rfc: RfcEntry) -> List[DraftRFC]:
        """
        Use the DataTracker to find the draft versions of a given RFC.

        The `RfcEntry` contains a `draft` field that (usually) points to the
        final draft before the document became an RFC. This function follows
        the history of the document back to the original submission to find
        all prior drafts.

        Note that earlier RFCs and "April Fools" RFCs do not exist in draft
        form, so this may return an empty list.
        """
        final_draft = None
        if rfc.draft is not None:
            final_draft = self.document_from_draft(rfc.draft[:-3])
            if final_draft is None:
                final_draft = self.document_from_rfc(rfc.doc_id)
        else:
            final_draft = self.document_from_rfc(rfc.doc_id)

        if final_draft is not None:
            return self._drafts(rfc, final_draft)
        else:
            return []


# =================================================================================================================================
# vim: set tw=0 ai:
