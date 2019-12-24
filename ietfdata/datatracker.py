# Copyright (C) 2017-2019 University of Glasgow
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

T = TypeVar('T')

import glob
import json
import requests
import re

# =================================================================================================================================
# Classes to represent the JSON-serialised objects returned by the Datatracker API:

# ---------------------------------------------------------------------------------------------------------------------------------
# Types relating to email addresses:

@dataclass(frozen=True)
class Email:
    resource_uri : str # Suitable for use with DataTracker::email()
    person       : str # Suitable for use with DataTracker::person()
    address      : str # The email address
    time         : str
    origin       : str
    primary      : bool
    active       : bool

    def __post_init__(self) -> None:
        assert self.resource_uri.startswith("/api/v1/person/email/")
        assert self.person.startswith("/api/v1/person/person/")


@dataclass(frozen=True)
class HistoricalEmail(Email):
    history_change_reason : Optional[str]
    history_user          : Optional[str]
    history_id            : int
    history_type          : str
    history_date          : str

    def __post_init__(self) -> None:
        assert self.resource_uri.startswith("/api/v1/person/historicalemail/")

# ---------------------------------------------------------------------------------------------------------------------------------
# Types relating to people:

@dataclass(frozen=True)
class Person:
    resource_uri    : str # Suitable for use with DataTracker::person()
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

    def __post_init__(self) -> None:
        assert self.resource_uri.startswith("/api/v1/person/person/")


@dataclass(frozen=True)
class HistoricalPerson(Person):
    history_change_reason : Optional[str]
    history_user          : Optional[str]
    history_id            : int
    history_type          : str
    history_date          : str

    def __post_init__(self) -> None:
        assert self.resource_uri.startswith("/api/v1/person/historicalperson/")


@dataclass(frozen=True)
class PersonAlias:
    id                 : int
    resource_uri       : str # Suitable for use with DataTracker::person_aliases()
    person             : str # Suitable for use with DataTracker::person()
    name               : str

    def __post_init__(self) -> None:
        assert self.resource_uri.startswith("/api/v1/person/alias/")
        assert self.person.startswith("/api/v1/person/person/")


# ---------------------------------------------------------------------------------------------------------------------------------
# Types relating to documents:

@dataclass(frozen=True)
class Document:
    id                 : int
    resource_uri       : str           # Suitable for use with DataTracker::document()
    name               : str
    title              : str
    pages              : Optional[int]
    words              : Optional[int]
    time               : str
    notify             : str
    expires            : Optional[str]
    type               : str           # Suitable for use with DataTracker::document_type()
    rfc                : Optional[int] 
    rev                : str           # If `rfc` is not None, `rev` will point to the RFC publication notice
    abstract           : str
    internal_comments  : str
    order              : int
    note               : str
    ad                 : Optional[str] # Suitable for use with DataTracker::person()
    shepherd           : Optional[str] # Suitable for use with DataTracker::person()
    group              : Optional[str] # Suitable for use with DataTracker::group()
    stream             : Optional[str] # Suitable for use with DataTracker::stream()
    intended_std_level : Optional[str]
    std_level          : Optional[str]
    states             : List[str]     # Suitable for use with DataTracker::document_state()
    submissions        : List[str]     # Suitable for use with DataTracker::submission()
    tags               : List[str]
    uploaded_filename  : str
    external_url       : str

    def __post_init__(self) -> None:
        assert self.resource_uri.startswith("/api/v1/doc/document/")
        assert self.type.startswith("/api/v1/name/doctypename/")
        assert self.ad                 is None or self.ad.startswith("/api/v1/person/person/")
        assert self.shepherd           is None or self.shepherd.startswith("/api/v1/person/email/")
        assert self.stream             is None or self.stream.startswith("/api/v1/name/streamname/")
        assert self.group              is None or self.group.startswith("/api/v1/group/group/")
        assert self.intended_std_level is None or self.intended_std_level.startswith("/api/v1/name/intendedstdlevelname/")
        assert self.std_level          is None or self.std_level.startswith("/api/v1/name/stdlevelname/")
        for state in self.states:
            assert state.startswith("/api/v1/doc/state/")
        for submit in self.submissions:
            assert submit.startswith("/api/v1/submit/submission/")

    def document_url(self) -> str:
        if self.type == "/api/v1/name/doctypename/agenda/":
            # FIXME: This doesn't work for interim meetings
            # FIXME: This doesn't work for PDF agenda files
            mtg = self.name.split("-")[1]
            url = "https://datatracker.ietf.org/meeting/" + mtg + "/materials/" + self.uploaded_filename
        elif self.type == "/api/v1/name/doctypename/bluesheets/":
            mtg = self.name.split("-")[1]
            url = "https://www.ietf.org/proceedings/" + mtg + "/bluesheets/" + self.uploaded_filename
        elif self.type == "/api/v1/name/doctypename/charter/":
            url = "https://www.ietf.org/charter/"     + self.name + "-" + self.rev + ".txt"
        elif self.type == "/api/v1/name/doctypename/conflrev/":
            url = "https://www.ietf.org/cr/"          + self.name + "-" + self.rev + ".txt"
        elif self.type == "/api/v1/name/doctypename/draft/":
            url = "https://www.ietf.org/archive/id/"  + self.name + "-" + self.rev + ".txt"
        elif self.type == "/api/v1/name/doctypename/liaison/":
            url = "https://www.ietf.org/lib/dt/documents/LIAISON/" + self.uploaded_filename
        elif self.type == "/api/v1/name/doctypename/liai-att/":
            url = "https://www.ietf.org/lib/dt/documents/LIAISON/" + self.uploaded_filename
        elif self.type == "/api/v1/name/doctypename/minutes/":
            mtg = self.name.split("-")[1]
            url = "https://datatracker.ietf.org/meeting/" + mtg + "/materials/" + self.uploaded_filename
        elif self.type == "/api/v1/name/doctypename/recording/":
            url = self.external_url
        elif self.type == "/api/v1/name/doctypename/review/":
            # FIXME: This points to the formatted HTML page containing the message, but we really want the raw message
            url = "https://datatracker.ietf.org/doc/" + self.name
        elif self.type == "/api/v1/name/doctypename/shepwrit/":
            url = self.external_url
        elif self.type == "/api/v1/name/doctypename/slides/":
            mtg = self.name.split("-")[1]
            url = "https://www.ietf.org/proceedings/" + mtg + "/slides/" + self.uploaded_filename
        elif self.type == "/api/v1/name/doctypename/statchg/":
            url = "https://www.ietf.org/sc/"          + self.name + "-" + self.rev + ".txt"
        else:
            raise NotImplementedError
        return url


@dataclass(frozen=True)
class DocumentAlias:
    id           : int
    resource_uri : str
    document     : str
    name         : str

    def __post_init__(self) -> None:
        assert self.resource_uri.startswith("/api/v1/doc/docalias/")
        assert self.document.startswith("/api/v1/doc/document/")


@dataclass(frozen=True)
class State:
    id           : int
    resource_uri : str
    desc         : str
    name         : str
    next_states  : List[str]
    order        : int
    slug         : str
    type         : str
    used         : bool

    def __post_init__(self) -> None:
        assert self.resource_uri.startswith("/api/v1/doc/state/")
        assert self.type.startswith("/api/v1/doc/statetype/")
        for state in self.next_states:
            assert state.startswith("/api/v1/doc/state/")


@dataclass(frozen=True)
class StateType:
    resource_uri : str
    label        : str
    slug         : str

    def __post_init__(self) -> None:
        assert self.resource_uri.startswith("/api/v1/doc/statetype/")


@dataclass(frozen=True)
class DocumentType:
    resource_uri : str
    name         : str
    used         : bool
    prefix       : str
    slug         : str
    desc         : str
    order        : int

    def __post_init__(self) -> None:
        assert self.resource_uri.startswith("/api/v1/name/doctypename/")


@dataclass(frozen=True)
class Stream:
    resource_uri : str
    name         : str
    desc         : str
    used         : bool
    slug         : str
    order        : int

    def __post_init__(self) -> None:
        assert self.resource_uri.startswith("/api/v1/name/streamname/")


@dataclass(frozen=True)
class Submission:
    abstract        : str
    access_key      : str
    auth_key        : str
    authors         : str
    checks          : List[str]
    document_date   : str
    draft           : str
    file_size       : int
    file_types      : str
    first_two_pages : str
    group           : str
    id              : int
    name            : str
    note            : str
    pages           : int
    remote_ip       : str
    replaces        : str
    resource_uri    : str
    rev             : str
    state           : str
    submission_date : str
    submitter       : str
    title           : str
    words           : Optional[int]

    def __post_init__(self) -> None:
        assert self.resource_uri.startswith("/api/v1/submit/submission/")
        assert self.state.startswith("/api/v1/name/draftsubmissionstatename/")
        assert self.group.startswith("/api/v1/group/group/")
        assert self.draft.startswith("/api/v1/doc/document/draft-")


# ---------------------------------------------------------------------------------------------------------------------------------
# Types relating to groups:

@dataclass(frozen=True)
class Group:
    acronym        : str
    ad             : Optional[str]
    charter        : str
    comments       : str
    description    : str
    id             : int
    list_archive   : str
    list_email     : str
    list_subscribe : str
    name           : str
    parent         : str
    resource_uri   : str
    state          : str
    time           : str
    type           : str
    unused_states  : List[str]
    unused_tags    : List[str]


@dataclass(frozen=True)
class GroupState:
    resource_uri   : str
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

@dataclass
class Meeting:
    resource_uri                     : str
    id                               : int
    type                             : str
    venue_name                       : str
    venue_addr                       : str
    reg_area                         : str
    time_zone                        : str
    acknowledgements                 : str
    agenda_info_note                 : str
    agenda_warning_note              : str
    updated                          : str
    idsubmit_cutoff_warning_days     : str
    idsubmit_cutoff_time_utc         : str
    idsubmit_cutoff_day_offset_00    : int
    idsubmit_cutoff_day_offset_01    : int
    submission_start_day_offset      : int
    submission_cutoff_day_offset     : int
    submission_correction_day_offset : int
    country                          : str
    city                             : str
    agenda                           : str
    number                           : str
    session_request_lock_message     : str
    break_area                       : str
    proceedings_final                : bool
    show_important_dates             : bool
    attendees                        : Optional[str]
    date                             : str
    days                             : int

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


@dataclass
class MeetingType:
    name         : str
    order        : int
    resource_uri : str
    slug         : str
    desc         : str
    used         : bool


# =================================================================================================================================
# A class to represent the datatracker:

class DataTracker:
    """
    A class for interacting with the IETF DataTracker.
    """
    def __init__(self):
        self.session  = requests.Session()
        self.base_url = "https://datatracker.ietf.org"


    def __del__(self):
        self.session.close()


    def _retrieve(self, uri: str, obj_type: Type[T]) -> Optional[T]:
        # FIXME: the datatracker has intermittent failures if we reuse connections,
        #        workaround by not using the session object to avoid reuse.
        response = requests.get(self.base_url + uri, verify=True)
        # response = self.session.get(self.base_url + uri, verify=True)
        if response.status_code == 200:
            return Pavlova().from_mapping(response.json(), obj_type)
        else:
            return None


    def _retrieve_multi(self, uri: str, obj_type: Type[T]) -> Iterator[T]:
        while uri is not None:
            # FIXME: the datatracker has intermittent failures if we reuse connections,
            #        workaround by not using the session object to avoid reuse.
            r = requests.get(self.base_url + uri, verify=True)
            # r = self.session.get(self.base_url + uri, verify=True)
            meta = r.json()['meta']
            objs = r.json()['objects']
            uri  = meta['next']
            for obj in objs:
                yield Pavlova().from_mapping(obj, obj_type)


    # ----------------------------------------------------------------------------------------------------------------------------
    # Datatracker API endpoints returning information about email addresses:
    # * https://datatracker.ietf.org/api/v1/person/email/csp@csperkins.org/
    # * https://datatracker.ietf.org/api/v1/person/historicalemail/

    def email(self, email_addr: str) -> Optional[Email]:
        uri = "/api/v1/person/email/" + email_addr + "/"
        return self._retrieve(uri, Email)


    def email_history_for_address(self, email_addr: str) -> Iterator[HistoricalEmail]:
        uri = "/api/v1/person/historicalemail/?address=" + email_addr
        return self._retrieve_multi(uri, HistoricalEmail)


    def email_history_for_person(self, person: Person) -> Iterator[HistoricalEmail]:
        uri = "/api/v1/person/historicalemail/?person=" + str(person.id)
        return self._retrieve_multi(uri, HistoricalEmail)


    # ----------------------------------------------------------------------------------------------------------------------------
    # Datatracker API endpoints returning information about people:
    # * https://datatracker.ietf.org/api/v1/person/person/
    # * https://datatracker.ietf.org/api/v1/person/person/20209/
    # * https://datatracker.ietf.org/api/v1/person/historicalperson/
    # * https://datatracker.ietf.org/api/v1/person/alias/


    def person(self, person_uri: str) -> Optional[Person]:
        if   person_uri.startswith("/api/v1/person/person/"):
            return self._retrieve(person_uri, Person)
        elif person_uri.startswith("/api/v1/person/email/"):
            email = self._retrieve(person_uri, Email)
            if email is not None:
                return self._retrieve(email.person, Person)
            else:
                return None
        else:
            raise RuntimeError


    def person_from_email(self, email_addr: str) -> Optional[Person]:
        return self.person("/api/v1/person/email/" + email_addr + "/")


    def person_aliases(self, person: Person) -> Iterator[PersonAlias]:
        url = "/api/v1/person/alias/?person=" + str(person.id)
        return self._retrieve_multi(url, PersonAlias)


    def person_history(self, person: Person) -> Iterator[HistoricalPerson]:
        url = "/api/v1/person/historicalperson/?id=" + str(person.id)
        return self._retrieve_multi(url, HistoricalPerson)


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
    # Datatracker API endpoints returning information about documents:
    # * https://datatracker.ietf.org/api/v1/doc/document/                        - list of documents
    # * https://datatracker.ietf.org/api/v1/doc/document/draft-ietf-avt-rtp-new/ - info about document

    def document(self, document_uri: str) -> Optional[Document]:
        assert document_uri.startswith("/api/v1/doc/document/")
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
            url = url + "&group=" + group.resource_uri
        return self._retrieve_multi(url, Document)


    # Datatracker API endpoints returning information about document aliases:
    # * https://datatracker.ietf.org/api/v1/doc/docalias/?name=/                 - draft that became the given RFC

    def documents_from_alias(self, alias: str) -> Iterator[DocumentAlias]:
        """
        Returns the documents that correspond to the specified alias.

        Parameters:
            alias -- The alias to lookup, for example "rfc3550", "std68", "bcp25", "draft-ietf-quic-transport"

        Returns:
            A list of Document objects
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
        docs = list(self.documents_from_alias(draft))
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
        docs = list(self.documents_from_alias(rfc.lower()))
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
        for alias in self.documents_from_alias(bcp.lower()):
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
        for alias in self.documents_from_alias(std.lower()):
            doc = self.document(alias.document)
            if doc is not None:
                yield doc


    # Datatracker API endpoints returning information about document states:
    # * https://datatracker.ietf.org/api/v1/doc/state/                           - Types of state a document can be in
    # * https://datatracker.ietf.org/api/v1/doc/statetype/                       - Possible types of state for a document

    def document_state(self, state_uri: str) -> Optional[State]:
        """
        Information about the state of a document.

        Parameters:
           state_uri -- A URI representing a document state, e.g., as returned
                        in the states entry of the dict returned by document()

        Returns:
            A State object
        """
        assert state_uri.startswith("/api/v1/doc/state/") and state_uri.endswith("/")
        return self._retrieve(state_uri, State)


    def document_states(self, statetype=None) -> Iterator[State]:
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
        return self._retrieve_multi(url, State)


    def document_state_types(self) -> Iterator[StateType]:
        """
        A generator returning possible state types for a document.
        These are the possible values of the 'type' field in the
        output of document_state(), or the statetype parameter to
        document_states().

        Returns:
           A sequence of StateType objects
        """
        return self._retrieve_multi("/api/v1/doc/statetype/", StateType)


    #   https://datatracker.ietf.org/api/v1/doc/docevent/                        - list of document events
    #   https://datatracker.ietf.org/api/v1/doc/docevent/?doc=...                - events for a document
    #   https://datatracker.ietf.org/api/v1/doc/docevent/?by=...                 - events by a person (as /api/v1/person/person)
    #   https://datatracker.ietf.org/api/v1/doc/docevent/?time=...               - events by time
    #   https://datatracker.ietf.org/api/v1/doc/documentauthor/?document=...     - authors of a document
    #   https://datatracker.ietf.org/api/v1/doc/documentauthor/?person=...       - documents by person (as /api/v1/person/person)
    #   https://datatracker.ietf.org/api/v1/doc/documentauthor/?email=...        - documents by person with particular email
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

    def submission(self, submission_uri: str) -> Optional[Submission]:
        """
        Information about a document submission.

        Parameters:
           submission_uri -- A submission URI of the form /api/v1/submit/submission/2402/

        Returns:
            A Submission object
        """

        assert submission_uri.startswith("/api/v1/submit/submission/")
        return self._retrieve(submission_uri, Submission)

    # Datatracker API endpoints returning information about names:
    # * https://datatracker.ietf.org/api/v1/name/doctypename/
    # * https://datatracker.ietf.org/api/v1/name/streamname/
    #   https://datatracker.ietf.org/api/v1/name/dbtemplatetypename/
    #   https://datatracker.ietf.org/api/v1/name/docrelationshipname/
    #   https://datatracker.ietf.org/api/v1/name/doctagname/
    #   https://datatracker.ietf.org/api/v1/name/docurltagname/
    #   https://datatracker.ietf.org/api/v1/name/groupstatename/
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
            doctype : Either a full document type URI (e.g., "/api/v1/name/doctypename/draft/")
                      or a document type slug (e.g., "draft").

        Returns:
            A DocumentType object
        """
        if doctype.startswith("/api/v1/name/doctypename/") and doctype.endswith("/"):
            doctype_uri = doctype
        else:
            doctype_uri = "/api/v1/name/doctypename/" + doctype + "/"
        return self._retrieve(doctype_uri, DocumentType)


    def document_types(self) -> Iterator[DocumentType]:
        """
        A generator returning possible document types.

        Parameters:
            none

        Returns:
            A sequence of DocumentType objects, as returned by document_type()
        """
        return self._retrieve_multi("/api/v1/name/doctypename/", DocumentType)


    def stream(self, stream_uri: str) -> Optional[Stream]:
        """
        Lookup information about a document stream in the datatracker.

        Parameters:
            stream_uri : a URI of the form, e.g., "/api/v1/name/streamname/.../"

        Returns:
            A Stream object
        """
        assert stream_uri.startswith("/api/v1/name/streamname/") and stream_uri.endswith("/")
        return self._retrieve(stream_uri, Stream)


    def streams(self) -> Iterator[Stream]:
        """
        A generator returning possible document streams.

        Parameters:
            none

        Returns:
            A sequence of Stream objects, as returned by stream()
        """
        return self._retrieve_multi("/api/v1/name/streamname/", Stream)


    # Datatracker API endpoints returning information about working groups:
    #   https://datatracker.ietf.org/api/v1/group/group/                               - list of groups
    #   https://datatracker.ietf.org/api/v1/group/group/2161/                          - info about group 2161
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

    def group(self, group_id: int) -> Optional[Group]:
        url  = "/api/v1/group/group/%d/" % (group_id)
        return self._retrieve(url, Group)


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
        """
        A generator that returns Group objects representing all groups recorded
        in the datatracker. The 'since' and 'until' parameters can be used to
        contrain the output to only entries with timestamps in a particular
        time range.
        If provided, 'name_contains' filters based on the whether the name field
        contains the specified value.
        If provided, 'state' filters based on group state (i.e., the values in the
        slug field of GroupState objects).
        if provided, 'parent' finds all groups that have the specified parent group.
        """
        url = "/api/v1/group/group/?time__gt=" + since + "&time__lt=" + until
        if name_contains is not None:
            url = url + "&name__contains=" + name_contains
        if state is not None:
            url = url + "&state=" + state.slug
        if parent is not None:
            url = url + "&parent=" + str(parent.id)
        return self._retrieve_multi(url, Group)


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
        url  = "/api/v1/name/groupstatename/" + group_state + "/"
        return self._retrieve(url, GroupState)


    def group_states(self) -> Iterator[GroupState]:
        """
        A generator returning possible group states.

        Parameters:
            none

        Returns:
            A sequence of Stream objects, as returned by stream()
        """
        url = "/api/v1/name/groupstatename/"
        return self._retrieve_multi(url, GroupState)


    # Datatracker API endpoints returning information about meetings:
    # * https://datatracker.ietf.org/api/v1/meeting/meeting/                        - list of meetings
    #   https://datatracker.ietf.org/api/v1/meeting/meeting/747/                    - information about meeting number 747
    #   https://datatracker.ietf.org/api/v1/meeting/session/                        - list of all sessions in meetings
    #   https://datatracker.ietf.org/api/v1/meeting/session/25886/                  - a session in a meeting
    #   https://datatracker.ietf.org/api/v1/meeting/session/?meeting=747            - sessions in meeting number 747
    #   https://datatracker.ietf.org/api/v1/meeting/session/?meeting=747&group=2161 - sessions in meeting number 747 for group 2161
    #   https://datatracker.ietf.org/api/v1/meeting/schedtimesessassignment/59003/  - a schededuled session within a meeting
    #   https://datatracker.ietf.org/api/v1/meeting/timeslot/9480/                  - a time slot within a meeting (time, duration, location)
    #   https://datatracker.ietf.org/api/v1/meeting/schedule/791/                   - a draft of the meeting agenda
    #   https://datatracker.ietf.org/api/v1/meeting/room/537/                       - a room at a meeting
    #   https://datatracker.ietf.org/api/v1/meeting/floorplan/14/                   - floor plan for a meeting venue
    # * https://datatracker.ietf.org/api/v1/name/meetingtypename/

    def meetings(self,
            since        : str = "1970-01-01",
            until        : str = "2038-01-19",
            meeting_type : Optional[MeetingType] = None) -> Iterator[Meeting]:
        """
        A generator returning information about meetings.

        Parameters:
           since        -- Only return meetings with date after this
           until        -- Only return meetings with date before this
           meeting_type -- If not None, constrain results to the specified MeetingType

        Returns:
            An iterator of Meeting objects
        """
        url = "/api/v1/meeting/meeting/?date__gt=" + since + "&date__lt=" + until
        if meeting_type is not None:
            url = url + "&type=" + meeting_type.slug
        return self._retrieve_multi(url, Meeting)


    def meeting_type(self, meeting_type: str) -> Optional[MeetingType]:
        """
        Retrieve a MeetingType

        Parameters:
           meeting_type -- The meeting type, as returned in the 'slug' of a MeetingType
                           object. Valid meeting types include "ietf" and "interim".

        Returns:
            A MeetingType object
        """
        url  = "/api/v1/name/meetingtypename/" + meeting_type + "/"
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
# vim: set tw=0 ai:
