# Copyright (C) 2017-2020 University of Glasgow
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

# The module contains code to interact with the IETF Datatracker
# (https://datatracker.ietf.org/release/about)
#
# The Datatracker API is at https://datatracker.ietf.org/api/v1 and is
# a REST API implemented using Django Tastypie (http://tastypieapi.org)
#
# It's possible to do time range queries on many of these values, for example:
#   https://datatracker.ietf.org/api/v1/person/person/?time__gt=2018-03-27T14:07:36
#
# See also:
#   https://datatracker.ietf.org/api/
#   https://trac.tools.ietf.org/tools/ietfdb/wiki/DatabaseSchemaDescription
#   https://trac.tools.ietf.org/tools/ietfdb/wiki/DatatrackerDrafts
#   RFC 6174 "Definition of IETF Working Group Document States"
#   RFC 6175 "Requirements to Extend the Datatracker for IETF Working Group Chairs and Authors"
#   RFC 6292 "Requirements for a Working Group Charter Tool"
#   RFC 6293 "Requirements for Internet-Draft Tracking by the IETF Community in the Datatracker"
#   RFC 6322 "Datatracker States and Annotations for the IAB, IRTF, and Independent Submission Streams"
#   RFC 6359 "Datatracker Extensions to Include IANA and RFC Editor Processing Information"
#   RFC 7760 "Statement of Work for Extensions to the IETF Datatracker for Author Statistics"

from datetime    import datetime, timedelta
from enum        import Enum
from typing      import List, Optional, Tuple, Dict, Iterator, Type, TypeVar
from dataclasses import dataclass
from pavlova     import Pavlova
from pavlova.parsers import GenericParser

T = TypeVar('T')

import glob
import json
import requests
import re

# =================================================================================================================================
# Classes to represent the JSON-serialised objects returned by the Datatracker API:

# ---------------------------------------------------------------------------------------------------------------------------------
# URI types:

@dataclass(frozen=True)
class URI:
    uri : str


@dataclass(frozen=True)
class DocumentURI(URI):
    def __post_init__(self) -> None:
        assert self.uri.startswith("/api/v1/doc/document/")


@dataclass(frozen=True)
class GroupURI(URI):
    def __post_init__(self) -> None:
        assert self.uri.startswith("/api/v1/group/group/")


# ---------------------------------------------------------------------------------------------------------------------------------
# Types relating to people:

@dataclass(frozen=True)
class PersonURI(URI):
    def __post_init__(self) -> None:
        assert self.uri.startswith("/api/v1/person/person/") or self.uri.startswith("/api/v1/person/historicalperson/")


@dataclass(frozen=True)
class Person:
    resource_uri    : PersonURI
    id              : int
    name            : str
    name_from_draft : str
    ascii           : str
    ascii_short     : Optional[str]
    user            : str
    time            : str
    photo           : str
    photo_thumb     : str
    biography       : str
    consent         : bool


@dataclass(frozen=True)
class HistoricalPerson(Person):
    history_change_reason : Optional[str]
    history_user          : Optional[str]
    history_id            : int
    history_type          : str
    history_date          : str


@dataclass(frozen=True)
class PersonAliasURI(URI):
    def __post_init__(self) -> None:
        assert self.uri.startswith("/api/v1/person/alias/")


@dataclass(frozen=True)
class PersonAlias:
    id                 : int
    resource_uri       : PersonAliasURI
    person             : PersonURI
    name               : str


@dataclass(frozen=True)
class PersonEventURI(URI):
    def __post_init__(self) -> None:
        assert self.uri.startswith("/api/v1/person/personevent/")


@dataclass(frozen=True)
class PersonEvent:
    desc            : str
    id              : int
    person          : PersonURI
    resource_uri    : PersonEventURI
    time            : str
    type            : str


# ---------------------------------------------------------------------------------------------------------------------------------
# Types relating to email addresses:

@dataclass(frozen=True)
class EmailURI(URI):
    def __post_init__(self) -> None:
        assert self.uri.startswith("/api/v1/person/email/") or self.uri.startswith("/api/v1/person/historicalemail/")


@dataclass(frozen=True)
class Email:
    resource_uri : EmailURI
    person       : PersonURI
    address      : str # The email address
    time         : str
    origin       : str
    primary      : bool
    active       : bool


@dataclass(frozen=True)
class HistoricalEmail(Email):
    history_change_reason : Optional[str]
    history_user          : Optional[str]
    history_id            : int
    history_type          : str
    history_date          : str


# ---------------------------------------------------------------------------------------------------------------------------------
# Types relating to documents:

@dataclass(frozen=True)
class DocumentTypeURI(URI):
    def __post_init__(self) -> None:
        assert self.uri.startswith("/api/v1/name/doctypename/")


@dataclass(frozen=True)
class DocumentType:
    resource_uri : DocumentTypeURI
    name         : str
    used         : bool
    prefix       : str
    slug         : str
    desc         : str
    order        : int


@dataclass(frozen=True)
class DocumentStateTypeURI(URI):
    def __post_init__(self) -> None:
        assert self.uri.startswith("/api/v1/doc/statetype/")


@dataclass(frozen=True)
class DocumentStateType:
    resource_uri : DocumentStateTypeURI
    label        : str
    slug         : str


@dataclass(frozen=True)
class DocumentStateURI(URI):
    def __post_init__(self) -> None:
        assert self.uri.startswith("/api/v1/doc/state/")


@dataclass(frozen=True)
class DocumentState:
    id           : int
    resource_uri : DocumentStateURI
    desc         : str
    name         : str
    next_states  : List[DocumentStateURI]
    order        : int
    slug         : str  # FIXME: should we introduce a StateSlug type (and similar for the other slug fields)?
    type         : DocumentStateTypeURI
    used         : bool


@dataclass(frozen=True)
class StreamURI(URI):
    def __post_init__(self) -> None:
        assert self.uri.startswith("/api/v1/name/streamname/")


@dataclass(frozen=True)
class Stream:
    resource_uri : StreamURI
    name         : str
    desc         : str
    used         : bool
    slug         : str
    order        : int


@dataclass(frozen=True)
class SubmissionURI(URI):
    def __post_init__(self) -> None:
        assert self.uri.startswith("/api/v1/submit/submission/")


@dataclass(frozen=True)
class SubmissionCheckURI(URI):
    def __post_init__(self) -> None:
        assert self.uri.startswith("/api/v1/submit/submissioncheck/")
        

@dataclass(frozen=True)
class Submission:
    abstract        : str
    access_key      : str
    auth_key        : str
    authors         : str
    checks          : List[SubmissionCheckURI]
    document_date   : str
    draft           : DocumentURI
    file_size       : Optional[int]
    file_types      : str
    first_two_pages : str
    group           : Optional[GroupURI]
    id              : int
    name            : str
    note            : str
    pages           : Optional[int]
    remote_ip       : str
    replaces        : str   # FIXME: this should be an Optional[URI]?
    resource_uri    : SubmissionURI
    rev             : str
    state           : str   # FIXME: this should be a URI subtype
    submission_date : str
    submitter       : str
    title           : str
    words           : Optional[int]


@dataclass(frozen=True)
class SubmissionEventURI(URI):
    def __post_init__(self) -> None:
        assert self.uri.startswith("/api/v1/submit/submissionevent/")


@dataclass(frozen=True)
class SubmissionEvent:
    by              : Optional[PersonURI]
    desc            : str
    id              : int
    resource_uri    : SubmissionEventURI
    submission      : SubmissionURI
    time            : str


# DocumentURI is defined earlier, to avoid circular dependencies

@dataclass(frozen=True)
class Document:
    id                 : int
    resource_uri       : DocumentURI
    name               : str
    title              : str
    pages              : Optional[int]
    words              : Optional[int]
    time               : str
    notify             : str
    expires            : Optional[str]
    type               : DocumentTypeURI
    rfc                : Optional[int]
    rev                : str           # If `rfc` is not None, `rev` will point to the RFC publication notice
    abstract           : str
    internal_comments  : str
    order              : int
    note               : str
    ad                 : Optional[PersonURI]
    shepherd           : Optional[EmailURI]
    group              : Optional[GroupURI]
    stream             : Optional[StreamURI]
    intended_std_level : Optional[str]  # FIXME: should be a URI subtype?
    std_level          : Optional[str]  # FIXME: should be a URI subtype?
    states             : List[DocumentStateURI]
    submissions        : List[SubmissionURI]
    tags               : List[str]
    uploaded_filename  : str
    external_url       : str

    def __post_init__(self) -> None:
        assert self.intended_std_level is None or self.intended_std_level.startswith("/api/v1/name/intendedstdlevelname/")
        assert self.std_level          is None or self.std_level.startswith("/api/v1/name/stdlevelname/")

    def document_url(self) -> str:
        if self.type == DocumentTypeURI("/api/v1/name/doctypename/agenda/"):
            # FIXME: This doesn't work for interim meetings
            # FIXME: This doesn't work for PDF agenda files
            mtg = self.name.split("-")[1]
            url = "https://datatracker.ietf.org/meeting/" + mtg + "/materials/" + self.uploaded_filename
        elif self.type == DocumentTypeURI("/api/v1/name/doctypename/bluesheets/"):
            mtg = self.name.split("-")[1]
            url = "https://www.ietf.org/proceedings/" + mtg + "/bluesheets/" + self.uploaded_filename
        elif self.type == DocumentTypeURI("/api/v1/name/doctypename/charter/"):
            url = "https://www.ietf.org/charter/"     + self.name + "-" + self.rev + ".txt"
        elif self.type == DocumentTypeURI("/api/v1/name/doctypename/conflrev/"):
            url = "https://www.ietf.org/cr/"          + self.name + "-" + self.rev + ".txt"
        elif self.type == DocumentTypeURI("/api/v1/name/doctypename/draft/"):
            url = "https://www.ietf.org/archive/id/"  + self.name + "-" + self.rev + ".txt"
        elif self.type == DocumentTypeURI("/api/v1/name/doctypename/liaison/"):
            url = "https://www.ietf.org/lib/dt/documents/LIAISON/" + self.uploaded_filename
        elif self.type == DocumentTypeURI("/api/v1/name/doctypename/liai-att/"):
            url = "https://www.ietf.org/lib/dt/documents/LIAISON/" + self.uploaded_filename
        elif self.type == DocumentTypeURI("/api/v1/name/doctypename/minutes/"):
            mtg = self.name.split("-")[1]
            url = "https://datatracker.ietf.org/meeting/" + mtg + "/materials/" + self.uploaded_filename
        elif self.type == DocumentTypeURI("/api/v1/name/doctypename/recording/"):
            url = self.external_url
        elif self.type == DocumentTypeURI("/api/v1/name/doctypename/review/"):
            # FIXME: This points to the formatted HTML page containing the message, but we really want the raw message
            url = "https://datatracker.ietf.org/doc/" + self.name
        elif self.type == DocumentTypeURI("/api/v1/name/doctypename/shepwrit/"):
            url = self.external_url
        elif self.type == DocumentTypeURI("/api/v1/name/doctypename/slides/"):
            mtg = self.name.split("-")[1]
            url = "https://www.ietf.org/proceedings/" + mtg + "/slides/" + self.uploaded_filename
        elif self.type == DocumentTypeURI("/api/v1/name/doctypename/statchg/"):
            url = "https://www.ietf.org/sc/"          + self.name + "-" + self.rev + ".txt"
        else:
            raise NotImplementedError
        return url


@dataclass(frozen=True)
class DocumentAliasURI(URI):
    def __post_init__(self) -> None:
        assert self.uri.startswith("/api/v1/doc/docalias/")


@dataclass(frozen=True)
class DocumentAlias:
    id           : int
    resource_uri : DocumentAliasURI
    document     : DocumentURI
    name         : str


@dataclass(frozen=True)
class DocumentEventURI(URI):
    def __post_init__(self) -> None:
        assert self.uri.startswith("/api/v1/doc/docevent/")


@dataclass(frozen=True)
class DocumentEvent:
    by              : PersonURI
    desc            : str
    doc             : DocumentURI
    id              : int
    resource_uri    : DocumentEventURI
    rev             : str
    time            : str
    type            : str


@dataclass(frozen=True)
class RelationshipTypeURI(URI):
    def __post_init__(self) -> None:
        assert self.uri.startswith("/api/v1/name/docrelationshipname/")


@dataclass(frozen=True)
class RelationshipType:
    resource_uri   : RelationshipTypeURI
    slug           : str
    desc           : str
    name           : str
    used           : bool
    order          : int
    revname        : str


@dataclass(frozen=True)
class RelatedDocumentURI(URI):
    def __post_init__(self) -> None:
        assert self.uri.startswith("/api/v1/doc/relateddocument/")


@dataclass(frozen=True)
class RelatedDocument:
    id              : int
    relationship    : RelationshipTypeURI
    resource_uri    : RelatedDocumentURI
    source          : DocumentURI
    target          : DocumentAliasURI


class DocumentAuthorURI(URI):
    def __post_init__(self) -> None:
        assert self.uri.startswith("/api/v1/doc/documentauthor/")

@dataclass(frozen=True)
class DocumentAuthor:
    id           : int
    order        : int
    resource_uri : DocumentAuthorURI
    country      : str
    affiliation  : str
    document     : DocumentURI
    person       : PersonURI
    email        : EmailURI
    

# ---------------------------------------------------------------------------------------------------------------------------------
# Types relating to groups:


# GroupURI is defined earlier, to avoid circular dependencies


@dataclass(frozen=True)
class Group:
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
    parent         : GroupURI
    resource_uri   : GroupURI
    state          : str    # FIXME: this should be a URI subtype
    time           : str
    type           : str    # FIXME: this should be a URI subtype
    unused_states  : List[str]
    unused_tags    : List[str]


@dataclass(frozen=True)
class GroupStateURI(URI):
    def __post_init__(self) -> None:
        assert self.uri.startswith("/api/v1/name/groupstatename/")


@dataclass(frozen=True)
class GroupState:
    resource_uri   : GroupStateURI
    slug           : str
    desc           : str
    name           : str
    used           : bool
    order          : int


# ---------------------------------------------------------------------------------------------------------------------------------
# Types relating to meetings:

class MeetingStatus(Enum):
    FUTURE    = 1
    ONGOING   = 2
    COMPLETED = 3


@dataclass(frozen=True)
class MeetingURI(URI):
    def __post_init__(self) -> None:
        assert self.uri.startswith("/api/v1/meeting/meeting/")


@dataclass(frozen=True)
class MeetingTypeURI(URI):
    def __post_init__(self) -> None:
        assert self.uri.startswith("/api/v1/name/meetingtypename/")


@dataclass(frozen=True)
class MeetingType:
    name         : str
    order        : int
    resource_uri : MeetingTypeURI
    slug         : str
    desc         : str
    used         : bool


@dataclass(frozen=True)
class ScheduleURI(URI):
    def __post_init__(self) -> None:
        assert self.uri.startswith("/api/v1/meeting/schedule/")


@dataclass(frozen=True)
class Schedule:
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
    badness      : Optional[str]


@dataclass(frozen=True)
class Meeting:
    id                               : int
    resource_uri                     : MeetingURI
    type                             : MeetingTypeURI
    country                          : str
    city                             : str
    venue_name                       : str
    venue_addr                       : str
    date                             : str  # Start date of the meeting
    days                             : int  # Duration of the meeting
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
    agenda                           : ScheduleURI  # An alias for schedule
    schedule                         : ScheduleURI  # The current meeting schedule (i.e., the agenda)
    number                           : str
    break_area                       : str
    reg_area                         : str
    proceedings_final                : bool
    show_important_dates             : bool
    attendees                        : Optional[int]
    updated                          : str  # Time this record was modified

    def status(self) -> MeetingStatus:
        now = datetime.now()
        meeting_start = datetime.strptime(self.date, "%Y-%m-%d")
        meeting_end   = meeting_start + timedelta(days = self.days - 1)
        if meeting_start > now:
            return MeetingStatus.FUTURE
        elif meeting_end < now:
            return MeetingStatus.COMPLETED
        else:
            return MeetingStatus.ONGOING


@dataclass(frozen=True)
class SessionURI(URI):
    def __post_init__(self) -> None:
        assert self.uri.startswith("/api/v1/meeting/session/")


@dataclass(frozen=True)
class TimeslotURI(URI):
    def __post_init__(self) -> None:
        assert self.uri.startswith("/api/v1/meeting/timeslot/")


@dataclass(frozen=True)
class Timeslot:
    id            : int
    resource_uri  : TimeslotURI
    type          : str               # FIXME: this is a URI "/api/v1/name/timeslottypename/regular/"
    meeting       : MeetingURI
    sessions      : List[SessionURI]  # Sessions assigned to this slot in various versions of the agenda; current assignment is last
    name          : str
    time          : str
    duration      : str
    location      : str               # FIXME this is a URI "/api/v1/meeting/room/668
    show_location : bool
    modified      : str


@dataclass(frozen=True)
class AssignmentURI(URI):
    def __post_init__(self) -> None:
        assert self.uri.startswith("/api/v1/meeting/schedtimesessassignment/")


@dataclass(frozen=True)
class Assignment:
    """
    The assignment of a `session` to a `timeslot` within a meeting `schedule`
    """
    id           : int
    resource_uri : AssignmentURI
    session      : SessionURI
    agenda       : ScheduleURI  # An alias for `schedule`
    schedule     : ScheduleURI
    timeslot     : TimeslotURI
    modified     : str
    notes        : str
    pinned       : bool
    extendedfrom : Optional[str]
    badness      : int


@dataclass(frozen=True)
class Session:
    id                  : int
    type                : str           # FIXME: this is a URI
    name                : str
    resource_uri        : SessionURI
    meeting             : MeetingURI
    group               : GroupURI
    materials           : List[DocumentURI]
    scheduled           : str          # Date scheduled
    requested_duration  : str
    resources           : List[str]    # FIXME
    agenda_note         : str
    assignments         : List[AssignmentURI]
    remote_instructions : str
    short               : str
    attendees           : int
    modified            : str
    comments            : str


# =================================================================================================================================
# A class to represent the datatracker:

class DataTracker:
    """
    A class for interacting with the IETF DataTracker.
    """
    def __init__(self):
        self.session  = requests.Session()
        self.ua       = "glasgow-ietfdata/0.2.0"          # Update when making a new relaase
        self.base_url = "https://datatracker.ietf.org"
        self.pavlova = Pavlova()
        # Please sort the following alphabetically:
        self.pavlova.register_parser(AssignmentURI,        GenericParser(self.pavlova, AssignmentURI))
        self.pavlova.register_parser(DocumentAliasURI,     GenericParser(self.pavlova, DocumentAliasURI))
        self.pavlova.register_parser(DocumentAuthorURI,    GenericParser(self.pavlova, DocumentAuthorURI))
        self.pavlova.register_parser(DocumentEventURI,     GenericParser(self.pavlova, DocumentEventURI))
        self.pavlova.register_parser(DocumentStateURI,     GenericParser(self.pavlova, DocumentStateURI))
        self.pavlova.register_parser(DocumentStateTypeURI, GenericParser(self.pavlova, DocumentStateTypeURI))
        self.pavlova.register_parser(DocumentTypeURI,      GenericParser(self.pavlova, DocumentTypeURI))
        self.pavlova.register_parser(DocumentURI,          GenericParser(self.pavlova, DocumentURI))
        self.pavlova.register_parser(EmailURI,             GenericParser(self.pavlova, EmailURI))
        self.pavlova.register_parser(GroupStateURI,        GenericParser(self.pavlova, GroupStateURI))
        self.pavlova.register_parser(GroupURI,             GenericParser(self.pavlova, GroupURI))
        self.pavlova.register_parser(MeetingTypeURI,       GenericParser(self.pavlova, MeetingTypeURI))
        self.pavlova.register_parser(MeetingURI,           GenericParser(self.pavlova, MeetingURI))
        self.pavlova.register_parser(PersonAliasURI,       GenericParser(self.pavlova, PersonAliasURI))
        self.pavlova.register_parser(PersonEventURI,       GenericParser(self.pavlova, PersonEventURI))
        self.pavlova.register_parser(PersonURI,            GenericParser(self.pavlova, PersonURI))
        self.pavlova.register_parser(RelationshipTypeURI,  GenericParser(self.pavlova, RelationshipTypeURI))
        self.pavlova.register_parser(RelatedDocumentURI,   GenericParser(self.pavlova, RelatedDocumentURI))
        self.pavlova.register_parser(SessionURI,           GenericParser(self.pavlova, SessionURI))
        self.pavlova.register_parser(ScheduleURI,          GenericParser(self.pavlova, ScheduleURI))
        self.pavlova.register_parser(StreamURI,            GenericParser(self.pavlova, StreamURI))
        self.pavlova.register_parser(SubmissionCheckURI,   GenericParser(self.pavlova, SubmissionCheckURI))
        self.pavlova.register_parser(SubmissionEventURI,   GenericParser(self.pavlova, SubmissionEventURI))
        self.pavlova.register_parser(SubmissionURI,        GenericParser(self.pavlova, SubmissionURI))
        self.pavlova.register_parser(TimeslotURI,          GenericParser(self.pavlova, TimeslotURI))


    def __del__(self):
        self.session.close()


    def _retrieve(self, resource_uri: URI, obj_type: Type[T]) -> Optional[T]:
        headers = {'user-agent': self.ua}
        r = self.session.get(self.base_url + resource_uri.uri, headers=headers, verify=True, stream=False)
        if r.status_code == 200:
            return self.pavlova.from_mapping(r.json(), obj_type)
        else:
            print("_retrieve failed: {}".format(r.status_code))
            return None


    def _retrieve_multi(self, uri: str, obj_type: Type[T]) -> Iterator[T]:
        if "?" in uri:
            uri += "&limit=100"
        else:
            uri += "?limit=100"
        while uri is not None:
            headers = {'user-agent': self.ua}
            r = self.session.get(self.base_url + uri, headers=headers, verify=True, stream=False)
            if r.status_code == 200:
                meta = r.json()['meta']
                objs = r.json()['objects']
                uri  = meta['next']
                for obj in objs:
                    yield self.pavlova.from_mapping(obj, obj_type)
            else:
                print("_retrieve_multi failed: {}".format(r.status_code))
                print(r.status_code)
                return None


    # ----------------------------------------------------------------------------------------------------------------------------
    # Datatracker API endpoints returning information about people:
    # * https://datatracker.ietf.org/api/v1/person/person/
    # * https://datatracker.ietf.org/api/v1/person/person/20209/
    # * https://datatracker.ietf.org/api/v1/person/historicalperson/
    # * https://datatracker.ietf.org/api/v1/person/alias/

    def person(self, person_uri: PersonURI) -> Optional[Person]:
        return self._retrieve(person_uri, Person)


    def person_from_email(self, email_addr: str) -> Optional[Person]:
        email = self.email(EmailURI("/api/v1/person/email/" + email_addr + "/"))
        if email is not None:
            return self.person(email.person)
        else:
            return None


    def person_aliases(self, person: Person) -> Iterator[PersonAlias]:
        url = "/api/v1/person/alias/?person=" + str(person.id)
        return self._retrieve_multi(url, PersonAlias)


    def person_history(self, person: Person) -> Iterator[HistoricalPerson]:
        url = "/api/v1/person/historicalperson/?id=" + str(person.id)
        return self._retrieve_multi(url, HistoricalPerson)


    def person_events(self, person: Person) -> Iterator[PersonEvent]:
        url = "/api/v1/person/personevent/?person=" + str(person.id)
        return self._retrieve_multi(url, PersonEvent)


    def people(self,
            since : str ="1970-01-01T00:00:00",
            until : str ="2038-01-19T03:14:07",
            name_contains : Optional[str] =None) -> Iterator[Person]:
        """
        A generator that returns people recorded in the datatracker. As of April
        2018, there are approximately 21500 people recorded.

        Parameters:
            since         -- Only return people with timestamp after this
            until         -- Only return people with timestamp before this
            name_contains -- Only return peopls whose name containing this string

        Returns:
            An iterator, where each element is as returned by the person() method
        """
        url = "/api/v1/person/person/?time__gte=" + since + "&time__lt=" + until
        if name_contains is not None:
            url = url + "&name__contains=" + name_contains
        return self._retrieve_multi(url, Person)


    # ----------------------------------------------------------------------------------------------------------------------------
    # Datatracker API endpoints returning information about email addresses:
    # * https://datatracker.ietf.org/api/v1/person/email/csp@csperkins.org/
    # * https://datatracker.ietf.org/api/v1/person/historicalemail/

    def email(self, email_uri: EmailURI) -> Optional[Email]:
        return self._retrieve(email_uri, Email)


    def email_for_person(self, person: Person) -> Iterator[Email]:
        uri = "/api/v1/person/email/?person=" + str(person.id)
        return self._retrieve_multi(uri, Email)


    def email_history_for_address(self, email_addr: str) -> Iterator[HistoricalEmail]:
        uri = "/api/v1/person/historicalemail/?address=" + email_addr
        return self._retrieve_multi(uri, HistoricalEmail)


    def email_history_for_person(self, person: Person) -> Iterator[HistoricalEmail]:
        uri = "/api/v1/person/historicalemail/?person=" + str(person.id)
        return self._retrieve_multi(uri, HistoricalEmail)


    def emails(self,
               since : str ="1970-01-01T00:00:00",
               until : str ="2038-01-19T03:14:07") -> Iterator[Email]:
        """
        A generator that returns email addresses recorded in the datatracker.

        Parameters:
            since         -- Only return people with timestamp after this
            until         -- Only return people with timestamp before this

        Returns:
            An iterator, where each element is an Email object
        """
        url = "/api/v1/person/email/?time__gte=" + since + "&time__lt=" + until
        return self._retrieve_multi(url, Email)


    # ----------------------------------------------------------------------------------------------------------------------------
    # Datatracker API endpoints returning information about documents:
    # * https://datatracker.ietf.org/api/v1/doc/document/                        - list of documents
    # * https://datatracker.ietf.org/api/v1/doc/document/draft-ietf-avt-rtp-new/ - info about document

    def document(self, document_uri: DocumentURI) -> Optional[Document]:
        return self._retrieve(document_uri, Document)


    def documents(self,
            since   : str = "1970-01-01T00:00:00",
            until   : str = "2038-01-19T03:14:07",
            doctype : Optional[DocumentType] = None,
            group   : Optional[Group]        = None) -> Iterator[Document]:
        url = "/api/v1/doc/document/?time__gt=" + since + "&time__lt=" + until
        if doctype is not None:
            url = url + "&type=" + doctype.slug
        if group is not None:
            url = url + "&group=" + str(group.id)
        return self._retrieve_multi(url, Document)


    # Datatracker API endpoints returning information about document aliases:
    # * https://datatracker.ietf.org/api/v1/doc/docalias/?name=/                 - draft that became the given RFC

    def docaliases_from_name(self, alias: str) -> Iterator[DocumentAlias]:
        """
        Returns a list of DocumentAlias objects that correspond to the specified name.

        Parameters:
            name -- The name to lookup, for example "rfc3550", "std68", "bcp25", "draft-ietf-quic-transport"

        Returns:
            A list of DocumentAlias objects
        """
        url = "/api/v1/doc/docalias/?name=" + alias
        return self._retrieve_multi(url, DocumentAlias)


    def document_from_draft(self, draft: str) -> Optional[Document]:
        """
        Returns the document with the specified name.

        Parameters:
            name -- The name of the document to lookup (e.g, "draft-ietf-avt-rtp-new")

        Returns:
            A Document object
        """
        assert draft.startswith("draft-")
        docs = list(self.docaliases_from_name(draft))
        if len(docs) == 0:
            return None
        elif len(docs) == 1:
            return self.document(docs[0].document)
        else:
            raise RuntimeError


    def document_from_rfc(self, rfc: str) -> Optional[Document]:
        """
        Returns the document that became the specified RFC.

        Parameters:
            rfc -- The RFC to lookup (e.g., "rfc3550" or "RFC3550")

        Returns:
            A Document object
        """
        assert rfc.lower().startswith("rfc")
        docs = list(self.docaliases_from_name(rfc.lower()))
        if len(docs) == 0:
            return None
        elif len(docs) == 1:
            return self.document(docs[0].document)
        else:
            raise RuntimeError


    def documents_from_bcp(self, bcp: str) -> Iterator[Document]:
        """
        Returns the document that became the specified BCP.

        Parameters:
            bcp -- The BCP to lookup (e.g., "bcp205" or "BCP205")

        Returns:
            A list of Document objects
        """
        assert bcp.lower().startswith("bcp")
        for alias in self.docaliases_from_name(bcp.lower()):
            doc = self.document(alias.document)
            if doc is not None:
                yield doc


    def documents_from_std(self, std: str) -> Iterator[Document]:
        """
        Returns the document that became the specified STD.

        Parameters:
            std -- The STD to lookup (e.g., "std68" or "STD68")

        Returns:
            A list of Document objects
        """
        assert std.lower().startswith("std")
        for alias in self.docaliases_from_name(std.lower()):
            doc = self.document(alias.document)
            if doc is not None:
                yield doc


    # Datatracker API endpoints returning information about document states:
    # * https://datatracker.ietf.org/api/v1/doc/state/                           - Types of state a document can be in
    # * https://datatracker.ietf.org/api/v1/doc/statetype/                       - Possible types of state for a document

    def document_state(self, state_uri: DocumentStateURI) -> Optional[DocumentState]:
        return self._retrieve(state_uri, DocumentState)


    def document_states(self, statetype : Optional[str] = None) -> Iterator[DocumentState]:
        """
        A generator returning the possible states a document can be in.

        Parameters:
           statetype -- The 'slug' field from one of the dicts returned by the
                        document_state_types() method; constrains the results
                        to that particular state type.

        Returns:
            A sequence of Document objects, as returned by document_state()
        """
        url   = "/api/v1/doc/state/"
        if statetype is not None:
            url = url + "?type=" + statetype
        return self._retrieve_multi(url, DocumentState)


    def document_state_types(self) -> Iterator[DocumentStateType]:
        """
        A generator returning possible state types for a document.
        These are the possible values of the 'type' field in the
        output of document_state(), or the statetype parameter to
        document_states().

        Returns:
           A sequence of StateType objects
        """
        return self._retrieve_multi("/api/v1/doc/statetype/", DocumentStateType)


    # Datatracker API endpoints returning information about document events:
    #   https://datatracker.ietf.org/api/v1/doc/docevent/                        - list of document events
    #   https://datatracker.ietf.org/api/v1/doc/docevent/?doc=...                - events for a document
    # * https://datatracker.ietf.org/api/v1/doc/docevent/?by=...                 - events by a person (as /api/v1/person/person)
    # * https://datatracker.ietf.org/api/v1/doc/docevent/?time=...               - events by time

    def document_event(self, event_uri : DocumentEventURI) -> Optional[DocumentEvent]:
        return self._retrieve(event_uri, DocumentEvent)


    def document_events(self,
                        since      : str = "1970-01-01T00:00:00",
                        until      : str = "2038-01-19T03:14:07",
                        by         : PersonURI            = None,
                        desc       : str                  = None,
                        rev        : int                  = None,
                        event_type : str                  = None) -> Iterator[DocumentEvent]:
        """
        A generator returning information about document events.

        Parameters:
            since      -- Only return document events with timestamp after this
            until      -- Only return document events with timestamp after this
            by         -- Only return document events by this person
            desc       -- Only return document events with this description
            rev        -- Only return document events with this revision number
            event_type -- Only return document events with this type

        Returns:
           A sequence of DocumentEvent objects
        """
        url = "/api/v1/doc/docevent/?time__gt=" + since + "&time__lt=" + until
        if by is not None:
            url +=  "&by=" + str(by)
        if desc is not None:
            url += "&desc=" + str(desc)
        if rev is not None:
            url += "&rev=" + str(rev)
        if event_type is not None:
            url += "&type=" + str(event_type)
        return self._retrieve_multi(url, DocumentEvent)


    # * https://datatracker.ietf.org/api/v1/doc/documentauthor/?document=...     - authors of a document
    # * https://datatracker.ietf.org/api/v1/doc/documentauthor/?person=...       - documents by person
    # * https://datatracker.ietf.org/api/v1/doc/documentauthor/?email=...        - documents by person

    def document_authors(self, document : Document) -> Iterator[DocumentAuthor]:
        url = "/api/v1/doc/documentauthor/?document=" + str(document.id)
        return self._retrieve_multi(url, DocumentAuthor)


    def documents_authored_by_person(self, person : Person) -> Iterator[DocumentAuthor]:
        url = "/api/v1/doc/documentauthor/?person=" + str(person.id)
        return self._retrieve_multi(url, DocumentAuthor)


    def documents_authored_by_email(self, email : Email) -> Iterator[DocumentAuthor]:
        url = "/api/v1/doc/documentauthor/?email=" + email.address
        return self._retrieve_multi(url, DocumentAuthor)


    #   https://datatracker.ietf.org/api/v1/doc/dochistory/
    #   https://datatracker.ietf.org/api/v1/doc/dochistoryauthor/
    #   https://datatracker.ietf.org/api/v1/doc/docreminder/
    #   https://datatracker.ietf.org/api/v1/doc/documenturl/
    #   https://datatracker.ietf.org/api/v1/doc/statedocevent/                   - subset of /api/v1/doc/docevent/; same parameters
    #   https://datatracker.ietf.org/api/v1/doc/ballotdocevent/                  -               "                "
    #   https://datatracker.ietf.org/api/v1/doc/newrevisiondocevent/             -               "                "
    #   https://datatracker.ietf.org/api/v1/doc/submissiondocevent/              -               "                "
    #   https://datatracker.ietf.org/api/v1/doc/writeupdocevent/                 -               "                "
    #   https://datatracker.ietf.org/api/v1/doc/consensusdocevent/               -               "                "
    #   https://datatracker.ietf.org/api/v1/doc/ballotpositiondocevent/          -               "                "
    #   https://datatracker.ietf.org/api/v1/doc/reviewrequestdocevent/           -               "                "
    #   https://datatracker.ietf.org/api/v1/doc/lastcalldocevent/                -               "                "
    #   https://datatracker.ietf.org/api/v1/doc/telechatdocevent/                -               "                "
    #   https://datatracker.ietf.org/api/v1/doc/relateddocument/?source=...      - documents that source draft relates to (references, replaces, etc)
    #   https://datatracker.ietf.org/api/v1/doc/relateddocument/?target=...      - documents that relate to target draft
    #   https://datatracker.ietf.org/api/v1/doc/ballottype/                      - Types of ballot that can be issued on a document
    #   https://datatracker.ietf.org/api/v1/doc/relateddochistory/
    #   https://datatracker.ietf.org/api/v1/doc/initialreviewdocevent/
    #   https://datatracker.ietf.org/api/v1/doc/deletedevent/
    #   https://datatracker.ietf.org/api/v1/doc/addedmessageevent/
    #   https://datatracker.ietf.org/api/v1/doc/editedauthorsdocevent/

    def submission(self, submission_uri: SubmissionURI) -> Optional[Submission]:
        return self._retrieve(submission_uri, Submission)


    def submission_event(self, event_uri: SubmissionEventURI) -> Optional[SubmissionEvent]:
        return self._retrieve(event_uri, SubmissionEvent)


    def submission_events(self,
                        since      : str = "1970-01-01T00:00:00",
                        until      : str = "2038-01-19T03:14:07",
                        by         : Optional[PersonURI]     = None,
                        submission : Optional[SubmissionURI] = None,
                        desc       : Optional[str]           = None) -> Iterator[SubmissionEvent]:
        """
        A generator returning information about submission events.

        Parameters:
            since      -- Only return submission events with timestamp after this
            until      -- Only return submission events with timestamp after this
            by         -- Only return submission events by this person
            submission -- Only return submission events about this submission
            desc       -- Only return submission events with this description

        Returns:
           A sequence of SubmissionEvent objects
        """
        url = "/api/v1/submit/submissionevent/?time__gt=" + since + "&time__lt=" + until
        if by is not None:
            url +=  "&by=" + str(by)
        if submission is not None:
            url += "&submission=" + str(submission)
        if desc is not None:
            url += "&desc=" + str(desc)
        return self._retrieve_multi(url, SubmissionEvent)


    # Datatracker API endpoints returning information about names:
    # * https://datatracker.ietf.org/api/v1/name/doctypename/
    # * https://datatracker.ietf.org/api/v1/name/streamname/
    #   https://datatracker.ietf.org/api/v1/name/dbtemplatetypename/
    #   https://datatracker.ietf.org/api/v1/name/docrelationshipname/
    #   https://datatracker.ietf.org/api/v1/name/doctagname/
    #   https://datatracker.ietf.org/api/v1/name/docurltagname/
    #   https://datatracker.ietf.org/api/v1/name/formallanguagename/
    #   https://datatracker.ietf.org/api/v1/name/timeslottypename/
    #   https://datatracker.ietf.org/api/v1/name/liaisonstatementeventtypename/
    #   https://datatracker.ietf.org/api/v1/name/stdlevelname/
    #   https://datatracker.ietf.org/api/v1/name/ballotpositionname/
    #   https://datatracker.ietf.org/api/v1/name/reviewrequeststatename/
    #   https://datatracker.ietf.org/api/v1/name/groupmilestonestatename/
    #   https://datatracker.ietf.org/api/v1/name/iprlicensetypename/
    #   https://datatracker.ietf.org/api/v1/name/feedbacktypename/
    #   https://datatracker.ietf.org/api/v1/name/reviewtypename/
    #   https://datatracker.ietf.org/api/v1/name/iprdisclosurestatename/
    #   https://datatracker.ietf.org/api/v1/name/reviewresultname/
    #   https://datatracker.ietf.org/api/v1/name/liaisonstatementstate/
    #   https://datatracker.ietf.org/api/v1/name/roomresourcename/
    #   https://datatracker.ietf.org/api/v1/name/liaisonstatementtagname/
    #   https://datatracker.ietf.org/api/v1/name/topicaudiencename/
    #   https://datatracker.ietf.org/api/v1/name/continentname/
    #   https://datatracker.ietf.org/api/v1/name/nomineepositionstatename/
    #   https://datatracker.ietf.org/api/v1/name/importantdatename/
    #   https://datatracker.ietf.org/api/v1/name/liaisonstatementpurposename/
    #   https://datatracker.ietf.org/api/v1/name/constraintname/
    #   https://datatracker.ietf.org/api/v1/name/sessionstatusname/
    #   https://datatracker.ietf.org/api/v1/name/ipreventtypename/
    #   https://datatracker.ietf.org/api/v1/name/agendatypename/
    #   https://datatracker.ietf.org/api/v1/name/docremindertypename/
    #   https://datatracker.ietf.org/api/v1/name/intendedstdlevelname/
    #   https://datatracker.ietf.org/api/v1/name/countryname/
    #   https://datatracker.ietf.org/api/v1/name/grouptypename/
    #   https://datatracker.ietf.org/api/v1/name/draftsubmissionstatename/
    #   https://datatracker.ietf.org/api/v1/name/rolename/


    def document_type(self, doctype: str) -> Optional[DocumentType]:
        """
        Lookup information about a document type in the datatracker.

        Parameters:
            doctype : A document type slug (e.g., "draft").

        Returns:
            A DocumentType object
        """
        uri = DocumentTypeURI("/api/v1/name/doctypename/" + doctype + "/")
        return self._retrieve(uri, DocumentType)


    def document_types(self) -> Iterator[DocumentType]:
        return self._retrieve_multi("/api/v1/name/doctypename/", DocumentType)


    def stream(self, stream_uri: StreamURI) -> Optional[Stream]:
        return self._retrieve(stream_uri, Stream)


    def streams(self) -> Iterator[Stream]:
        return self._retrieve_multi("/api/v1/name/streamname/", Stream)


    # Datatracker API endpoints returning information about working groups:
    # * https://datatracker.ietf.org/api/v1/group/group/                               - list of groups
    # * https://datatracker.ietf.org/api/v1/group/group/2161/                          - info about group 2161
    #   https://datatracker.ietf.org/api/v1/group/grouphistory/?group=2161             - history
    #   https://datatracker.ietf.org/api/v1/group/groupurl/?group=2161                 - URLs
    #   https://datatracker.ietf.org/api/v1/group/groupevent/?group=2161               - events
    #   https://datatracker.ietf.org/api/v1/group/groupmilestone/?group=2161           - Current milestones
    #   https://datatracker.ietf.org/api/v1/group/groupmilestonehistory/?group=2161    - Previous milestones
    #   https://datatracker.ietf.org/api/v1/group/milestonegroupevent/?group=2161      - changed milestones
    #   https://datatracker.ietf.org/api/v1/group/role/?group=2161                     - The current WG chairs and ADs of a group
    #   https://datatracker.ietf.org/api/v1/group/role/?person=20209                   - Groups a person is currently involved with
    #   https://datatracker.ietf.org/api/v1/group/role/?email=csp@csperkins.org        - Groups a person is currently involved with
    #   https://datatracker.ietf.org/api/v1/group/rolehistory/?group=2161              - The previous WG chairs and ADs of a group
    #   https://datatracker.ietf.org/api/v1/group/rolehistory/?person=20209            - Groups person was previously involved with
    #   https://datatracker.ietf.org/api/v1/group/rolehistory/?email=csp@csperkins.org - Groups person was previously involved with
    #   https://datatracker.ietf.org/api/v1/group/changestategroupevent/?group=2161    - Group state changes
    #   https://datatracker.ietf.org/api/v1/group/groupstatetransitions                - ???

    def group(self, group_uri: GroupURI) -> Optional[Group]:
        return self._retrieve(group_uri, Group)


    def group_from_acronym(self, acronym: str) -> Optional[Group]:
        url    = "/api/v1/group/group/?acronym=" + acronym
        groups = list(self._retrieve_multi(url, Group))
        if len(groups) == 0:
            return None
        elif len(groups) == 1:
            return groups[0]
        else:
            raise RuntimeError


    def groups(self,
            since         : str                  = "1970-01-01T00:00:00",
            until         : str                  = "2038-01-19T03:14:07",
            name_contains : Optional[str]        = None,
            state         : Optional[GroupState] = None,
            parent        : Optional[Group]      = None) -> Iterator[Group]:
        url = "/api/v1/group/group/?time__gt=" + since + "&time__lt=" + until
        if name_contains is not None:
            url = url + "&name__contains=" + name_contains
        if state is not None:
            url = url + "&state=" + state.slug
        if parent is not None:
            url = url + "&parent=" + str(parent.id)
        return self._retrieve_multi(url, Group)

    # * https://datatracker.ietf.org/api/v1/name/groupstatename/

    def group_state(self, group_state : str) -> Optional[GroupState]:
        """
        Retrieve a GroupState

        Parameters:
           group_state -- The group state, as returned in the 'slug' of a GroupState
                           object. Valid group states include "abandon", "active",
                           "bof", "bof-conc", "conclude", "dormant", "proposed",
                           "replaced", and "unknown".

        Returns:
            A GroupState object
        """
        url  = GroupStateURI("/api/v1/name/groupstatename/" + group_state + "/")
        return self._retrieve(url, GroupState)


    def group_states(self) -> Iterator[GroupState]:
        url = "/api/v1/name/groupstatename/"
        return self._retrieve_multi(url, GroupState)


    # Datatracker API endpoints returning information about meetings:
    # * https://datatracker.ietf.org/api/v1/meeting/meeting/                        - list of meetings
    # * https://datatracker.ietf.org/api/v1/meeting/meeting/747/                    - information about meeting number 747
    #   https://datatracker.ietf.org/api/v1/meeting/session/                        - list of all sessions in meetings
    #   https://datatracker.ietf.org/api/v1/meeting/session/25886/                  - a session in a meeting
    #   https://datatracker.ietf.org/api/v1/meeting/session/?meeting=747            - sessions in meeting number 747
    #   https://datatracker.ietf.org/api/v1/meeting/session/?meeting=747&group=2161 - sessions in meeting number 747 for group 2161
    # * https://datatracker.ietf.org/api/v1/meeting/schedtimesessassignment/59003/  - a schededuled session within a meeting
    #   https://datatracker.ietf.org/api/v1/meeting/timeslot/9480/                  - a time slot within a meeting (time, duration, location)
    # * https://datatracker.ietf.org/api/v1/meeting/schedule/791/                   - a draft of the meeting agenda
    #   https://datatracker.ietf.org/api/v1/meeting/room/537/                       - a room at a meeting
    #   https://datatracker.ietf.org/api/v1/meeting/floorplan/14/                   - floor plan for a meeting venue
    #   https://datatracker.ietf.org/api/v1/meeting/schedulingevent/                - meetings being scheduled
    #
    #   https://datatracker.ietf.org/meeting/107/agenda.json
    #   https://datatracker.ietf.org/meeting/interim-2020-hrpc-01/agenda.json

    def meeting_session_assignment(self, assignment_uri : AssignmentURI) -> Optional[Assignment]:
        return self._retrieve(assignment_uri, Assignment)


    def meeting_session_assignments(self, schedule : Schedule) -> Iterator[Assignment]:
        """
        The assignment of sessions to timeslots in a particular version of the
        meeting schedule.
        """
        url = "/api/v1/meeting/schedtimesessassignment/?schedule=" + str(schedule.id)
        return self._retrieve_multi(url, Assignment)


    def meeting_schedule(self, schedule_uri : ScheduleURI) -> Optional[Schedule]:
        """
        Information about a particular version of the schedule for a meeting.

        Use `meeting_session_assignments()` to find what sessions are scheduled
        in each timeslot of the meeting in this version of the meeting schedule.
        """
        return self._retrieve(schedule_uri, Schedule)


    def meeting(self, meeting_uri : MeetingURI) -> Optional[Meeting]:
        """
        Information about a meeting.
        """
        return self._retrieve(meeting_uri, Meeting)


    def meetings(self,
            start_date   : str = "1970-01-01",
            end_date     : str = "2038-01-19",
            meeting_type : Optional[MeetingType] = None) -> Iterator[Meeting]:
        """
        Return information about meetings taking place within a particular date range.
        """
        url = "/api/v1/meeting/meeting/"
        url = url + "?date__gte=" + start_date + "&date__lte=" + end_date
        if meeting_type is not None:
            url = url + "&type=" + meeting_type.slug
        return self._retrieve_multi(url, Meeting)


    # * https://datatracker.ietf.org/api/v1/name/meetingtypename/

    def meeting_type(self, meeting_type: str) -> Optional[MeetingType]:
        """
        Retrieve a MeetingType

        Parameters:
           meeting_type -- The meeting type, as returned in the 'slug' of a MeetingType
                           object. Valid meeting types include "ietf" and "interim".

        Returns:
            A MeetingType object
        """
        url = MeetingTypeURI("/api/v1/name/meetingtypename/" + meeting_type + "/")
        return self._retrieve(url, MeetingType)


    def meeting_types(self) -> Iterator[MeetingType]:
        """
        A generator returning the possible meeting types

        Parameters:
           None

        Returns:
            An iterator of MeetingType objects
        """
        return self._retrieve_multi("/api/v1/name/meetingtypename/", MeetingType)

# =================================================================================================================================
#   https://datatracker.ietf.org/api/v1/doc/relateddocument/?source=...      - documents that source draft relates to (references, replaces, etc)
#   https://datatracker.ietf.org/api/v1/doc/relateddocument/?target=...      - documents that relate to target draft

    def related_documents(self, 
        source               : Optional[Document]         = None, 
        target               : Optional[DocumentAlias]    = None, 
        relationship_type    : Optional[RelationshipType] = None) -> Iterator[RelatedDocument]:

        url = "/api/v1/doc/relateddocument/"
        if source is not None and target is not None and relationship_type is not None:
            url = url + "?source=" + str(source.id) + "&target=" + str(target.id) + "&relationship=" + relationship_type.slug
        elif source is not None and target is not None:
            url = url + "?source=" + str(source.id) + "&target=" + str(target.id)
        elif source is not None and relationship_type is not None:
            url = url + "?source=" + str(source.id) + "&relationship=" + relationship_type.slug
        elif target is not None and relationship_type is not None:
            url = url + "?target=" + str(target.id) + "&relationship=" + relationship_type.slug
        elif target is not None:
            url = url + "?target=" + str(target.id)
        elif source is not None:
            url = url + "?source=" + str(source.id)
        elif relationship_type is not None:
            url = url + "?relationship=" + relationship_type.slug
        return self._retrieve_multi(url, RelatedDocument)
    
    
    def relationship_type(self, relationship_type_uri: RelationshipTypeURI) -> Optional[RelationshipType]:
        """
        Retrieve a relationship type

        Parameters:
            relationship_type_uri -- The relationship type uri, 
            as found in the resource_uri of a relationship type.

        Returns:
            A RelationshipType object
        """

        return self._retrieve(relationship_type_uri, RelationshipType)


    def relationship_types(self) -> Iterator[RelationshipType]:
        """
        A generator returning the possible relationship types

        Parameters:
           None

        Returns:
            An iterator of RelationshipType objects
        """

        url = "/api/v1/name/docrelationshipname/"
        return self._retrieve_multi(url, RelationshipType)

# =================================================================================================================================
# vim: set tw=0 ai:
