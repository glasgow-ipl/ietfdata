# Copyright (C) 2017-2025 University of Glasgow
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

import ast
import urllib.parse

from datetime          import date, datetime, timedelta, timezone
from enum              import Enum
from inspect           import signature
from typing            import List, Optional, Tuple, Dict, Iterator, Type, TypeVar, Any, Union, Generic, get_origin
from typing_extensions import Self
from dataclasses       import dataclass, field
from pydantic          import BaseModel, ValidationError, model_validator

# =================================================================================================================================
# Classes to represent the JSON-serialised objects returned by the Datatracker API:

# ---------------------------------------------------------------------------------------------------------------------------------
# URI types:

class URI(BaseModel):
    uri    : Optional[str]
    root   : str = ""
    params : Dict[str, Any] = field(default_factory=dict)
    # params_alt is used by DTBackendArchive only
    params_alt : Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        if len(self.params) > 0:
            return F"{self.uri}?{urllib.parse.urlencode(self.params)}"
        else:
            return str(self.uri)

    # https://stackoverflow.com/a/77647989
    @model_validator(mode="before")
    @classmethod
    def from_literal(cls, data: Any) -> Any:
        if isinstance(data, str):
            return {"uri" : data}
        else:
            return data


class DocumentURI(URI):
    root : str = "/api/v1/doc/document/"


class GroupURI(URI):
    root : str = "/api/v1/group/group/"


# ---------------------------------------------------------------------------------------------------------------------------------
# Resource type

class Resource(BaseModel):
    resource_uri : URI

T = TypeVar('T', bound=Resource)
R = TypeVar('R', bound=Type[Resource])


# ---------------------------------------------------------------------------------------------------------------------------------
# Types relating to people:

class PersonURI(URI):
    root : str = "/api/v1/person/person/"


class HistoricalPersonURI(URI):
    root : str = "/api/v1/person/historicalperson/"


class Person(Resource):
    resource_uri    : PersonURI
    id              : int
    name            : str            # Full name in Unicode
    name_from_draft : Optional[str]
    ascii           : str            # Name as rendered in ASCII
    # ascii_short: Fill in this with initials and surname only if taking the initials
    # and surname of the ASCII name above produces an incorrect initials-only form.
    ascii_short     : Optional[str]
    user            : Optional[str]
    time            : datetime
    photo           : Optional[str]
    photo_thumb     : Optional[str]
    biography       : str
    # Plain name correction: Use this if you have a Spanish double surname.
    # Don't use this for nicknames, and don't use it unless you've actually
    # observed that the datatracker shows your name incorrectly."
    plain           : str
    pronouns_freetext     : Optional[str]
    pronouns_selectable   : str


class HistoricalPerson(Resource):
    resource_uri          : HistoricalPersonURI
    id                    : int
    name                  : str
    name_from_draft       : Optional[str]
    ascii                 : str
    ascii_short           : Optional[str]
    user                  : Optional[str]
    time                  : datetime
    photo                 : Optional[str]
    photo_thumb           : Optional[str]
    biography             : str
    history_change_reason : Optional[str]
    history_user          : Optional[str]
    history_id            : int
    history_type          : str
    history_date          : datetime
    plain                 : str
    pronouns_freetext     : Optional[str]
    pronouns_selectable   : str


class PersonAliasURI(URI):
    root : str = "/api/v1/person/alias/"


class PersonAlias(Resource):
    id                 : int
    resource_uri       : PersonAliasURI
    person             : PersonURI
    name               : str


class PersonEventURI(URI):
    root : str = "/api/v1/person/personevent/"


class PersonEvent(Resource):
    desc            : str
    id              : int
    person          : PersonURI
    resource_uri    : PersonEventURI
    time            : datetime
    type            : str


class ExtResourceTypeNameURI(URI):
    root : str = "/api/v1/name/extresourcetypename/"


class ExtResourceTypeName(Resource):
    resource_uri : ExtResourceTypeNameURI
    desc         : str
    name         : str
    order        : int
    slug         : str
    used         : bool


class ExtResourceNameURI(URI):
    root : str = "/api/v1/name/extresourcename/"


class ExtResourceName(Resource):
    resource_uri  : ExtResourceNameURI
    type          : ExtResourceTypeNameURI
    desc          : str
    name          : str
    order         : int
    slug          : str
    used          : bool


class PersonExtResourceURI(URI):
    root : str = "/api/v1/person/personextresource/"


class PersonExtResource(Resource):
    id           : int
    resource_uri : PersonExtResourceURI
    display_name : str
    person       : PersonURI
    name         : ExtResourceNameURI
    value        : str


# ---------------------------------------------------------------------------------------------------------------------------------
# Types relating to email addresses:

class EmailURI(URI):
    root : str = "/api/v1/person/email/"


class HistoricalEmailURI(URI):
    root : str = "/api/v1/person/historicalemail/"


class Email(Resource):
    resource_uri : EmailURI
    person       : Optional[PersonURI]
    address      : str # The email address
    time         : datetime
    origin       : str
    primary      : bool
    active       : bool


class HistoricalEmail(Resource):
    resource_uri          : HistoricalEmailURI
    person                : Optional[PersonURI]
    address               : str # The email address
    time                  : datetime
    origin                : str
    primary               : bool
    active                : bool
    history_change_reason : Optional[str]
    history_user          : Optional[str]
    history_id            : int
    history_type          : str
    history_date          : datetime


# ---------------------------------------------------------------------------------------------------------------------------------
# Types relating to documents:

class DocumentTypeURI(URI):
    root : str = "/api/v1/name/doctypename/"


class DocumentType(Resource):
    resource_uri : DocumentTypeURI
    name         : str
    used         : bool
    prefix       : str
    slug         : str
    desc         : str
    order        : int


class DocumentStateTypeURI(URI):
    root : str = "/api/v1/doc/statetype/"


class DocumentStateType(Resource):
    resource_uri : DocumentStateTypeURI
    label        : str
    slug         : str


class DocumentStateURI(URI):
    root : str = "/api/v1/doc/state/"


class DocumentState(Resource):
    id           : int
    resource_uri : DocumentStateURI
    desc         : str
    name         : str
    next_states  : List[DocumentStateURI]
    order        : int
    slug         : str  # FIXME: should we introduce a StateSlug type (and similar for the other slug fields)?
    type         : DocumentStateTypeURI
    used         : bool


class StreamURI(URI):
    root : str = "/api/v1/name/streamname/"


class Stream(Resource):
    resource_uri : StreamURI
    name         : str
    desc         : str
    used         : bool
    slug         : str
    order        : int


class SubmissionURI(URI):
    root : str = "/api/v1/submit/submission/"


class SubmissionCheckURI(URI):
    root : str = "/api/v1/submit/submissioncheck/"


class Submission(Resource):
    abstract        : str
    access_key      : str
    auth_key        : str
    authors         : str   # See the parse_authors() method
    checks          : List[SubmissionCheckURI]
    document_date   : Optional[date]
    draft           : Optional[DocumentURI]
    file_size       : Optional[int]
    file_types      : str   # e.g., ".txt,.xml"
    group           : Optional[GroupURI]
    id              : int
    name            : str
    note            : str
    pages           : Optional[int]
    remote_ip       : str
    replaces        : str   # This is a comma separated list of draft names (e.g., "draft-dkg-hrpc-glossary,draft-varon-hrpc-methodology")
                            # although in most cases there is only one entry, and hence no comma.
    resource_uri    : SubmissionURI
    rev             : str
    state           : str   # FIXME: this should be a URI subtype
    submission_date : date
    submitter       : str
    title           : str
    words           : Optional[int]
    xml_version     : Optional[str]

    """
    URLs from which this submission can be downloaded.
    """
    def urls(self) -> Iterator[Tuple[str, str]]:
        for file_type in self.file_types.split(","):
            yield (file_type, "https://www.ietf.org/archive/id/"  + self.name + "-" + self.rev + file_type)

    def parse_authors(self) -> List[Dict[str,str]]:
        authors = ast.literal_eval(self.authors) # type: List[Dict[str, str]]
        return authors


class SubmissionEventURI(URI):
    root : str = "/api/v1/submit/submissionevent/"


class SubmissionEvent(Resource):
    by              : Optional[PersonURI]
    desc            : str
    id              : int
    resource_uri    : SubmissionEventURI
    submission      : SubmissionURI
    time            : datetime


class DocumentUrlTagURI(URI):
    root : str = "/api/v1/name/docurltagname/"


class DocumentUrlURI(URI):
    root : str = "/api/v1/doc/documenturl/"
    
    
class DocumentUrl(Resource):
    desc         : str
    doc          : DocumentURI
    id           : int
    resource_uri : DocumentUrlURI
    tag          : DocumentUrlTagURI
    url          : str


class DocumentTagURI(URI):
    root : str = "/api/v1/name/doctagname/"


class DocumentTag(Resource):
    resource_uri  : DocumentTagURI
    slug          : str
    order         : int
    name          : str
    used          : bool
    desc          : str


# DocumentURI is defined earlier, to avoid circular dependencies

class Document(Resource):
    id                 : int
    resource_uri       : DocumentURI
    name               : str
    title              : str
    pages              : Optional[int]
    words              : Optional[int]
    time               : datetime
    notify             : str
    expires            : Optional[str]
    type               : DocumentTypeURI
    rfc                : Optional[str]
    rfc_number         : Optional[int]
    rev                : str
    abstract           : str
    note               : str
    ad                 : Optional[PersonURI]
    shepherd           : Optional[EmailURI]
    group              : Optional[GroupURI]
    stream             : Optional[StreamURI]
    intended_std_level : Optional[str]  # FIXME: should be a URI subtype?
    std_level          : Optional[str]  # FIXME: should be a URI subtype?
    states             : List[DocumentStateURI]
    submissions        : List[SubmissionURI]
    tags               : List[DocumentTagURI]
    uploaded_filename  : str
    external_url       : str

    def __post_init__(self) -> None:
        assert self.intended_std_level is None or self.intended_std_level.startswith("/api/v1/name/intendedstdlevelname/")
        assert self.std_level          is None or self.std_level.startswith("/api/v1/name/stdlevelname/")

    def url(self) -> str:
        # See https://github.com/ietf-tools/datatracker/blob/main/ietf/settings.py and search for DOC_HREFS
        if self.type == DocumentTypeURI(uri="/api/v1/name/doctypename/agenda/"):
            # FIXME: should be "/meeting/{meeting.number}/materials/{doc.name}-{doc.rev}" ???
            # FIXME: This doesn't work for interim meetings
            # FIXME: This doesn't work for PDF agenda files
            # FIXME: Older items are under, e.g., https://www.ietf.org/proceedings/90/agenda/agenda-90-precis.txt
            mtg = self.name.split("-")[1]
            # Recent documents are in the datatracker, older ones on the proceedings site
            url = "https://datatracker.ietf.org/meeting/" + mtg + "/materials/" + self.uploaded_filename
            url = "https://www.ietf.org/proceedings/" + mtg + "/agenda/" + self.uploaded_filename
        elif self.type == DocumentTypeURI(uri="/api/v1/name/doctypename/bluesheets/"):
            mtg = self.name.split("-")[1]
            if mtg == "interim":
                mtg = "-".join(self.name.split("-")[1:-1])
            url = "https://www.ietf.org/proceedings/" + mtg + "/bluesheets/" + self.uploaded_filename
        elif self.type == DocumentTypeURI(uri="/api/v1/name/doctypename/charter/"):
            url = "https://www.ietf.org/charter/"     + self.name + "-" + self.rev + ".txt"
        elif self.type == DocumentTypeURI(uri="/api/v1/name/doctypename/conflrev/"):
            url = "https://www.ietf.org/cr/"          + self.name + "-" + self.rev + ".txt"
        elif self.type == DocumentTypeURI(uri="/api/v1/name/doctypename/draft/"):
            url = "https://www.ietf.org/archive/id/"  + self.name + "-" + self.rev + ".txt"
        elif self.type == DocumentTypeURI(uri="/api/v1/name/doctypename/liaison/"):
            url = "https://www.ietf.org/lib/dt/documents/LIAISON/" + self.uploaded_filename
        elif self.type == DocumentTypeURI(uri="/api/v1/name/doctypename/liai-att/"):
            url = "https://www.ietf.org/lib/dt/documents/LIAISON/" + self.uploaded_filename
        elif self.type == DocumentTypeURI(uri="/api/v1/name/doctypename/minutes/"):
            mtg = self.name.split("-")[1]
            # Recent documents are in the datatracker, older ones on the proceedings site
            url = "https://datatracker.ietf.org/meeting/" + mtg + "/materials/" + self.uploaded_filename
            url = "https://www.ietf.org/proceedings/" + mtg + "/minutes/" + self.uploaded_filename
        elif self.type == DocumentTypeURI(uri="/api/v1/name/doctypename/recording/"):
            url = self.external_url
        elif self.type == DocumentTypeURI(uri="/api/v1/name/doctypename/review/"):
            # FIXME: This points to the formatted HTML page containing the message, but we really want the raw message
            url = "https://datatracker.ietf.org/doc/" + self.name
        elif self.type == DocumentTypeURI(uri="/api/v1/name/doctypename/shepwrit/"):
            url = self.external_url
        elif self.type == DocumentTypeURI(uri="/api/v1/name/doctypename/slides/"):
            # FIXME: should be https://www.ietf.org/slides/{doc.name}-{doc.rev} ???
            mtg = self.name.split("-")[1]
            url = "https://www.ietf.org/proceedings/" + mtg + "/slides/" + self.uploaded_filename
        elif self.type == DocumentTypeURI(uri="/api/v1/name/doctypename/statchg/"):
            url = "https://www.ietf.org/ietf-ftp/status-changes/" + self.name + "-" + self.rev + ".txt"
        elif self.type == DocumentTypeURI(uri="/api/v1/name/doctypename/chatlog/"):
            mtg = self.name.split("-")[1]
            if mtg == "interim":
                mtg = "-".join(self.name.split("-")[1:-1])
            url = "https://datatracker.ietf.org/meeting/" + mtg + "/materials/" + self.uploaded_filename
        else:
            raise NotImplementedError
        return url


class DocumentEventURI(URI):
    root : str = "/api/v1/doc/docevent/"


class DocumentEvent(Resource):
    by              : PersonURI
    desc            : str
    doc             : DocumentURI
    id              : int
    resource_uri    : DocumentEventURI
    rev             : str
    time            : datetime
    type            : str


class BallotPositionNameURI(URI):
    root : str = "/api/v1/name/ballotpositionname/"


class BallotPositionName(Resource):
    blocking     : bool
    desc         : Optional[str]
    name         : str
    order        : int
    resource_uri : BallotPositionNameURI
    slug         : str
    used         : bool


class BallotTypeURI(URI):
    root : str = "/api/v1/doc/ballottype/"


class BallotType(Resource):
    doc_type     : DocumentTypeURI
    id           : int
    name         : str
    order        : int
    positions    : List[BallotPositionNameURI]
    question     : str
    resource_uri : BallotTypeURI
    slug         : str
    used         : bool


class BallotDocumentEventURI(URI):
    root : str = "/api/v1/doc/ballotdocevent/"


class BallotDocumentEvent(Resource):
    ballot_type     : BallotTypeURI
    by              : PersonURI
    desc            : str
    doc             : DocumentURI
    docevent_ptr    : DocumentEventURI
    id              : int
    resource_uri    : BallotDocumentEventURI
    rev             : str
    time            : datetime
    type            : str


class RelationshipTypeURI(URI):
    root : str = "/api/v1/name/docrelationshipname/"


class RelationshipType(Resource):
    resource_uri   : RelationshipTypeURI
    slug           : str
    desc           : str
    name           : str
    used           : bool
    order          : int
    revname        : str


class RelatedDocumentURI(URI):
    root : str = "/api/v1/doc/relateddocument/"


class RelatedDocument(Resource):
    id              : int
    relationship    : RelationshipTypeURI
    resource_uri    : RelatedDocumentURI
    source          : DocumentURI
    target          : DocumentURI


class DocumentAuthorURI(URI):
    root : str = "/api/v1/doc/documentauthor/"


class DocumentAuthor(Resource):
    id           : int
    order        : int
    resource_uri : DocumentAuthorURI
    country      : str
    affiliation  : str
    document     : DocumentURI
    person       : PersonURI
    email        : Optional[EmailURI]



# ---------------------------------------------------------------------------------------------------------------------------------
# Types relating to groups:


class GroupStateURI(URI):
    root : str = "/api/v1/name/groupstatename/"


class GroupState(Resource):
    resource_uri   : GroupStateURI
    slug           : str
    desc           : str
    name           : str
    used           : bool
    order          : int


class GroupTypeNameURI(URI):
    root : str = "/api/v1/name/grouptypename/"


class GroupTypeName(Resource):
    desc          : str
    name          : str
    order         : int
    resource_uri  : GroupTypeNameURI
    slug          : str
    used          : bool
    verbose_name  : str


# GroupURI is defined earlier, to avoid circular dependencies


class Group(Resource):
    acronym        : str
    ad             : Optional[PersonURI]
    charter        : Optional[DocumentURI]
    comments       : str
    description    : str
    id             : int
    list_archive   : str
    list_email     : str
    list_subscribe : str
    name           : str
    parent         : Optional[GroupURI]
    resource_uri   : GroupURI
    state          : GroupStateURI
    time           : datetime
    type           : GroupTypeNameURI
    unused_states  : List[DocumentStateURI]
    unused_tags    : List[str]
    meeting_seen_as_area : bool
    used_roles           : str
    uses_milestone_dates : bool


class GroupHistoryURI(URI):
    root : str = "/api/v1/group/grouphistory/"


class GroupHistory(Resource):
    acronym              : str
    ad                   : Optional[PersonURI]
    comments             : str
    description          : str
    group                : GroupURI
    id                   : int
    list_archive         : str
    list_email           : str
    list_subscribe       : str
    name                 : str
    parent               : Optional[GroupURI]
    resource_uri         : GroupHistoryURI
    state                : GroupStateURI
    time                 : datetime
    type                 : GroupTypeNameURI
    unused_states        : List[DocumentStateURI]
    unused_tags          : List[str]
    uses_milestone_dates : bool
    meeting_seen_as_area : bool
    used_roles           : str


class GroupEventURI(URI):
    root : str = "/api/v1/group/groupevent/"


class GroupEvent(Resource):
    by           : PersonURI
    desc         : str
    group        : GroupURI
    id           : int
    resource_uri : GroupEventURI
    time         : datetime
    type         : str


class GroupUrlURI(URI):
    root : str = "/api/v1/group/groupurl/"


class GroupUrl(Resource):
    group        : GroupURI
    id           : int
    name         : str
    resource_uri : GroupUrlURI
    url          : str


class GroupMilestoneStateNameURI(URI):
    root : str = "/api/v1/name/groupmilestonestatename/"


class GroupMilestoneStateName(Resource):
    desc         : str
    name         : str
    order        : int
    resource_uri : GroupMilestoneStateNameURI
    slug         : str
    used         : bool


class GroupMilestoneURI(URI):
    root : str = "/api/v1/group/groupmilestone/"


class GroupMilestone(Resource):
    desc         : str
    docs         : List[DocumentURI]
    due          : str
    group        : GroupURI
    id           : int
    order        : Optional[int]
    resolved     : str
    resource_uri : GroupMilestoneURI
    state        : GroupMilestoneStateNameURI
    time         : datetime


class RoleNameURI(URI):
    root : str = "/api/v1/name/rolename/"


class RoleName(Resource):
    desc         : str
    name         : str
    order        : int
    resource_uri : RoleNameURI
    slug         : str
    used         : bool


class GroupRoleURI(URI):
    root : str = "/api/v1/group/role/"


class GroupRole(Resource):
    email        : EmailURI
    group        : GroupURI
    id           : int
    name         : RoleNameURI
    person       : PersonURI
    resource_uri : GroupRoleURI

class GroupMilestoneHistoryURI(URI):
    root : str = "/api/v1/group/groupmilestonehistory/"


class GroupMilestoneHistory(Resource):
    desc         : str
    docs         : List[DocumentURI]
    due          : str
    group        : GroupURI
    id           : int
    milestone    : GroupMilestoneURI
    order        : Optional[int]
    resolved     : str
    resource_uri : GroupMilestoneHistoryURI
    state        : GroupMilestoneStateNameURI
    time         : datetime


class GroupMilestoneEventURI(URI):
    root : str = "/api/v1/group/milestonegroupevent/"


class GroupMilestoneEvent(Resource):
    by             : PersonURI
    desc           : str
    group          : GroupURI
    groupevent_ptr : GroupEventURI
    id             : int
    milestone      : GroupMilestoneURI
    resource_uri   : GroupMilestoneEventURI
    time           : datetime
    type           : str


class GroupRoleHistoryURI(URI):
    root : str = "/api/v1/group/rolehistory/"


class GroupRoleHistory(Resource):
    email        : EmailURI
    group        : GroupHistoryURI
    id           : int
    name         : RoleNameURI
    person       : PersonURI
    resource_uri : GroupRoleHistoryURI


class GroupStateChangeEventURI(URI):
    root : str = "/api/v1/group/changestategroupevent/"


class GroupStateChangeEvent(Resource):
    by             : PersonURI
    desc           : str
    group          : GroupURI
    groupevent_ptr : GroupEventURI
    id             : int
    resource_uri   : GroupStateChangeEventURI
    state          : GroupStateURI
    time           : datetime
    type           : str


# ---------------------------------------------------------------------------------------------------------------------------------
# Types relating to meetings:

class MeetingStatus(Enum):
    FUTURE    = 1
    ONGOING   = 2
    COMPLETED = 3


class MeetingURI(URI):
    root : str = "/api/v1/meeting/meeting/"


class MeetingTypeURI(URI):
    root : str = "/api/v1/name/meetingtypename/"


class MeetingType(Resource):
    name         : str
    order        : int
    resource_uri : MeetingTypeURI
    slug         : str
    desc         : str
    used         : bool


class ScheduleURI(URI):
    root : str = "/api/v1/meeting/schedule/"


class Schedule(Resource):
    """
    A particular version of the meeting schedule (i.e., the meeting agenda)

    Use `meeting_session_assignments()` to find the assignment of sessions
    to timeslots within this schedule.
    """
    id           : int
    name         : str
    resource_uri : ScheduleURI
    owner        : PersonURI
    meeting      : MeetingURI
    visible      : bool
    public       : bool
    badness      : Optional[int]


class Meeting(Resource):
    id                               : int
    resource_uri                     : MeetingURI
    type                             : MeetingTypeURI
    country                          : str
    city                             : str
    venue_name                       : str
    venue_addr                       : str
    date                             : date
    days                             : int  # FIXME: this should be a timedelta object
    time_zone                        : str
    acknowledgements                 : str
    agenda_info_note                 : str
    agenda_warning_note              : str
    session_request_lock_message     : str
    idsubmit_cutoff_warning_days     : str
    idsubmit_cutoff_time_utc         : str
    idsubmit_cutoff_day_offset_00    : int
    idsubmit_cutoff_day_offset_01    : int
    submission_start_day_offset      : int
    submission_cutoff_day_offset     : int
    submission_correction_day_offset : int
    agenda                           : Optional[ScheduleURI]  # An alias for schedule
    schedule                         : Optional[ScheduleURI]  # The current meeting schedule (i.e., the agenda)
    number                           : str
    break_area                       : str
    reg_area                         : str
    proceedings_final                : bool
    show_important_dates             : bool
    attendees                        : Optional[int]
    updated                          : Optional[datetime]     # Time this record was modified

    def status(self) -> MeetingStatus:
        now = date.today()
        meeting_start = self.date
        meeting_end   = self.date + timedelta(days = self.days)
        if meeting_start > now:
            return MeetingStatus.FUTURE
        elif meeting_end < now:
            return MeetingStatus.COMPLETED
        else:
            return MeetingStatus.ONGOING


class SessionURI(URI):
    root : str = "/api/v1/meeting/session/"


class TimeslotURI(URI):
    root : str = "/api/v1/meeting/timeslot/"


class Timeslot(Resource):
    id            : int
    resource_uri  : TimeslotURI
    type          : str               # FIXME: this is a URI "/api/v1/name/timeslottypename/regular/"
    meeting       : MeetingURI
    sessions      : List[SessionURI]  # Sessions assigned to this slot in various versions of the agenda; current assignment is last
    name          : str
    time          : datetime
    duration      : str               # FIXME: this should be a timedelta object
    location      : Optional[str]     # FIXME: this is a URI "/api/v1/meeting/room/668"
    show_location : bool
    modified      : datetime


class SessionAssignmentURI(URI):
    root : str = "/api/v1/meeting/schedtimesessassignment/"


class SessionAssignment(Resource):
    """
    The assignment of a `session` to a `timeslot` within a meeting `schedule`
    """
    id           : int
    resource_uri : SessionAssignmentURI
    session      : SessionURI
    agenda       : ScheduleURI  # An alias for `schedule`
    schedule     : ScheduleURI
    timeslot     : TimeslotURI
    modified     : datetime
    pinned       : bool
    extendedfrom : Optional[str]
    badness      : Optional[int]


class SessionPurposeURI(URI):
    root : str = "/api/v1/name/sessionpurposename/"


class SessionPurpose(Resource):
    resource_uri   : SessionPurposeURI
    used           : bool
    timeslot_types : str
    order          : int
    on_agenda      : bool
    name           : str
    desc           : str
    slug           : str


class Session(Resource):
    """
    A session within a meeting.

    Note that a Session object is created, and will be assigned to a
    Timeslot, when a Meeting is requested, not when it is scheduled.
    Use the `meeting_session_status()` method to check if the session
    was actually scheduled to take place.
    """
    id                  : int
    type                : str           # FIXME: this is a URI
    name                : str
    resource_uri        : SessionURI
    meeting             : MeetingURI
    group               : GroupURI
    materials           : List[DocumentURI]
    scheduled           : Optional[datetime]
    requested_duration  : str
    resources           : List[str]    # FIXME
    agenda_note         : str
    assignments         : List[SessionAssignmentURI]
    remote_instructions : str
    short               : str
    attendees           : Optional[int]
    modified            : datetime
    comments            : str
    on_agenda           : bool
    purpose             : SessionPurposeURI
    has_onsite_tool     : bool
    chat_room           : str


class SessionStatusNameURI(URI):
    root : str = "/api/v1/name/sessionstatusname/"


class SessionStatusName(Resource):
    order        : int
    slug         : str
    resource_uri : SessionStatusNameURI
    used         : bool
    desc         : str
    name         : str


class SchedulingEventURI(URI):
    root : str = "/api/v1/meeting/schedulingevent/"


class SchedulingEvent(Resource):
    id           : int
    session      : SessionURI
    status       : SessionStatusNameURI
    by           : PersonURI
    resource_uri : SchedulingEventURI
    time         : datetime


class MeetingAttendedURI(URI):
    root : str = "/api/v1/meeting/attended/"


class MeetingAttended(Resource):
    id           : int
    origin       : str
    person       : PersonURI
    resource_uri : MeetingAttendedURI
    session      : SessionURI
    time         : datetime


# See also MeetingRegistrationURI
class MeetingRegistrationOldURI(URI):
    root : str = "/api/v1/stats/meetingregistration/"


# See also MeetingRegistration
class MeetingRegistrationOld(Resource):
    affiliation  : str
    attended     : bool
    country_code : str
    email        : str
    first_name   : str
    id           : int
    last_name    : str
    meeting      : MeetingURI
    person       : Optional[PersonURI]
    resource_uri : MeetingRegistrationOldURI
    checkedin    : bool


# ---------------------------------------------------------------------------------------------------------------------------------
# Types relating to IPR disclosures:

class IPRDisclosureStateURI(URI):
    root : str = "/api/v1/name/iprdisclosurestatename/"


class IPRDisclosureState(Resource):
    desc         : str
    name         : str
    order        : int
    resource_uri : IPRDisclosureStateURI
    slug         : str
    used         : bool


class IPRDisclosureBaseURI(URI):
    root : str = "/api/v1/ipr/iprdisclosurebase/"


class IPRDisclosureBase(Resource):
    by                 : PersonURI
    compliant          : bool
    docs               : List[DocumentURI]
    holder_legal_name  : str
    id                 : int
    notes              : str
    other_designations : str
    rel                : List[IPRDisclosureBaseURI]
    resource_uri       : IPRDisclosureBaseURI
    state              : IPRDisclosureStateURI
    submitter_email    : str
    submitter_name     : str
    time               : datetime
    title              : str


class GenericIPRDisclosureURI(URI):
    root : str = "/api/v1/ipr/genericiprdisclosure/"


class GenericIPRDisclosure(Resource):
    by                    : PersonURI
    compliant             : bool
    docs                  : List[DocumentURI]
    holder_contact_email  : str
    holder_contact_info   : str
    holder_contact_name   : str
    holder_legal_name     : str
    id                    : int
    iprdisclosurebase_ptr : IPRDisclosureBaseURI
    notes                 : str
    other_designations    : str
    rel                   : List[IPRDisclosureBaseURI]
    resource_uri          : GenericIPRDisclosureURI
    state                 : IPRDisclosureStateURI
    statement             : str
    submitter_email       : str
    submitter_name        : str
    time                  : datetime
    title                 : str


class IPRLicenseTypeURI(URI):
    root : str = "/api/v1/name/iprlicensetypename/"


class IPRLicenseType(Resource):
    desc         : str
    name         : str
    order        : int
    resource_uri : IPRLicenseTypeURI
    slug         : str
    used         : bool


class HolderIPRDisclosureURI(URI):
    root : str = "/api/v1/ipr/holderiprdisclosure/"


class HolderIPRDisclosure(Resource):
    by                                   : PersonURI
    compliant                            : bool
    docs                                 : List[DocumentURI]
    has_patent_pending                   : bool
    holder_contact_email                 : str
    holder_contact_info                  : str
    holder_contact_name                  : str
    holder_legal_name                    : str
    id                                   : int
    ietfer_contact_email                 : str
    ietfer_contact_info                  : str
    ietfer_name                          : str
    iprdisclosurebase_ptr                : IPRDisclosureBaseURI
    licensing                            : IPRLicenseTypeURI
    licensing_comments                   : str
    notes                                : str
    other_designations                   : str
    patent_info                          : str
    rel                                  : List[IPRDisclosureBaseURI]
    resource_uri                         : HolderIPRDisclosureURI
    state                                : IPRDisclosureStateURI
    submitter_claims_all_terms_disclosed : bool
    submitter_email                      : str
    submitter_name                       : str
    time                                 : datetime
    title                                : str


class ThirdPartyIPRDisclosureURI(URI):
    root : str = "/api/v1/ipr/thirdpartyiprdisclosure/"


class ThirdPartyIPRDisclosure(Resource):
    by                     : PersonURI
    compliant              : bool
    docs                   : List[DocumentURI]
    has_patent_pending     : bool
    holder_legal_name      : str
    id                     : int
    ietfer_contact_email   : str
    ietfer_contact_info    : str
    ietfer_name            : str
    iprdisclosurebase_ptr  : IPRDisclosureBaseURI
    notes                  : str
    other_designations     : str
    patent_info            : str
    rel                    : List[IPRDisclosureBaseURI]
    resource_uri           : ThirdPartyIPRDisclosureURI
    state                  : IPRDisclosureStateURI
    submitter_email        : str
    submitter_name         : str
    time                   : datetime
    title                  : str


# ---------------------------------------------------------------------------------------------------------------------------------
# Types relating to reviews:

class ReviewAssignmentStateURI(URI):
    root : str = "/api/v1/name/reviewassignmentstatename/"


class ReviewAssignmentState(Resource):
    desc         : str
    name         : str
    order        : int
    resource_uri : ReviewAssignmentStateURI
    slug         : str
    used         : bool


class ReviewResultTypeURI(URI):
    root : str = "/api/v1/name/reviewresultname/"


class ReviewResultType(Resource):
    desc         : str
    name         : str
    order        : int
    resource_uri : ReviewResultTypeURI
    slug         : str
    used         : bool


class ReviewTypeURI(URI):
    root : str = "/api/v1/name/reviewtypename/"


class ReviewType(Resource):
    desc         : str
    name         : str
    order        : int
    resource_uri : ReviewTypeURI
    slug         : str
    used         : bool


class ReviewRequestStateURI(URI):
    root : str = "/api/v1/name/reviewrequeststatename/"


class ReviewRequestState(Resource):
    desc         : str
    name         : str
    order        : int
    resource_uri : ReviewRequestStateURI
    slug         : str
    used         : bool


class ReviewRequestURI(URI):
    root : str = "/api/v1/review/reviewrequest/"


class ReviewRequest(Resource):
    comment       : str
    deadline      : str
    doc           : DocumentURI
    id            : int
    requested_by  : PersonURI
    requested_rev : str
    resource_uri  : ReviewRequestURI
    state         : ReviewRequestStateURI
    team          : GroupURI
    time          : datetime
    type          : ReviewTypeURI


class ReviewAssignmentURI(URI):
    root : str = "/api/v1/review/reviewassignment/"


class ReviewAssignment(Resource):
    assigned_on    : datetime
    completed_on   : Optional[datetime]
    id             : int
    mailarch_url   : Optional[str] # can type?
    resource_uri   : ReviewAssignmentURI
    result         : Optional[ReviewResultTypeURI]
    review         : Optional[DocumentURI]
    review_request : ReviewRequestURI
    reviewed_rev   : str
    reviewer       : EmailURI
    state          : ReviewAssignmentStateURI


class ReviewWishURI(URI):
    root : str = "/api/v1/review/reviewwish/"


class ReviewWish(Resource):
    doc          : DocumentURI
    id           : int
    person       : PersonURI
    resource_uri : ReviewWishURI
    team         : GroupURI
    time         : datetime


class HistoricalUnavailablePeriodURI(URI):
    root : str = "/api/v1/review/historicalunavailableperiod/"


class HistoricalUnavailablePeriod(Resource):
    availability          : str
    end_date              : str
    history_change_reason : str
    history_date          : datetime
    history_id            : int
    history_type          : str
    id                    : int
    person                : PersonURI
    reason                : str
    resource_uri          : HistoricalUnavailablePeriodURI
    start_date            : str
    team                  : GroupURI


class HistoricalReviewRequestURI(URI):
    root : str = "/api/v1/review/historicalreviewrequest/"


class HistoricalReviewRequest(Resource):
    comment               : str
    deadline              : str
    doc                   : DocumentURI
    history_change_reason : str
    history_date          : datetime
    history_id            : int
    history_type          : str
    id                    : int
    requested_by          : PersonURI
    requested_rev         : str
    resource_uri          : HistoricalReviewRequestURI
    state                 : ReviewRequestStateURI
    team                  : GroupURI
    time                  : datetime
    type                  : ReviewTypeURI


class NextReviewerInTeamURI(URI):
    root : str = "/api/v1/review/nextreviewerinteam/"


class NextReviewerInTeam(Resource):
    id            : int
    next_reviewer : PersonURI
    resource_uri  : NextReviewerInTeamURI
    team          : GroupURI


class ReviewTeamSettingsURI(URI):
    root : str = "/api/v1/review/reviewteamsettings/"


class ReviewTeamSettings(Resource):
    autosuggest                             : bool
    group                                   : GroupURI
    id                                      : int
    notify_ad_when                          : List[ReviewResultTypeURI]
    remind_days_unconfirmed_assignments     : Optional[int]
    resource_uri                            : ReviewTeamSettingsURI
    review_results                          : List[ReviewResultTypeURI]
    review_types                            : List[ReviewTypeURI]
    secr_mail_alias                         : str
    allow_reviewer_to_reject_after_deadline : bool


class ReviewerSettingsURI(URI):
    root : str = "/api/v1/review/reviewersettings/"


class ReviewerSettings(Resource):
    expertise                   : str
    filter_re                   : str
    id                          : int
    min_interval                : Optional[int]
    person                      : PersonURI
    remind_days_before_deadline : Optional[int]
    remind_days_open_reviews    : Optional[int]
    request_assignment_next     : bool
    resource_uri                : ReviewerSettingsURI
    skip_next                   : int
    team                        : GroupURI


class UnavailablePeriodURI(URI):
    root : str = "/api/v1/review/unavailableperiod/"


class UnavailablePeriod(Resource):
    availability : str
    end_date     : str
    id           : int
    person       : PersonURI
    reason       : str
    resource_uri : UnavailablePeriodURI
    start_date   : Optional[str]
    team         : GroupURI


class HistoricalReviewerSettingsURI(URI):
    root : str = "/api/v1/review/historicalreviewersettings/"


class HistoricalReviewerSettings(Resource):
    expertise                   : str
    filter_re                   : str
    history_change_reason       : Optional[str]
    history_date                : datetime
    history_id                  : int
    history_type                : str
    history_user                : str
    id                          : int
    min_interval                : Optional[int]
    person                      : PersonURI
    remind_days_before_deadline : Optional[int]
    remind_days_open_reviews    : Optional[int]
    request_assignment_next     : bool
    resource_uri                : HistoricalReviewerSettingsURI
    skip_next                   : int
    team                        : GroupURI


class HistoricalReviewAssignmentURI(URI):
    root : str = "/api/v1/review/historicalreviewassignment/"


class HistoricalReviewAssignment(Resource):
    assigned_on           : datetime
    completed_on          : datetime
    history_change_reason : str
    history_date          : datetime
    history_id            : int
    history_type          : str
    id                    : int
    mailarch_url          : Optional[str]
    resource_uri          : HistoricalReviewAssignmentURI
    result                : ReviewResultTypeURI
    review                : DocumentURI
    review_request        : ReviewRequestURI
    reviewed_rev          : str
    reviewer              : EmailURI
    state                 : ReviewAssignmentStateURI


class ReviewSecretarySettingsURI(URI):
    root : str = "/api/v1/review/reviewsecretarysettings/"


class ReviewSecretarySettings(Resource):
    days_to_show_in_reviewer_list      : Optional[int]
    id                                 : int
    max_items_to_show_in_reviewer_list : Optional[int]
    person                             : PersonURI
    remind_days_before_deadline        : int
    resource_uri                       : ReviewSecretarySettingsURI
    team                               : GroupURI


# ---------------------------------------------------------------------------------------------------------------------------------
# Types relating to mailing lists:

class EmailListURI(URI):
    root : str = "/api/v1/mailinglists/list/"


class EmailList(Resource):
    id           : int
    resource_uri : EmailListURI
    name         : str
    description  : str
    advertised   : bool


class EmailListSubscriptionsURI(URI):
    root : str = "/api/v1/mailinglists/subscribed/"


class EmailListSubscriptions(Resource):
    id           : int
    resource_uri : EmailListSubscriptionsURI
    email        : str
    lists        : List[EmailListURI]
    time         : datetime


# ---------------------------------------------------------------------------------------------------------------------------------
# Types relating to places:

class ContinentURI(URI):
    root : str = "/api/v1/name/continentname/"


class Continent(Resource):
    resource_uri : ContinentURI
    desc         : str
    order        : int
    name         : str
    used         : bool
    slug         : str


class CountryURI(URI):
    root : str = "/api/v1/name/countryname/"


class Country(Resource):
    resource_uri : CountryURI
    desc         : str
    slug         : str
    in_eu        : bool
    order        : int
    used         : bool
    name         : str
    continent    : ContinentURI


class CountryAliasURI(URI):
    root : str = "/api/v1/stats/countryalias/"


class CountryAlias(Resource):
    id           : int
    resource_uri : CountryAliasURI
    country      : CountryURI
    alias        : str


# ---------------------------------------------------------------------------------------------------------------------------------
# Types relating to statistics:

# See also MeetingRegistrationOldURI
class MeetingRegistrationURI(URI):
    root : str = "/api/v1/stats/meetingregistration/"


# See also MeetingRegistrationOld
class MeetingRegistration(Resource):
    affiliation  : str
    attended     : bool
    country_code : str
    email        : str
    first_name   : str
    id           : int
    last_name    : str
    meeting      : MeetingURI
    person       : Optional[PersonURI]
    reg_type     : str
    resource_uri : MeetingRegistrationURI
    ticket_type  : str
    checkedin    : bool


# =================================================================================================================================
# vim: set tw=0 ai:
