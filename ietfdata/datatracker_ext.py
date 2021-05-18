# Copyright (C) 2020-2021 University of Glasgow
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
# Private helper functions

def names_to_try(name: str, email: str) -> List[str]:
    names = []

    # Derive alternative names to try:
    if name != "":
        names.append(name)
        split = name.split()

        # If given, e.g., "Colin S. Perkins" also try "Colin Perkins":
        if len(split) == 3 and len(split[1]) == 2 and split[1][0].isalpha() and split[1][1] == ".":
            alias = split[0] + " " + split[2]
            names.append(alias)

        # If given, e.g., "Perkins, Colin" also try "Colin Perkins::
        if len(split) == 2 and len(split[0]) >= 2 and split[0][-1] == ",":
            alias = split[1] + " " + split[0][:-1]
            names.append(alias)

        # If given, e.g. "Colin Perkins (csperkins)" also try "Colin Perkins":
        if len(split) == 3 and len(split[2]) >= 2 and split[2][0] == "(" and split[2][-1] == ")":
            alias = split[0] + " " + split[1]
            names.append(alias)

    # Derive names from the email address:
    if "@" in email:
        local, remote = email.split("@")

        if local.endswith(".ietf") or local.endswith("-ietf") or local.endswith("+ietf"):
            local = local[:-5]
        split = local.split(".")

        # If given, e.g., "colin.perkins@glasgow.ac.uk" also try "Colin Perkins":
        if len(split) == 2 and len(split[0]) > 1 and len(split[1]) > 1:
            alias = split[0][0].upper() + split[0][1:] + " " + split[1][0].upper() + split[1][1:]
            names.append(alias)

        # If given, e.g., "mary.h.barnes@gmail.com" also try "Mary H. Barnes" and "Mary Barnes":
        if len(split) == 3 and len(split[0]) > 1 and len(split[1]) == 1 and len(split[2]) > 1:
            alias = split[0][0].upper() + split[0][1:] + " " + split[1].upper() + ". " + split[2][0].upper() + split[2][1:]
            names.append(alias)
            alias = split[0][0].upper() + split[0][1:] + " " + split[2][0].upper() + split[2][1:]
            names.append(alias)

    return names

# =================================================================================================================================

@dataclass
class DraftHistory:
    draft      : Document
    rev        : str
    date       : datetime
    submission : Optional[Submission]


class DataTrackerExt(DataTracker):
    """
    The `DataTrackerExt` class extends the `DataTracker` with methods that
    perform complex queries across multiple API endpoints.
    """

    def __init__(self,
            use_cache: bool = False,
            mongodb_hostname: str = "localhost",
            mongodb_port: int = 27017,
            mongodb_username: Optional[str] = None,
            mongodb_password: Optional[str] = None):
        super().__init__(use_cache, mongodb_hostname, mongodb_port, mongodb_username, mongodb_password)



    def draft_history(self, draft: Document, drafts_seen: List[Document] = []) -> List[DraftHistory]:
        """
        Find the previous versions of an Internet-Draft
        """
        assert draft.type == DocumentTypeURI("/api/v1/name/doctypename/draft/")

        drafts : List[DraftHistory] = []

        if draft in drafts_seen:
            return []
        else:
            drafts_seen.append(draft)

        # Step 1: Use document_events() to find previous versions of the draft.
        for event in self.document_events(doc=draft, event_type="new_revision"):
            drafts.append(DraftHistory(draft, event.rev, event.time, None))

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
                if submission.replaces != "":
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
                drafts.append(DraftHistory(draft, submission.rev, submission.submission_date, submission))

        # Step 3: Use related_documents() to find additional drafts this replaces:
        for related in self.related_documents(source=draft, relationship_type=self.relationship_type_from_slug("replaces")):
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
                drafts.extend(self.draft_history(r, drafts_seen=drafts_seen))

        return list(reversed(sorted(drafts, key=lambda d: d.date)))



    def draft_history_for_rfc(self, rfc: RfcEntry) -> List[DraftHistory]:
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
            return self.draft_history(final_draft)
        else:
            return []


    def iab_chair(self) -> Person:
        chairs = list(self.group_roles(group = self.group_from_acronym("iab"), name = self.role_name_from_slug("chair")))
        assert(len(chairs) == 1)   # There is only one IAB chair
        chair = self.person(chairs[0].person)
        assert chair is not None
        return chair


    def iab_members(self) -> Iterator[Person]:
        for member in self.group_roles(group = self.group_from_acronym("iab"), name = self.role_name_from_slug("member")):
            person = self.person(member.person)
            assert person is not None
            yield  person


    def ietf_chair(self) -> Person:
        chairs = list(self.group_roles(group = self.group_from_acronym("ietf"), name = self.role_name_from_slug("chair")))
        assert(len(chairs) == 1)   # There is only one IETF chair
        chair = self.person(chairs[0].person)
        assert chair is not None
        return chair


    def iesg_members(self) -> Iterator[Person]:
        for member in self.group_roles(group = self.group_from_acronym("iesg"), name = self.role_name_from_slug("ad")):
            person = self.person(member.person)
            assert person is not None
            yield  person


    def irtf_chair(self) -> Person:
        chairs = list(self.group_roles(group = self.group_from_acronym("irtf"), name = self.role_name_from_slug("chair")))
        assert(len(chairs) == 1)   # There is only one IRTF chair
        chair = self.person(chairs[0].person)
        assert chair is not None
        return chair


    def irsg_members(self) -> Iterator[Person]:
        for member in self.group_roles(group = self.group_from_acronym("irsg")):
            person = self.person(member.person)
            assert person is not None
            yield  person


    def active_research_groups(self) -> Iterator[Group]:
        active_state   = self.group_state_from_slug("active")
        research_group = self.group_type_name_from_slug("rg")

        for group in self.groups(parent = self.group_from_acronym("irtf")):
            t = self.group_type_name(group.type)
            s = self.group_state(group.state)
            if s == active_state and t == research_group:
                yield group


    def research_group_chairs(self) -> Iterator[Person]:
        chair  = self.role_name_from_slug("chair")
        chairs = set()
        for group in self.active_research_groups():
            for role in self.group_roles(group = group, name = chair):
                person = self.person(role.person)
                assert person is not None
                if person.id not in chairs:   # people can chair more than one group
                    chairs.add(person.id)
                    yield person


    def concluded_research_groups(self) -> Iterator[Group]:
        concluded_state = self.group_state_from_slug("conclude")
        research_group  = self.group_type_name_from_slug("wg")

        for group in self.groups(parent = self.group_from_acronym("irtf")):
            t = self.group_type_name(group.type)
            s = self.group_state(group.state)
            if s == concluded_state and t == research_group:
                yield group


    def active_working_groups(self) -> Iterator[Group]:
        active_state  = self.group_state_from_slug("active")
        working_group = self.group_type_name_from_slug("wg")

        for area in self.groups(parent = self.group_from_acronym("iesg")):
            if self.group_state(area.state) == active_state:
                for group in self.groups(parent = area):
                    t = self.group_type_name(group.type)
                    s = self.group_state(group.state)
                    if s == active_state and t == working_group:
                        yield group


    def working_group_chairs(self) -> Iterator[Person]:
        chair  = self.role_name_from_slug("chair")
        chairs = set()
        for group in self.active_working_groups():
            for role in self.group_roles(group = group, name = chair):
                person = self.person(role.person)
                assert person is not None
                if person.id not in chairs:   # people can chair more than one group
                    chairs.add(person.id)
                    yield person


    def next_ietf_meeting(self) -> Optional[Meeting]:
        """
        Return the next upcoming, or currently ongoing, IETF meeting.
        """
        next_meeting = None
        for meeting in self.meetings(meeting_type = self.meeting_type_from_slug("ietf")):
            if meeting.status() == MeetingStatus.ONGOING:
                next_meeting = meeting
                break
            elif meeting.status() == MeetingStatus.FUTURE:
                if next_meeting is None or meeting.date < next_meeting.date:
                    next_meeting = meeting
            elif meeting.status() == MeetingStatus.COMPLETED:
                pass
        return next_meeting


    def person_from_name_email(self, name: str, email_addr: str) -> Optional[Person]:
        """
        Given a name and an email address, for example as might be extracted from an
        email "From:" header, try to find a person in the datatracker. This uses a
        number of heuristics if there is no exact match.
        """
        # Try to match on the email address:
        email = self.email_for_address(email_addr)
        if email is not None and email.person is not None:
            self.log.debug(f"person_from_name_email: {name} <{email_addr}> -> {email.person} (email match)")
            return self.person(email.person)

        # Try to match on the base email address:
        if "@" in email_addr:
            local, remote = email_addr.split("@")
            if local.count("+") == 1:
                base, suffix = local.split("+")
                email_base = F"{base}@{remote}"
                email = self.email_for_address(email_base)
                if email is not None and email.person is not None:
                    self.log.debug(f"person_from_name_email: {name} <{email_addr}> -> {email.person} (email match as {email_base})")
                    return self.person(email.person)

        # Try to match on the name:
        for suffix in [" via Datatracker", " via RT"]:
            if name.endswith(suffix):
                name = name[:-len(suffix)]

        for n in names_to_try(name, email_addr):
            people = list(self.people(name = n))
            if len(people) == 1:
                self.log.debug(f"person_from_name_email: {name} <{email_addr}> -> {people[0].resource_uri} (name match)")
                return people[0]

            people = list(self.people(name_ascii = n))
            if len(people) == 1:
                self.log.debug(f"person_from_name_email: {name} <{email_addr}> -> {people[0].resource_uri} (name_ascii match)")
                return people[0]

            people = list(self.people(name_plain = n))
            if len(people) == 1:
                self.log.debug(f"person_from_name_email: {name} <{email_addr}> -> {people[0].resource_uri} (name_plain match)")
                return people[0]

            aliases = list(self.person_aliases(name = n))
            if len(aliases) == 1:
                self.log.debug(f"person_from_name_email: {name} <{email_addr}> -> {aliases[0].person} (alias match)")
                return self.person(aliases[0].person)

        self.log.debug(f"person_from_name_email: {name} <{email_addr}> failed to match")
        return None


# =================================================================================================================================
# vim: set tw=0 ai:
