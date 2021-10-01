# Copyright (C) 2017-2021 University of Glasgow
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
#   https://datatracker.ietf.org/api/v1/person/person/?time__gte=2018-03-27T14:07:36
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

from datetime    import datetime, timedelta, timezone
from enum        import Enum
from inspect     import signature
from typing      import List, Optional, Tuple, Dict, Iterator, Type, TypeVar, Any, Union, Generic, get_origin
from dataclasses import dataclass, field
from pathlib     import Path
from pavlova     import Pavlova
from pavlova.parsers import GenericParser
from pymongo         import MongoClient, ASCENDING, TEXT, ReplaceOne
from pymongo.database import Database

import ast
import copy
import dateutil.tz
import glob
import json
import logging
import os
import requests
import re
import sys
import time
import urllib.parse

# =================================================================================================================================
# Classes to represent the JSON-serialised objects returned by the Datatracker API:

# ---------------------------------------------------------------------------------------------------------------------------------
# URI types:

@dataclass(frozen=True)
class URI:
    uri    : Optional[str]
    root   : str = ""
    params : Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        if len(self.params) > 0:
            return F"{self.uri}?{urllib.parse.urlencode(self.params)}"
        else:
            return str(self.uri)

    def __post_init__(self) -> None:
        assert self.uri is None or self.uri.startswith(self.root)


@dataclass(frozen=True)
class DocumentURI(URI):
    root : str = "/api/v1/doc/document/"


@dataclass(frozen=True)
class GroupURI(URI):
    root : str = "/api/v1/group/group/"


# ---------------------------------------------------------------------------------------------------------------------------------
# Resource type

@dataclass(frozen=True)
class Resource:
    resource_uri : URI

T = TypeVar('T', bound=Resource)
R = TypeVar('R', bound=Type[Resource])


# ---------------------------------------------------------------------------------------------------------------------------------
# Types relating to people:

@dataclass(frozen=True)
class PersonURI(URI):
    root : str = "/api/v1/person/person/"


@dataclass(frozen=True)
class HistoricalPersonURI(URI):
    root : str = "/api/v1/person/historicalperson/"


@dataclass(frozen=True)
class Person(Resource):
    resource_uri    : PersonURI
    id              : int
    name            : str            # Full name in Unicode
    name_from_draft : str
    ascii           : str            # Name as rendered in ASCII
    # ascii_short: Fill in this with initials and surname only if taking the initials
    # and surname of the ASCII name above produces an incorrect initials-only form.
    ascii_short     : Optional[str]
    user            : str
    time            : datetime
    photo           : str
    photo_thumb     : str
    biography       : str
    consent         : bool
    # Plain name correction: Use this if you have a Spanish double surname.
    # Don't use this for nicknames, and don't use it unless you've actually
    # observed that the datatracker shows your name incorrectly."
    plain           : str


@dataclass(frozen=True)
class HistoricalPerson(Resource):
    resource_uri          : HistoricalPersonURI
    id                    : int
    name                  : str
    name_from_draft       : str
    ascii                 : str
    ascii_short           : Optional[str]
    user                  : str
    time                  : datetime
    photo                 : str
    photo_thumb           : str
    biography             : str
    consent               : bool
    history_change_reason : Optional[str]
    history_user          : Optional[str]
    history_id            : int
    history_type          : str
    history_date          : datetime
    plain                 : str


@dataclass(frozen=True)
class PersonAliasURI(URI):
    root : str = "/api/v1/person/alias/"


@dataclass(frozen=True)
class PersonAlias(Resource):
    id                 : int
    resource_uri       : PersonAliasURI
    person             : PersonURI
    name               : str


@dataclass(frozen=True)
class PersonEventURI(URI):
    root : str = "/api/v1/person/personevent/"


@dataclass(frozen=True)
class PersonEvent(Resource):
    desc            : str
    id              : int
    person          : PersonURI
    resource_uri    : PersonEventURI
    time            : datetime
    type            : str


# ---------------------------------------------------------------------------------------------------------------------------------
# Types relating to email addresses:

@dataclass(frozen=True)
class EmailURI(URI):
    root : str = "/api/v1/person/email/"


@dataclass(frozen=True)
class HistoricalEmailURI(URI):
    root : str = "/api/v1/person/historicalemail/"


@dataclass(frozen=True)
class Email(Resource):
    resource_uri : EmailURI
    person       : Optional[PersonURI]
    address      : str # The email address
    time         : datetime
    origin       : str
    primary      : bool
    active       : bool


@dataclass(frozen=True)
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

@dataclass(frozen=True)
class DocumentTypeURI(URI):
    root : str = "/api/v1/name/doctypename/"


@dataclass(frozen=True)
class DocumentType(Resource):
    resource_uri : DocumentTypeURI
    name         : str
    used         : bool
    prefix       : str
    slug         : str
    desc         : str
    order        : int


@dataclass(frozen=True)
class DocumentStateTypeURI(URI):
    root : str = "/api/v1/doc/statetype/"


@dataclass(frozen=True)
class DocumentStateType(Resource):
    resource_uri : DocumentStateTypeURI
    label        : str
    slug         : str


@dataclass(frozen=True)
class DocumentStateURI(URI):
    root : str = "/api/v1/doc/state/"


@dataclass(frozen=True)
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


@dataclass(frozen=True)
class StreamURI(URI):
    root : str = "/api/v1/name/streamname/"


@dataclass(frozen=True)
class Stream(Resource):
    resource_uri : StreamURI
    name         : str
    desc         : str
    used         : bool
    slug         : str
    order        : int


@dataclass(frozen=True)
class SubmissionURI(URI):
    root : str = "/api/v1/submit/submission/"


@dataclass(frozen=True)
class SubmissionCheckURI(URI):
    root : str = "/api/v1/submit/submissioncheck/"


@dataclass(frozen=True)
class Submission(Resource):
    abstract        : str
    access_key      : str
    auth_key        : str
    authors         : str   # See the parse_authors() method
    checks          : List[SubmissionCheckURI]
    document_date   : Optional[datetime]
    draft           : DocumentURI
    file_size       : Optional[int]
    file_types      : str   # e.g., ".txt,.xml"
    first_two_pages : str
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
    submission_date : datetime
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


@dataclass(frozen=True)
class SubmissionEventURI(URI):
    root : str = "/api/v1/submit/submissionevent/"


@dataclass(frozen=True)
class SubmissionEvent(Resource):
    by              : Optional[PersonURI]
    desc            : str
    id              : int
    resource_uri    : SubmissionEventURI
    submission      : SubmissionURI
    time            : datetime


# DocumentURI is defined earlier, to avoid circular dependencies

@dataclass(frozen=True)
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

    def url(self) -> str:
        # See https://trac.tools.ietf.org/tools/ietfdb/browser/trunk/ietf/settings.py and search for DOC_HREFS
        if self.type == DocumentTypeURI("/api/v1/name/doctypename/agenda/"):
            # FIXME: should be "/meeting/{meeting.number}/materials/{doc.name}-{doc.rev}" ???
            # FIXME: This doesn't work for interim meetings
            # FIXME: This doesn't work for PDF agenda files
            # FIXME: Older items are under, e.g., https://www.ietf.org/proceedings/90/agenda/agenda-90-precis.txt
            mtg = self.name.split("-")[1]
            # Recent documents are in the datatracker, older ones on the proceedings site
            url = "https://datatracker.ietf.org/meeting/" + mtg + "/materials/" + self.uploaded_filename
            url = "https://www.ietf.org/proceedings/" + mtg + "/agenda/" + self.uploaded_filename
        elif self.type == DocumentTypeURI("/api/v1/name/doctypename/bluesheets/"):
            # FIXME: should be "https://www.ietf.org/proceedings/{meeting.number}/bluesheets/{doc.uploaded_filename}" ???
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
            # Recent documents are in the datatracker, older ones on the proceedings site
            url = "https://datatracker.ietf.org/meeting/" + mtg + "/materials/" + self.uploaded_filename
            url = "https://www.ietf.org/proceedings/" + mtg + "/minutes/" + self.uploaded_filename
        elif self.type == DocumentTypeURI("/api/v1/name/doctypename/recording/"):
            url = self.external_url
        elif self.type == DocumentTypeURI("/api/v1/name/doctypename/review/"):
            # FIXME: This points to the formatted HTML page containing the message, but we really want the raw message
            url = "https://datatracker.ietf.org/doc/" + self.name
        elif self.type == DocumentTypeURI("/api/v1/name/doctypename/shepwrit/"):
            url = self.external_url
        elif self.type == DocumentTypeURI("/api/v1/name/doctypename/slides/"):
            # FIXME: should be https://www.ietf.org/slides/{doc.name}-{doc.rev} ???
            mtg = self.name.split("-")[1]
            url = "https://www.ietf.org/proceedings/" + mtg + "/slides/" + self.uploaded_filename
        elif self.type == DocumentTypeURI("/api/v1/name/doctypename/statchg/"):
            url = "https://www.ietf.org/sc/"          + self.name + "-" + self.rev + ".txt"
        else:
            raise NotImplementedError
        return url


@dataclass(frozen=True)
class DocumentAliasURI(URI):
    root : str = "/api/v1/doc/docalias/"


@dataclass(frozen=True)
class DocumentAlias(Resource):
    id           : int
    resource_uri : DocumentAliasURI
    document     : DocumentURI
    name         : str


@dataclass(frozen=True)
class DocumentEventURI(URI):
    root : str = "/api/v1/doc/docevent/"


@dataclass(frozen=True)
class DocumentEvent(Resource):
    by              : PersonURI
    desc            : str
    doc             : DocumentURI
    id              : int
    resource_uri    : DocumentEventURI
    rev             : str
    time            : datetime
    type            : str


@dataclass(frozen=True)
class BallotPositionNameURI(URI):
    root : str = "/api/v1/name/ballotpositionname/"


@dataclass(frozen=True)
class BallotPositionName(Resource):
    blocking     : bool
    desc         : Optional[str]
    name         : str
    order        : int
    resource_uri : BallotPositionNameURI
    slug         : str
    used         : bool


@dataclass(frozen=True)
class BallotTypeURI(URI):
    root : str = "/api/v1/doc/ballottype/"


@dataclass(frozen=True)
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


@dataclass(frozen=True)
class BallotDocumentEventURI(URI):
    root : str = "/api/v1/doc/ballotdocevent/"


@dataclass(frozen=True)
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


@dataclass(frozen=True)
class RelationshipTypeURI(URI):
    root : str = "/api/v1/name/docrelationshipname/"


@dataclass(frozen=True)
class RelationshipType(Resource):
    resource_uri   : RelationshipTypeURI
    slug           : str
    desc           : str
    name           : str
    used           : bool
    order          : int
    revname        : str


@dataclass(frozen=True)
class RelatedDocumentURI(URI):
    root : str = "/api/v1/doc/relateddocument/"


@dataclass(frozen=True)
class RelatedDocument(Resource):
    id              : int
    relationship    : RelationshipTypeURI
    resource_uri    : RelatedDocumentURI
    source          : DocumentURI
    target          : DocumentAliasURI


@dataclass(frozen=True)
class DocumentAuthorURI(URI):
    root : str = "/api/v1/doc/documentauthor/"


@dataclass(frozen=True)
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


@dataclass(frozen=True)
class GroupStateURI(URI):
    root : str = "/api/v1/name/groupstatename/"


@dataclass(frozen=True)
class GroupState(Resource):
    resource_uri   : GroupStateURI
    slug           : str
    desc           : str
    name           : str
    used           : bool
    order          : int


@dataclass(frozen=True)
class GroupTypeNameURI(URI):
    root : str = "/api/v1/name/grouptypename/"


@dataclass(frozen=True)
class GroupTypeName(Resource):
    desc          : str
    name          : str
    order         : int
    resource_uri  : GroupTypeNameURI
    slug          : str
    used          : bool
    verbose_name  : str


# GroupURI is defined earlier, to avoid circular dependencies


@dataclass(frozen=True)
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


@dataclass(frozen=True)
class GroupHistoryURI(URI):
    root : str = "/api/v1/group/grouphistory/"


@dataclass(frozen=True)
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


@dataclass(frozen=True)
class GroupEventURI(URI):
    root : str = "/api/v1/group/groupevent/"


@dataclass(frozen=True)
class GroupEvent(Resource):
    by           : PersonURI
    desc         : str
    group        : GroupURI
    id           : int
    resource_uri : GroupEventURI
    time         : datetime
    type         : str


@dataclass(frozen=True)
class GroupUrlURI(URI):
    root : str = "/api/v1/group/groupurl/"


@dataclass(frozen=True)
class GroupUrl(Resource):
    group        : GroupURI
    id           : int
    name         : str
    resource_uri : GroupUrlURI
    url          : str


@dataclass(frozen=True)
class GroupMilestoneStateNameURI(URI):
    root : str = "/api/v1/name/groupmilestonestatename/"


@dataclass(frozen=True)
class GroupMilestoneStateName(Resource):
    desc         : str
    name         : str
    order        : int
    resource_uri : GroupMilestoneStateNameURI
    slug         : str
    used         : bool


@dataclass(frozen=True)
class GroupMilestoneURI(URI):
    root : str = "/api/v1/group/groupmilestone/"


@dataclass(frozen=True)
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


@dataclass(frozen=True)
class RoleNameURI(URI):
    root : str = "/api/v1/name/rolename/"


@dataclass(frozen=True)
class RoleName(Resource):
    desc         : str
    name         : str
    order        : int
    resource_uri : RoleNameURI
    slug         : str
    used         : bool


@dataclass(frozen=True)
class GroupRoleURI(URI):
    root : str = "/api/v1/group/role/"


@dataclass(frozen=True)
class GroupRole(Resource):
    email        : EmailURI
    group        : GroupURI
    id           : int
    name         : RoleNameURI
    person       : PersonURI
    resource_uri : GroupRoleURI

@dataclass(frozen=True)
class GroupMilestoneHistoryURI(URI):
    root : str = "/api/v1/group/groupmilestonehistory/"


@dataclass(frozen=True)
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


@dataclass(frozen=True)
class GroupMilestoneEventURI(URI):
    root : str = "/api/v1/group/milestonegroupevent/"


@dataclass(frozen=True)
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


@dataclass(frozen=True)
class GroupRoleHistoryURI(URI):
    root : str = "/api/v1/group/rolehistory/"


@dataclass(frozen=True)
class GroupRoleHistory(Resource):
    email        : EmailURI
    group        : GroupHistoryURI
    id           : int
    name         : RoleNameURI
    person       : PersonURI
    resource_uri : GroupRoleHistoryURI


@dataclass(frozen=True)
class GroupStateChangeEventURI(URI):
    root : str = "/api/v1/group/changestategroupevent/"


@dataclass(frozen=True)
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


@dataclass(frozen=True)
class MeetingURI(URI):
    root : str = "/api/v1/meeting/meeting/"


@dataclass(frozen=True)
class MeetingTypeURI(URI):
    root : str = "/api/v1/name/meetingtypename/"


@dataclass(frozen=True)
class MeetingType(Resource):
    name         : str
    order        : int
    resource_uri : MeetingTypeURI
    slug         : str
    desc         : str
    used         : bool


@dataclass(frozen=True)
class ScheduleURI(URI):
    root : str = "/api/v1/meeting/schedule/"


@dataclass(frozen=True)
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
    badness      : Optional[str]
    notes        : str


@dataclass(frozen=True)
class Meeting(Resource):
    id                               : int
    resource_uri                     : MeetingURI
    type                             : MeetingTypeURI
    country                          : str
    city                             : str
    venue_name                       : str
    venue_addr                       : str
    date                             : datetime
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
    updated                          : datetime     # Time this record was modified

    def status(self) -> MeetingStatus:
        now = datetime.now()
        meeting_start = self.date
        meeting_end   = self.date + timedelta(days = self.days)
        if meeting_start > now:
            return MeetingStatus.FUTURE
        elif meeting_end < now:
            return MeetingStatus.COMPLETED
        else:
            return MeetingStatus.ONGOING


@dataclass(frozen=True)
class SessionURI(URI):
    root : str = "/api/v1/meeting/session/"


@dataclass(frozen=True)
class TimeslotURI(URI):
    root : str = "/api/v1/meeting/timeslot/"


@dataclass(frozen=True)
class Timeslot(Resource):
    id            : int
    resource_uri  : TimeslotURI
    type          : str               # FIXME: this is a URI "/api/v1/name/timeslottypename/regular/"
    meeting       : MeetingURI
    sessions      : List[SessionURI]  # Sessions assigned to this slot in various versions of the agenda; current assignment is last
    name          : str
    time          : datetime
    duration      : str               # FIXME: this should be a timedelta object
    location      : Optional[str]     # FIXME: this is a URI "/api/v1/meeting/room/668"
    show_location : bool
    modified      : datetime


@dataclass(frozen=True)
class SessionAssignmentURI(URI):
    root : str = "/api/v1/meeting/schedtimesessassignment/"


@dataclass(frozen=True)
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
    notes        : str
    pinned       : bool
    extendedfrom : Optional[str]
    badness      : int


@dataclass(frozen=True)
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


@dataclass(frozen=True)
class SessionStatusNameURI(URI):
    root : str = "/api/v1/name/sessionstatusname/"


@dataclass(frozen=True)
class SessionStatusName(Resource):
    order        : int
    slug         : str
    resource_uri : SessionStatusNameURI
    used         : bool
    desc         : str
    name         : str


@dataclass(frozen=True)
class SchedulingEventURI(URI):
    root : str = "/api/v1/meeting/schedulingevent/"


@dataclass(frozen=True)
class SchedulingEvent(Resource):
    id           : int
    session      : SessionURI
    status       : SessionStatusNameURI
    by           : PersonURI
    resource_uri : SchedulingEventURI
    time         : datetime


# ---------------------------------------------------------------------------------------------------------------------------------
# Types relating to IPR disclosures:

@dataclass(frozen=True)
class IPRDisclosureStateURI(URI):
    root : str = "/api/v1/name/iprdisclosurestatename/"


@dataclass(frozen=True)
class IPRDisclosureState(Resource):
    desc         : str
    name         : str
    order        : int
    resource_uri : IPRDisclosureStateURI
    slug         : str
    used         : bool


@dataclass(frozen=True)
class IPRDisclosureBaseURI(URI):
    root : str = "/api/v1/ipr/iprdisclosurebase/"


@dataclass(frozen=True)
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


@dataclass(frozen=True)
class GenericIPRDisclosureURI(URI):
    root : str = "/api/v1/ipr/genericiprdisclosure/"


@dataclass(frozen=True)
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


@dataclass(frozen=True)
class IPRLicenseTypeURI(URI):
    root : str = "/api/v1/name/iprlicensetypename/"


@dataclass(frozen=True)
class IPRLicenseType(Resource):
    desc         : str
    name         : str
    order        : int
    resource_uri : IPRLicenseTypeURI
    slug         : str
    used         : bool


@dataclass(frozen=True)
class HolderIPRDisclosureURI(URI):
    root : str = "/api/v1/ipr/holderiprdisclosure/"


@dataclass(frozen=True)
class HolderIPRDisclosure(Resource):
    by                                   : PersonURI
    compliant                            : bool
    docs                                 : List[DocumentAliasURI]
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


@dataclass(frozen=True)
class ThirdPartyIPRDisclosureURI(URI):
    root : str = "/api/v1/ipr/thirdpartyiprdisclosure/"


@dataclass(frozen=True)
class ThirdPartyIPRDisclosure(Resource):
    by                     : PersonURI
    compliant              : bool
    docs                   : List[DocumentAliasURI]
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

@dataclass(frozen=True)
class ReviewAssignmentStateURI(URI):
    root : str = "/api/v1/name/reviewassignmentstatename/"


@dataclass(frozen=True)
class ReviewAssignmentState(Resource):
    desc         : str
    name         : str
    order        : int
    resource_uri : ReviewAssignmentStateURI
    slug         : str
    used         : bool


@dataclass(frozen=True)
class ReviewResultTypeURI(URI):
    root : str = "/api/v1/name/reviewresultname/"


@dataclass(frozen=True)
class ReviewResultType(Resource):
    desc         : str
    name         : str
    order        : int
    resource_uri : ReviewResultTypeURI
    slug         : str
    used         : bool


@dataclass(frozen=True)
class ReviewTypeURI(URI):
    root : str = "/api/v1/name/reviewtypename/"


@dataclass(frozen=True)
class ReviewType(Resource):
    desc         : str
    name         : str
    order        : int
    resource_uri : ReviewTypeURI
    slug         : str
    used         : bool


@dataclass(frozen=True)
class ReviewRequestStateURI(URI):
    root : str = "/api/v1/name/reviewrequeststatename/"


@dataclass(frozen=True)
class ReviewRequestState(Resource):
    desc         : str
    name         : str
    order        : int
    resource_uri : ReviewRequestStateURI
    slug         : str
    used         : bool


@dataclass(frozen=True)
class ReviewRequestURI(URI):
    root : str = "/api/v1/review/reviewrequest/"


@dataclass(frozen=True)
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


@dataclass(frozen=True)
class ReviewAssignmentURI(URI):
    root : str = "/api/v1/review/reviewassignment/"


@dataclass(frozen=True)
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


@dataclass(frozen=True)
class ReviewWishURI(URI):
    root : str = "/api/v1/review/reviewwish/"


@dataclass(frozen=True)
class ReviewWish(Resource):
    doc          : DocumentURI
    id           : int
    person       : PersonURI
    resource_uri : ReviewWishURI
    team         : GroupURI
    time         : datetime


@dataclass(frozen=True)
class HistoricalUnavailablePeriodURI(URI):
    root : str = "/api/v1/review/historicalunavailableperiod/"


@dataclass(frozen=True)
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


@dataclass(frozen=True)
class HistoricalReviewRequestURI(URI):
    root : str = "/api/v1/review/historicalreviewrequest/"


@dataclass(frozen=True)
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


@dataclass(frozen=True)
class NextReviewerInTeamURI(URI):
    root : str = "/api/v1/review/nextreviewerinteam/"


@dataclass(frozen=True)
class NextReviewerInTeam(Resource):
    id            : int
    next_reviewer : PersonURI
    resource_uri  : NextReviewerInTeamURI
    team          : GroupURI


@dataclass(frozen=True)
class ReviewTeamSettingsURI(URI):
    root : str = "/api/v1/review/reviewteamsettings/"


@dataclass(frozen=True)
class ReviewTeamSettings(Resource):
    autosuggest                         : bool
    group                               : GroupURI
    id                                  : int
    notify_ad_when                      : List[ReviewResultTypeURI]
    remind_days_unconfirmed_assignments : Optional[int]
    resource_uri                        : ReviewTeamSettingsURI
    review_results                      : List[ReviewResultTypeURI]
    review_types                        : List[ReviewTypeURI]
    secr_mail_alias                     : str


@dataclass(frozen=True)
class ReviewerSettingsURI(URI):
    root : str = "/api/v1/review/reviewersettings/"


@dataclass(frozen=True)
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


@dataclass(frozen=True)
class UnavailablePeriodURI(URI):
    root : str = "/api/v1/review/unavailableperiod/"


@dataclass(frozen=True)
class UnavailablePeriod(Resource):
    availability : str
    end_date     : str
    id           : int
    person       : PersonURI
    reason       : str
    resource_uri : UnavailablePeriodURI
    start_date   : Optional[str]
    team         : GroupURI


@dataclass(frozen=True)
class HistoricalReviewerSettingsURI(URI):
    root : str = "/api/v1/review/historicalreviewersettings/"


@dataclass(frozen=True)
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


@dataclass(frozen=True)
class HistoricalReviewAssignmentURI(URI):
    root : str = "/api/v1/review/historicalreviewassignment/"


@dataclass(frozen=True)
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


@dataclass(frozen=True)
class ReviewSecretarySettingsURI(URI):
    root : str = "/api/v1/review/reviewsecretarysettings/"


@dataclass(frozen=True)
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

@dataclass(frozen=True)
class EmailListURI(URI):
    root : str = "/api/v1/mailinglists/list/"


@dataclass(frozen=True)
class EmailList(Resource):
    id           : int
    resource_uri : EmailListURI
    name         : str
    description  : str
    advertised   : bool


@dataclass(frozen=True)
class EmailListSubscriptionsURI(URI):
    root : str = "/api/v1/mailinglists/subscribed/"


@dataclass(frozen=True)
class EmailListSubscriptions(Resource):
    id           : int
    resource_uri : EmailListSubscriptionsURI
    email        : str
    lists        : List[EmailListURI]
    time         : datetime


# ---------------------------------------------------------------------------------------------------------------------------------
# Types relating to places:

@dataclass(frozen=True)
class ContinentURI(URI):
    root : str = "/api/v1/name/continentname/"


@dataclass(frozen=True)
class Continent(Resource):
    resource_uri : ContinentURI
    desc         : str
    order        : int
    name         : str
    used         : bool
    slug         : str


@dataclass(frozen=True)
class CountryURI(URI):
    root : str = "/api/v1/name/countryname/"


@dataclass(frozen=True)
class Country(Resource):
    resource_uri : CountryURI
    desc         : str
    slug         : str
    in_eu        : bool
    order        : int
    used         : bool
    name         : str
    continent    : ContinentURI


@dataclass(frozen=True)
class CountryAliasURI(URI):
    root : str = "/api/v1/stats/countryalias/"


@dataclass(frozen=True)
class CountryAlias(Resource):
    id           : int
    resource_uri : CountryAliasURI
    country      : CountryURI
    alias        : str


# ---------------------------------------------------------------------------------------------------------------------------------
# Types relating to statistics:

@dataclass(frozen=True)
class MeetingRegistrationURI(URI):
    root : str = "/api/v1/stats/meetingregistration/"


@dataclass(frozen=True)
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


# ---------------------------------------------------------------------------------------------------------------------------------
# Types relating to messages:


@dataclass(frozen=True)
class AnnouncementFromURI(URI):
    root : str = "/api/v1/message/announcementfrom/"


@dataclass(frozen=True)
class AnnouncementFrom(Resource):
    address      : str
    group        : GroupURI
    id           : int
    name         : RoleNameURI
    resource_uri : AnnouncementFromURI


@dataclass(frozen=True)
class MessageURI(URI):
    root : str = "/api/v1/message/message/"


@dataclass(frozen=True)
class Message(Resource):
    bcc            : str
    body           : str
    by             : PersonURI
    cc             : str
    content_type   : str
    frm            : str
    id             : int
    msgid          : str
    related_docs   : List[DocumentURI]
    related_groups : List[GroupURI]
    reply_to       : str
    resource_uri   : MessageURI
    sent           : datetime
    subject        : str
    time           : datetime
    to             : str


@dataclass(frozen=True)
class SendQueueURI(URI):
    root : str = "/api/v1/message/sendqueue/"


@dataclass(frozen=True)
class SendQueueEntry(Resource):
    by             : PersonURI
    id             : int
    message        : MessageURI
    note           : str
    resource_uri   : SendQueueURI
    send_at        : Optional[datetime]
    sent_at        : Optional[datetime]
    time           : datetime


# =================================================================================================================================
# A class to represent the datatracker:

def _parent_uri(uri: URI) -> URI:
    assert uri.uri is not None and uri.uri.startswith("/api/v1/")
    sep0 = 8
    sep1 = uri.uri[sep0:].find("/") + sep0 + 1
    sep2 = uri.uri[sep1:].find("/") + sep1 + 1
    return type(uri)(uri.uri[:sep2])


def _db_collection(uri: URI) -> str:
    assert uri.uri is not None
    return uri.uri.strip('/').replace("/", "_")


def _translate_query(uri: URI, obj_type: Type[T]) -> Dict[Any, Any]:
    translated_params : Dict[Any, Any] = {}

    for (param, value) in uri.params.items():
        #print(F"_translate_query: param={param} value={value}")
        if "__gte" in param:
            param = param[:-5]
            translated_params[param] = {**translated_params.get(param, {}), "$gte": value}
        elif "__gt" in param:
            param = param[:-4]
            translated_params[param] = {**translated_params.get(param, {}), "$gt": value}
        elif "__lte" in param:
            param = param[:-5]
            translated_params[param] = {**translated_params.get(param, {}), "$lte": value}
        elif "__lt" in param:
            param = param[:-4]
            translated_params[param] = {**translated_params.get(param, {}), "$lt": value}
        elif "__contains" in param:
            param = param[:-10]
            translated_params[param] = {**translated_params.get(param, {}), "$regex": value}
        else:
            param_type = obj_type.__dict__["__dataclass_fields__"][param].type
            if get_origin(param_type) is Union:
                param_type = param_type.__args__[0]
            if get_origin(param_type) is list:
                param_type = param_type.__args__[0]
            if issubclass(param_type, URI):
                if isinstance(value, str) and value.startswith(param_type.root):
                    translated_params[param] = value
                else:
                    translated_params[param] = f"{param_type.root}{value}/"
            else:
                translated_params[param] = value
        #print(F"translated = {translated_params[param]}")
    return translated_params


def _sort_objs(obj: Tuple[str,Dict[Any, Any]]) -> str:
    key, _ = obj
    return key


@dataclass
class CacheMetadata:
    created     : datetime
    updated     : datetime
    partial     : bool
    total_count : int
    queries     : List[str]


@dataclass
class Hints(Generic[T]):
    obj_type :  Type[T]
    sort_by : str
    update_strategy : str
    deref   : Dict[str, str]


class DataTracker:
    """
    A class for interacting with the IETF DataTracker.
    """
    def __init__(self,
            use_cache: bool = False,
            mongodb_hostname: str = "localhost",
            mongodb_port: int = 27017,
            mongodb_username: Optional[str] = None,
            mongodb_password: Optional[str] = None):
        if os.environ.get('IETFDATA_CACHE_HOST') is not None:
            use_cache = True
            cache_host = os.environ.get('IETFDATA_CACHE_HOST')
            cache_port = os.environ.get('IETFDATA_CACHE_PORT', 27017)
            cache_username = os.environ.get('IETFDATA_CACHE_USER')
            cache_password = os.environ.get('IETFDATA_CACHE_PASSWORD')
            if cache_host is not None:
                mongodb_hostname = cache_host
            if cache_port is not None:
                mongodb_port = int(cache_port)
            if cache_username is not None:
                mongodb_username = cache_username
            if cache_password is not None:
                mongodb_password = cache_password
        if use_cache:
            self.db : Optional[Database] = None
            if mongodb_username is not None:
                self.db = MongoClient(host=mongodb_hostname, port=mongodb_port, username=mongodb_username, password=mongodb_password).ietfdata
            else:
                self.db = MongoClient(host=mongodb_hostname, port=mongodb_port).ietfdata
        else:
            self.db    = None
        self.session   = requests.Session()
        self.ua        = "glasgow-ietfdata/0.5.1"          # Update when making a new relaase
        self.base_url  = "https://datatracker.ietf.org"
        self.http_req  = 0
        self.cache_req = 0
        self.cache_hit = 0
        self.cache_ver = "1" # Increment when changing cache architecture
        self.cache_update : Dict[str, datetime] = {}
        self.get_count = 0
        self.db_calls  = 0

        # Configure logging
        logging.basicConfig(level=os.environ.get("IETFDATA_LOGLEVEL", "INFO"))
        self.log      = logging.getLogger("ietfdata")
        if self.db is not None:
            self.log.info(f"{self.ua} (cache enabled)")
        else:
            self.log.info(f"{self.ua} (cache disabled)")

        # Register generic parsers for each URI type:
        self.pavlova = Pavlova()
        for uri_type in URI.__subclasses__():
            self.pavlova.register_parser(uri_type, GenericParser(self.pavlova, uri_type))
        self.pavlova.register_parser(CacheMetadata, GenericParser(self.pavlova, CacheMetadata))

        # Register cache hints:
        self._hints = {} # type: Dict[str, Hints]
        self._hints["/api/v1/doc/ballotdocevent/"]                 = Hints(BallotDocumentEvent, "id", "T", {"doc": "id"})
        self._hints["/api/v1/doc/ballottype/"]                     = Hints(BallotType, "slug", "V", {})
        self._hints["/api/v1/doc/docalias/"]                       = Hints(DocumentAlias, "id", "-", {})  # FIXME: no modification time
        self._hints["/api/v1/doc/docevent/"]                       = Hints(DocumentEvent, "id", "T", {"doc": "id"})
        self._hints["/api/v1/doc/document/"]                       = Hints(Document, "id", "T", {})
        self._hints["/api/v1/doc/documentauthor/"]                 = Hints(DocumentAuthor, "id", "R", {"document": "id"})
        self._hints["/api/v1/doc/relateddocument/"]                = Hints(RelatedDocument, "id", "-", {"source": "id", "target": "id", "relationship": "slug"}) # FIXME: no modification time, but will be updated when the corresponding `source` is updated
        self._hints["/api/v1/doc/state/"]                          = Hints(DocumentState, "id", "V", {})
        self._hints["/api/v1/doc/statetype/"]                      = Hints(DocumentStateType, "slug", "V", {})
        self._hints["/api/v1/group/changestategroupevent/"]        = Hints(GroupStateChangeEvent, "id", "T", {})
        self._hints["/api/v1/group/group/"]                        = Hints(Group, "id", "T", {})
        self._hints["/api/v1/group/groupevent/"]                   = Hints(GroupEvent, "id", "T", {})
        # FIXME: when a group, /api/v1/group/group/1861/, is updated, /api/v1/group/grouphistory/?group=1861 Resource
        # will be updated with an object with "time" equal to the previous modification time of the group.
        # For example, when the IRSG membership was changed on 2021-04-26, a grouphistory object with time
        # 2020-07-25 was added, representing the previous state of the group.
        self._hints["/api/v1/group/grouphistory/"]                 = Hints(GroupHistory, "id", "T", {})
        self._hints["/api/v1/group/groupmilestone/"]               = Hints(GroupMilestone, "id", "T", {})
        self._hints["/api/v1/group/groupmilestonehistory/"]        = Hints(GroupMilestoneHistory, "id", "T", {})
        self._hints["/api/v1/group/groupurl/"]                     = Hints(GroupUrl, "id", "-", {})  # FIXME: no modification time, but will be updated with the corresponding `group` is updated
        self._hints["/api/v1/group/milestonegroupevent/"]          = Hints(GroupMilestoneEvent, "id", "T", {})
        self._hints["/api/v1/group/role/"]                         = Hints(GroupRole, "id", "-", {})  # FIXME: no modification time, but will be updated with the corresponding `group` is updated
        self._hints["/api/v1/group/rolehistory/"]                  = Hints(GroupRoleHistory, "id", "-", {})  # FIXME: No modification time, but will be updated when the corresponding `grouphistory` is updated
        self._hints["/api/v1/ipr/genericiprdisclosure/"]           = Hints(GenericIPRDisclosure, "id", "T", {})
        self._hints["/api/v1/ipr/holderiprdisclosure/"]            = Hints(HolderIPRDisclosure, "id", "T", {})
        self._hints["/api/v1/ipr/iprdisclosurebase/"]              = Hints(IPRDisclosureBase, "id", "T", {})
        self._hints["/api/v1/ipr/thirdpartyiprdisclosure/"]        = Hints(ThirdPartyIPRDisclosure, "id", "T", {})
        self._hints["/api/v1/mailinglists/list/"]                  = Hints(EmailList, "id", "-", {})  # FIXME: no modification time
        self._hints["/api/v1/mailinglists/subscribed/"]            = Hints(EmailListSubscriptions, "id", "-", {})  # FIXME: these have a time field, but not clear updated
        self._hints["/api/v1/meeting/meeting/"]                    = Hints(Meeting, "id", "U", {})  # FIXME: has an `updated` field that doesn't allow filtering?
        self._hints["/api/v1/meeting/schedtimesessassignment/"]    = Hints(SessionAssignment, "id", "M", {})
        self._hints["/api/v1/meeting/schedule/"]                   = Hints(Schedule, "id", "-", {})  # FIXME: immutable once created?
        self._hints["/api/v1/meeting/schedulingevent/"]            = Hints(SchedulingEvent, "id", "T", {})
        self._hints["/api/v1/meeting/session/"]                    = Hints(Session, "id", "M", {})
        self._hints["/api/v1/meeting/timeslot/"]                   = Hints(Timeslot, "id", "M", {})
        self._hints["/api/v1/message/announcementfrom/"]           = Hints(AnnouncementFrom, "id", "V", {})
        self._hints["/api/v1/message/message/"]                    = Hints(Message, "id", "-", {"related_doc": "id"}) # No longer accessible
        self._hints["/api/v1/message/sendqueue/"]                  = Hints(SendQueueEntry, "id", "T", {})
        self._hints["/api/v1/name/ballotpositionname/"]            = Hints(BallotPositionName, "slug", "V", {})
        self._hints["/api/v1/name/docrelationshipname/"]           = Hints(RelationshipType, "slug", "V", {})
        self._hints["/api/v1/name/doctypename/"]                   = Hints(DocumentType, "slug", "V", {})
        self._hints["/api/v1/name/groupmilestonestatename/"]       = Hints(GroupMilestoneStateName, "slug", "V", {})
        self._hints["/api/v1/name/groupstatename/"]                = Hints(GroupState, "slug", "V", {})
        self._hints["/api/v1/name/grouptypename/"]                 = Hints(GroupTypeName, "slug", "V", {})
        self._hints["/api/v1/name/meetingtypename/"]               = Hints(MeetingType, "slug", "V", {})
        self._hints["/api/v1/name/iprdisclosurestatename/"]        = Hints(IPRDisclosureState, "slug", "V", {})
        self._hints["/api/v1/name/iprlicensetypename/"]            = Hints(IPRLicenseType, "slug", "V", {})
        self._hints["/api/v1/name/reviewassignmentstatename/"]     = Hints(ReviewAssignmentState, "slug", "V", {})
        self._hints["/api/v1/name/reviewresultname/"]              = Hints(ReviewResultType, "slug", "V", {})
        self._hints["/api/v1/name/reviewtypename/"]                = Hints(ReviewType, "slug", "V", {})
        self._hints["/api/v1/name/reviewrequeststatename/"]        = Hints(ReviewRequestState, "slug", "V", {})
        self._hints["/api/v1/name/rolename/"]                      = Hints(RoleName, "slug", "V", {})
        self._hints["/api/v1/name/sessionstatusname/"]             = Hints(SessionStatusName, "slug", "V", {})
        self._hints["/api/v1/name/streamname/"]                    = Hints(Stream, "slug", "V", {})
        self._hints["/api/v1/person/alias/"]                       = Hints(PersonAlias, "id", "-", {})    # FIXME: no modification time, but updated with the `person` is updated
        self._hints["/api/v1/person/email/"]                       = Hints(Email, "address", "T", {})
        self._hints["/api/v1/person/historicalemail/"]             = Hints(HistoricalEmail, "address", "H", {})
        self._hints["/api/v1/person/historicalperson/"]            = Hints(HistoricalPerson, "id", "H", {})
        self._hints["/api/v1/person/person/"]                      = Hints(Person, "id", "T", {})
        self._hints["/api/v1/person/personevent/"]                 = Hints(PersonEvent, "id", "T", {})
        self._hints["/api/v1/review/historicalreviewassignment/"]  = Hints(HistoricalReviewAssignment, "id", "C", {})
        self._hints["/api/v1/review/historicalreviewersettings/"]  = Hints(HistoricalReviewerSettings, "id", "H", {})
        self._hints["/api/v1/review/historicalreviewrequest/"]     = Hints(HistoricalReviewRequest, "id", "T", {"doc": "id"})
        self._hints["/api/v1/review/historicalunavailableperiod/"] = Hints(HistoricalUnavailablePeriod, "id", "-", {})
        self._hints["/api/v1/review/nextreviewerinteam/"]          = Hints(NextReviewerInTeam, "id", "-", {})
        self._hints["/api/v1/review/reviewassignment/"]            = Hints(ReviewAssignment, "id", "-", {})
        self._hints["/api/v1/review/reviewersettings/"]            = Hints(ReviewerSettings, "id", "-", {})
        self._hints["/api/v1/review/reviewrequest/"]               = Hints(ReviewRequest, "id", "T", {"doc": "id"})
        self._hints["/api/v1/review/reviewsecretarysettings/"]     = Hints(ReviewSecretarySettings, "id", "-", {})
        self._hints["/api/v1/review/reviewteamsettings/"]          = Hints(ReviewTeamSettings, "id", "-", {})
        self._hints["/api/v1/review/reviewwish/"]                  = Hints(ReviewWish, "id", "T", {"doc": "id"})
        self._hints["/api/v1/review/unavailableperiod/"]           = Hints(UnavailablePeriod, "id", "-", {})
        self._hints["/api/v1/name/continentname/"]                 = Hints(Continent, "slug", "V", {})
        self._hints["/api/v1/name/countryname/"]                   = Hints(Country, "slug", "V", {})
        self._hints["/api/v1/stats/countryalias/"]                 = Hints(CountryAlias, "id", "V", {})
        self._hints["/api/v1/stats/meetingregistration/"]          = Hints(MeetingRegistration, "id", "-", {})
        self._hints["/api/v1/submit/submission/"]                  = Hints(Submission, "id", "-", {})
        self._hints["/api/v1/submit/submissionevent/"]             = Hints(SubmissionEvent, "id", "T", {})

        # check Datatracker and cache versions
        self._cache_check_versions()


    def __del__(self):
        self.log.info(F"cache requests: {self.cache_req}")
        if self.cache_req == 0:
            self.log.info(F"cache hit rate: -")
        else:
            self.log.info(F"cache hit rate: {self.cache_hit / self.cache_req * 100.0:.1f}%")
        self.log.info(F"HTTP GET calls: {self.get_count}")
        self.log.info(F"db requests: {self.db_calls}")
        self.session.close()


    # ----------------------------------------------------------------------------------------------------------------------------
    # Private methods to access the datatracker.
    #
    # The _datatracker_get_single() and _datatracker_get_multi() functions
    # retrieve data from the IETF datatracker without using the cache. They are
    # used by the cache layer to access the datatracker when updating the cache,
    # and by the retrieval layer to retrieve objects from the datatracker if the
    # cache is disabled.

    def _datatracker_get_single(self, obj_uri: URI) -> Optional[Dict[str, Any]]:
        assert obj_uri.uri is not None
        retry_time  = 1.875
        while True:
            try:
                req_url     = self.base_url + obj_uri.uri
                req_headers = {'User-Agent': self.ua}
                req_params  = obj_uri.params
                self._rate_limit()
                self.get_count += 1
                r = self.session.get(req_url, params = req_params, headers = req_headers, verify = True, stream = False)
                if r.status_code == 200:
                    self.log.debug(F"_datatracker_get_single: ({r.status_code}) {obj_uri}")
                    url_obj = r.json() # type: Dict[str, Any]
                    return url_obj
                elif r.status_code == 404:
                    self.log.debug(F"_datatracker_get_single: ({r.status_code}) {obj_uri}")
                    return None
                else:
                    self.log.warning(F"_datatracker_get_single: error {r.status_code} {obj_uri} - retry in {retry_time}")
                    if retry_time > 60:
                        self.log.error(F"_datatracker_get_single: error - retry limit exceeded")
                        sys.exit(1)
                    self.session.close()
                    time.sleep(retry_time)
                    retry_time *= 2
            except requests.exceptions.ConnectionError:
                self.log.warning(F"_datatracker_get_single: connection error - retry in {retry_time}")
                if retry_time > 60:
                    self.log.error(F"_datatracker_get_single: error - retry limit exceeded")
                    sys.exit(1)
                self.session.close()
                time.sleep(retry_time)
                retry_time *= 2


    def _datatracker_get_multi(self, get_uri: URI, order_by: Optional[str] = None) -> Iterator[Dict[Any, Any]]:
        obj_uri = copy.deepcopy(get_uri)

        assert "order_by" not in obj_uri.params
        assert "limit"    not in obj_uri.params

        if order_by != None:
            obj_uri.params["order_by"] = order_by
        obj_uri.params[   "limit"] = 100

        total_count  = -1
        fetched_objs = {} # type: Dict[str, Dict[Any, Any]]
        while obj_uri.uri is not None:
            self._rate_limit()
            retry = True
            retry_time = 1.875
            while retry:
                retry = False
                req_url     = self.base_url + obj_uri.uri
                req_params  = obj_uri.params
                req_headers = {'User-Agent': self.ua}
                try:
                    self.get_count += 1
                    r = self.session.get(url = req_url, params = req_params, headers = req_headers, verify = True, stream = False)
                    if r.status_code == 200:
                        self.log.debug(F"_datatracker_get_multi ({r.status_code}) {obj_uri}")
                        meta = r.json()['meta']
                        objs = r.json()['objects']
                        obj_uri  = URI(meta['next'])
                        for obj in objs:
                            # API requests returning lists should never return duplicate
                            # objects, but due to datatracker bugs this sometimes happens.
                            # Check for and log such problems, but pass the duplicates up
                            # to the higher layers for reconcilition.
                            if obj["resource_uri"] in fetched_objs:
                                self.log.warning(F"_datatracker_get_multi duplicate object {obj['resource_uri']}")
                            else:
                                fetched_objs[obj["resource_uri"]] = obj
                            yield obj
                        total_count = meta["total_count"]
                    elif r.status_code == 500:
                        self.log.warning(F"_datatracker_get_multi ({r.status_code}) {obj_uri}")
                        if retry_time > 60:
                            self.log.info(F"_datatracker_get_multi retry time exceeded")
                            sys.exit(1)
                        self.session.close()
                        time.sleep(retry_time)
                        retry_time *= 2
                        retry = True
                    else:
                        self.log.error(F"_datatracker_get_multi ({r.status_code}) {obj_uri}")
                        sys.exit(1)
                except requests.exceptions.ConnectionError:
                    self.log.warning(F"_datatracker_get_multi: connection error - will retry in {retry_time}")
                    self.session.close()
                    time.sleep(retry_time)
                    retry_time *= 2
                    retry = True
        if total_count != len(fetched_objs):
            self.log.warning(F"_datatracker_get_multi: expected {total_count} objects but got {len(fetched_objs)}")


    def _datatracker_get_multi_count(self, obj_type_uri: URI) -> int:
        assert obj_type_uri.uri is not None
        assert obj_type_uri.params == {}

        retry_time  = 1.875
        while True:
            try:
                req_url     = self.base_url + obj_type_uri.uri
                req_params  = {"limit": 1}
                req_headers = {'User-Agent': self.ua}
                self.get_count += 1
                r = self.session.get(url = req_url, params = req_params, headers = req_headers, verify = True, stream = False)
                if r.status_code == 200:
                    meta = r.json()['meta']
                    total_count = meta['total_count'] # type: int
                    self.log.debug(F"_datatracker_get_multi_count: {r.status_code} {obj_type_uri} count={total_count}")
                    return total_count
                else:
                    self.log.warning(F"_datatracker_get_multi_count: error {r.status_code} {obj_type_uri} - retry in {retry_time}")
                    if retry_time > 60:
                        self.log.error(F"_datatracker_get_multi_count: error - retry limit exceeded")
                        sys.exit(1)
                    self.session.close()
                    time.sleep(retry_time)
                    retry_time *= 2
            except requests.exceptions.ConnectionError:
                self.log.warning(F"_datatracker_get_multi_count: connection error - retry in {retry_time}")
                if retry_time > 60:
                    self.log.error(F"_datatracker_get_multi_count: error - retry limit exceeded")
                    sys.exit(1)
                self.session.close()
                time.sleep(retry_time)
                retry_time *= 2


    # ----------------------------------------------------------------------------------------------------------------------------
    # Private methods to manage the local cache.
    #
    # With the exception of _cache_update(), these should only access the local cache.
    #
    # The cache stores objects in the `ietfdata` database of the specified MongoDB instance.
    #
    # Objects are stored in collections named after the Datatracker URI with slashes replaced
    # by underscores (e.g., objects with URIs starting "/api/v1/person/person/" are stored in
    # the collection "api_v1_person_person"). The _db_collection() function can be used to
    # convert a URI to a collection name.
    #
    # Documents within those collections hold the JSON as retrieved from the datatracker.
    #
    # There is also a "cache_info" collection, containing metadata about the cache.

    def _cache_update_timed(self, obj_type_uri: URI, now: datetime, meta: CacheMetadata, field: str) -> None:
        start_time = meta.updated.strftime("%Y-%m-%dT%H:%M:%S.%f")  # Avoid isoformat(), since don't want TZ offset
        until_time  = now.strftime("%Y-%m-%dT%H:%M:%S.%f")
        update_uri = URI(obj_type_uri.uri)
        update_uri.params[F"{field}__gte"] = start_time
        update_uri.params[F"{field}__lt"]  = until_time
        self.log.info(F"_cache_update: {obj_type_uri} {start_time} -> {until_time}")
        for obj_json in self._datatracker_get_multi(update_uri):
            self._cache_put_object(obj_json)
            # When updating a Document, update the corresponding DocumentAuthor objects
            if obj_type_uri.uri == "/api/v1/doc/document/":
                uri = URI("/api/v1/doc/documentauthor/")
                uri.params["document"] = obj_json["id"]
                for item in self._datatracker_get_multi(uri):
                    self.log.info(f"_cache_update_timed: {obj_json['resource_uri']} -> {item['resource_uri']}")
                    self._cache_put_object(item)
                self._cache_record_query(uri, _parent_uri(uri))
        meta = self._cache_load_metadata(obj_type_uri)
        meta.updated = now
        obj_count = self._datatracker_get_multi_count(obj_type_uri)
        if obj_count is not None and obj_count != meta.total_count:
            self.log.info(f"_cache_update_timed: updated total_count {obj_type_uri} {meta.total_count} -> {obj_count}")
            meta.total_count = obj_count
        self._cache_save_metadata(obj_type_uri, meta)


    def _cache_update(self, obj_type_uri: URI, dt_version_changed:bool) -> None:
        if self.db is None:
            return
        assert(obj_type_uri.uri) is not None
        self._cache_create(obj_type_uri)
        now  = datetime.now(tz = dateutil.tz.gettz("America/Los_Angeles"))

        # Rewrite dependent object types to update the cache for objects on which
        # they depend. For example, if asked to update document authors, instead
        # ask to update documents since that will update the document authors too.
        if self._hints[obj_type_uri.uri].update_strategy == "R":
            if obj_type_uri.uri == "/api/v1/doc/documentauthor/":
                new_uri = URI("/api/v1/doc/document/")
            else:
                raise NotImplementedError(f"Cannot rewrite {obj_type_uri} in _cache_update")
            self.log.info(f"_cache_update: {obj_type_uri} -> {new_uri}")
            obj_type_uri = new_uri

        assert(obj_type_uri.uri) is not None

        # Only check for cache updates for each object type at most once per minute.
        # This significantly reduces the load on the database.
        if obj_type_uri.uri not in self.cache_update:
            self.cache_update[obj_type_uri.uri] = now
        elif now - self.cache_update[obj_type_uri.uri] < timedelta(minutes=1):
            return

        meta = self._cache_load_metadata(obj_type_uri)

        # URIs under /api/v1/name/ are internal names used by the datatracker.
        # Delete and recreate these caches if the datatracker version changed.
        if self._hints[obj_type_uri.uri].update_strategy == "V" and dt_version_changed:
            self.log.info(f"_cache_update: drop {obj_type_uri} due to datatracker version change")
            self._cache_delete(obj_type_uri)
            self._cache_create(obj_type_uri)
            meta = self._cache_load_metadata(obj_type_uri) # Reload metadata since cache entry recreated

        # Should we switch from a partial cache to full cache for this object type?
        cached_size = self.db[_db_collection(obj_type_uri)].count_documents({})
        if meta.partial and meta.total_count > 0 and cached_size / meta.total_count > 0.10:
            self.log.info(F"switch to full cache {obj_type_uri.uri}: cached {cached_size} of {meta.total_count} objects")
            for obj_json in self._datatracker_get_multi(obj_type_uri):
                self._cache_put_object(obj_json)
            meta.partial = False
            meta.queries = []
            meta.updated = now
            obj_count = self._datatracker_get_multi_count(obj_type_uri)
            if obj_count is not None and obj_count != meta.total_count:
                self.log.info(f"_cache_update: updated total_count {obj_type_uri} {meta.total_count}->{obj_count}")
                meta.total_count = obj_count
            self._cache_save_metadata(obj_type_uri, meta)

        # Update object types that have a "time" field giving last modified time:
        if self._hints[obj_type_uri.uri].update_strategy == "T" and now - meta.updated > timedelta(hours=1):
            self._cache_update_timed(obj_type_uri, now, meta, "time")

        # Update object types that have a "modified" field giving last modified time:
        if self._hints[obj_type_uri.uri].update_strategy == "M" and now - meta.updated > timedelta(hours=1):
            self._cache_update_timed(obj_type_uri, now, meta, "modified")

        # Update object types that have a "history_date" field giving last modified time:
        if self._hints[obj_type_uri.uri].update_strategy == "H" and now - meta.updated > timedelta(hours=1):
            self._cache_update_timed(obj_type_uri, now, meta, "history_date")

        # Update object types that have a "completed_on" field giving last modified time:
        if self._hints[obj_type_uri.uri].update_strategy == "C" and now - meta.updated > timedelta(hours=1):
            self._cache_update_timed(obj_type_uri, now, meta, "completed_on")

        # Update object types that have a "updated" field giving last modified time:
        if self._hints[obj_type_uri.uri].update_strategy == "U" and now - meta.updated > timedelta(hours=24):
            # FIXME: This should be as simple as saying:
            #   self._cache_update_timed(obj_type_uri, now, meta, "updated")
            # but the only objects with "updated" as /api/v1/meeting/meeting/ and the datatracker doesn't
            # allow filtering on the updated tag for meetings. As a work around, delete and refetch the
            # cache.
            self.log.warning(f"_cache_update: {obj_type_uri} can't update - will drop and refetch")
            self._cache_delete(obj_type_uri)
            self._cache_create(obj_type_uri)
            meta = self._cache_load_metadata(obj_type_uri) # Reload metadata since cache entry recreated

        # Warn if there are object types we don't know how to update
        if self._hints[obj_type_uri.uri].update_strategy == "-":
            self.log.warning(f"_cache_update: {obj_type_uri} - don't know how to update cache")

        # Is the cache metadata consistent?
        cached_size = self.db[_db_collection(obj_type_uri)].count_documents({})
        if not meta.partial and meta.total_count != cached_size:
            self.log.info(F"cache inconsistent {str(obj_type_uri)}: have {cached_size} objects, expected {meta.total_count}")

        # Record that the cache was updated
        self.cache_update[obj_type_uri.uri] = now


    def _cache_delete(self, obj_type_uri: URI) -> None:
        assert self.db is not None
        collection = _db_collection(obj_type_uri)
        self.log.info(f"_cache_delete: {collection}")
        self.db.cache_info.delete_one({"collection": collection})
        self.db[collection].drop()
        self.db_calls += 1


    def _cache_load_metadata(self, obj_type_uri: URI) -> CacheMetadata:
        assert self.db is not None
        collection  = _db_collection(obj_type_uri)
        meta_json = self.db.cache_info.find_one({"collection" : collection})
        self.db_calls += 1
        assert isinstance(meta_json, dict)
        return self.pavlova.from_mapping(meta_json, CacheMetadata)


    def _cache_save_metadata(self, obj_type_uri: URI, meta: CacheMetadata) -> None:
        assert self.db is not None
        meta_dict : Dict[str, Any] = {}
        meta_dict["collection"]  = _db_collection(obj_type_uri)
        meta_dict["created"]     = meta.created.isoformat()
        meta_dict["updated"]     = meta.updated.isoformat()
        meta_dict["partial"]     = meta.partial
        meta_dict["queries"]     = meta.queries
        meta_dict["total_count"] = meta.total_count
        self.db.cache_info.replace_one({"collection" : meta_dict["collection"]}, meta_dict, upsert=True)
        self.db.cache_info.create_index([('collection', ASCENDING)], unique=True)
        self.db_calls += 1


    def _cache_create(self, obj_type_uri: URI) -> None:
        assert self.db is not None
        collection  = _db_collection(obj_type_uri)
        self.db_calls += 1
        if self.db.cache_info.find_one({"collection": collection}):
            self.log.debug(F"_cache_create: {collection} already exists")
        else:
            self.log.info(F"_cache_create: {collection}")
            created     = datetime.now(tz = dateutil.tz.gettz("America/Los_Angeles"))
            updated     = created
            total_count = self._datatracker_get_multi_count(obj_type_uri)
            self._cache_save_metadata(obj_type_uri, CacheMetadata(created, updated, True, total_count, []))
            # # create indexes
            # try:
            #     for field in self._hints[type(obj_type_uri)].fields:
            #         self.db[_db_collection(obj_type_uri)].create_index([(field, ASCENDING)], background=True)
            #     for unique_field in self._hints[type(obj_type_uri)].unique_fields:
            #         self.db[_db_collection(obj_type_uri)].create_index([(unique_field, ASCENDING)], unique=True, background=True)
            # except:
            #     pass


    def _cache_record_query(self, obj_uri: URI, obj_type_uri: URI) -> None:
        if self.db is None:
            return
        assert obj_uri.uri is not None and "?" not in obj_uri.uri
        meta  = self._cache_load_metadata(obj_type_uri)
        if meta.partial:
            cache_uri = URI(obj_uri.uri)
            for n, v in obj_uri.params.items():
                assert n is not None
                assert v is not None
                if n != "time__gte" and n != "time__lt":
                    cache_uri.params[n] = v
            if str(cache_uri) not in meta.queries:
                self.log.debug(f"_cache_record_query: {str(cache_uri)}")
                meta.queries.append(str(cache_uri))
                self._cache_save_metadata(obj_type_uri, meta)
        else:
            # Queries are not recorded if we have a complete cache for this object type
            pass


    def _cache_has_object(self, obj_uri: URI) -> bool:
        if self.db is None:
            return False
        self._cache_update(_parent_uri(obj_uri), False)
        self.cache_req += 1
        self.db_calls  += 1
        if self.db[_db_collection(_parent_uri(obj_uri))].find_one({"resource_uri": obj_uri.uri}):
            self.cache_hit += 1
            return True       # Object is in the local cache
        else:
            if self._cache_has_all_objects(_parent_uri(obj_uri)):
                self.cache_hit += 1
                return True   # Object is known not to exist
            else:
                return False  # Object is not in the cache


    def _cache_get_object(self, obj_uri: URI) -> Optional[Dict[str, Any]]:
        assert self.db is not None
        self.db_calls += 1
        self.log.debug(F"_cache_get_object: {obj_uri}")
        return self.db[_db_collection(_parent_uri(obj_uri))].find_one({"resource_uri": obj_uri.uri})


    def _cache_put_object(self, obj_json: Dict[str, Any]) -> None:
        if self.db is None:
            return
        obj_uri      = URI(obj_json['resource_uri'])
        obj_type_uri = _parent_uri(obj_uri)
        self.log.info(F"_cache_put_object: {obj_uri}")
        self._cache_create(obj_type_uri)
        self.db[_db_collection(obj_type_uri)].replace_one({"resource_uri" : obj_uri.uri}, obj_json, upsert=True)
        self.db_calls += 1


    def _cache_has_all_objects(self, obj_type_uri: URI):
        if self.db is None:
            return False
        meta = self._cache_load_metadata(obj_type_uri)
        return not meta.partial


    def _cache_has_objects(self, obj_uri: URI, obj_type_uri: URI) -> bool:
        if self.db is None:
            return False
        meta = self._cache_load_metadata(obj_type_uri)
        return str(obj_uri) in meta.queries


    def _cache_get_objects(self, obj_uri: URI, obj_type_uri: URI, obj_type: Type[T]) -> Iterator[Dict[Any, Any]]:
        assert self.db          is not None
        assert obj_uri.uri      is not None
        assert obj_type_uri.uri is not None
        self.log.debug(F"_cache_get_objects: obj_uri={obj_uri}")
        #if len(obj_uri.params) > 1:
        #    for field in _translate_query(obj_uri, param_objs, obj_type).keys():
        #        self.log.debug(F"_cache_get_objects: create index '{field}'")
        #        self.db[_db_collection(obj_type_uri)].create_index([(field, ASCENDING)])
        deref = self._hints[obj_type_uri.uri].deref
        for s, d in deref.items():
            if s in obj_uri.params:
                deref_uri = obj_type.__dict__["__dataclass_fields__"][s].type.root
                deref_key = _db_collection(URI(deref_uri))
                self.log.debug(F"_cache_get_objects: deref {deref_uri}")
                self.db_calls += 1
                deref_json = self.db[deref_key].find_one({d: obj_uri.params[s]})
                assert deref_json is not None
                obj_uri.params[s] = deref_json["resource_uri"]
        query = _translate_query(obj_uri, obj_type)
        dbkey = _db_collection(obj_type_uri)
        self.log.debug(F"_cache_get_objects: query {query}")
        self.log.debug(F"_cache_get_objects: dbkey {dbkey}")
        self.db_calls += 1
        for obj_json in self.db[dbkey].find(query):
            self.log.debug(F"_cache_get_objects: get {obj_json['resource_uri']}")
            yield obj_json


    def _cache_check_versions(self) -> None:
        if self.db is None:
            return

        # Check for and upgrade v0.1.0 cache format to v1 cache format:
        cache_version_metadata = self.db.cache_info.find_one({"meta_key": "_cache_versions"})
        if cache_version_metadata is not None:
            if cache_version_metadata["cache_version"] == "0.1.0":
                # This is an instance of the original MongoDB cache. The cached data is useful,
                # but the format of the indexes and cache_info collections has changed. Remove
                # the old indexes, and update the cache_info collection to match the new format:
                self.log.info(f"_cache_check_versions: cache version changed 0.1.0 -> {self.cache_ver}")
                self.log.info(f"_cache_check_versions: drop index on cache_info")
                self.db.cache_info.drop_indexes()
                new_items : List[Dict[str, Any]] = []
                for item in self.db.cache_info.find():
                    collection = item["meta_key"]
                    if collection == "_cache_versions":
                        new_item = {
                            "collection"    : item["meta_key"],
                            "dt_version"    : item["dt_version"],
                            "cache_version" : self.cache_ver
                        }
                    else:
                        self.log.info(f"_cache_check_versions: drop index on {collection}")
                        self.db[collection].drop_indexes()
                        new_item = {
                            "collection"  : item["meta_key"],
                            "created"     : item["created"],
                            "updated"     : item["updated"],
                            "partial"     : item["partial"],
                            "queries"     : item["queries"],
                            "total_count" : item["total_count"]
                        }
                    new_items.append(new_item)
                for item in new_items:
                    self.log.info(f"_cache_check_versions: remove old cache_info {item['collection']}")
                    self.db.cache_info.delete_one({"meta_key": item['collection']})
                    self.log.info(f"_cache_check_versions: insert new cache_info {item['collection']}")
                    self.db.cache_info.insert_one(item)

        # Find cache and datatracker versions:
        cache_version_metadata = self.db.cache_info.find_one({"collection": "_cache_versions"})
        if cache_version_metadata is None:
            dt_version    = None
            cache_version = self.cache_ver
        else:
            dt_version    = cache_version_metadata["dt_version"]
            cache_version = cache_version_metadata["cache_version"]

        # Check cache version
        if cache_version != self.cache_ver:
            # Exit if the cache version doesn't match that we're expecting. Need to add code above
            # to update the cache if the format changes, as was done with the v0.1.1 to v1 change.
            self.log.error(f"_cache_check_versions: cache version changed {cache_version} -> {self.cache_ver}")
            sys.exit()
        else:
            self.log.info(f"_cache_check_versions: cache version {self.cache_ver}")

        # check Datatracker version
        version_info = self._datatracker_get_single(URI("/api/version/"))
        if version_info is not None:
            if dt_version != version_info["version"]:
                self.log.info(f"_cache_check_versions: datatracker version updated {dt_version} -> {version_info['version']}")
                for cache_uri in self._hints:
                    self.log.info(f"_cache_check_versions: update cache {cache_uri}")
                    self._cache_update(URI(cache_uri), True)
                dt_version = version_info["version"]
            else:
                self.log.info(f"_cache_check_versions: datatracker version {dt_version}")
        else:
            self.log.warning("_cache_check_versions: could not check datatracker version")

        self.db.cache_info.replace_one(
                {"collection": "_cache_versions"},
                {"collection": "_cache_versions", "dt_version": dt_version, "cache_version": cache_version},
                upsert=True)

    # ----------------------------------------------------------------------------------------------------------------------------
    # Private methods to retrieve objects from the datatracker:

    def _rate_limit(self) -> None:
        # A trivial rate limiter. Called before every HTTP GET to the datatracker.
        # The datatracker objects if more than 100 requests are made on a single
        # persistent HTTP connection.
        self.http_req += 1
        if (self.http_req % 100) == 0:
            self.session.close()


    def _retrieve(self, obj_uri: URI, obj_type: Type[T]) -> Optional[T]:
        self.log.debug(F"_retrieve {obj_uri}")
        self._cache_update(_parent_uri(obj_uri), False)
        if self._cache_has_object(obj_uri):
            self.log.debug(F"_retrieve {obj_uri} cache hit")
            obj_json = self._cache_get_object(obj_uri)
            if obj_json is not None:
                return self.pavlova.from_mapping(obj_json, obj_type)
            else:
                return None
        else:
            self.log.debug(F"_retrieve {obj_uri} cache miss")
            obj_json = self._datatracker_get_single(obj_uri)
            if obj_json is not None:
                self._cache_put_object(obj_json)
                self._cache_record_query(obj_uri, _parent_uri(obj_uri))
                return self.pavlova.from_mapping(obj_json, obj_type)
            else:
                return None


    def _retrieve_multi(self, obj_uri: URI, obj_type: Type[T]) -> Iterator[T]:
        self.log.debug(F"_retrieve_multi: obj_uri {obj_uri}")
        obj_type_uri = type(obj_uri)(obj_uri.uri)
        cache_uri = type(obj_uri)(obj_uri.uri)
        assert obj_uri.uri      is not None
        assert obj_type_uri.uri is not None
        assert cache_uri.uri    is not None
        for n, v in obj_uri.params.items():
            assert n is not None
            assert v is not None
            if n != "time__gte" and n != "time__lt":
                cache_uri.params[n] = v
        self._cache_update(obj_type_uri, False)
        obj_jsons = [] # type: List[Dict[str, Any]]
        if self._cache_has_objects(cache_uri, obj_type_uri) or self._cache_has_all_objects(obj_uri):
            self.log.debug(F"_retrieve_multi: cache hit {cache_uri} {obj_uri}")
            for obj_json in self._cache_get_objects(obj_uri, obj_type_uri, obj_type):
                obj_jsons.append(obj_json)
        else:
            self.log.debug(F"_retrieve_multi: cache miss {cache_uri} {obj_uri}")
            for obj_json in self._datatracker_get_multi(obj_uri):
                obj_jsons.append(obj_json)
                self._cache_put_object(obj_json)
                # If this object has a deref field, we need to fetch and cache the referenced object too
                if self.db is not None:
                    for s, d in self._hints[obj_type_uri.uri].deref.items():
                        deref_uri  = URI(obj_json[s])
                        if self._cache_has_object(deref_uri):
                            self.log.info(F"_retrieve_multri deref {deref_uri} already cached")
                        else:
                            deref_json = self._datatracker_get_single(deref_uri)
                            if deref_json is not None:
                                self.log.info(F"_retrieve_multri deref {deref_uri}")
                                self._cache_put_object(deref_json)
        self._cache_record_query(cache_uri, obj_type_uri)
        sort_by = self._hints[obj_type_uri.uri].sort_by
        for obj_json in sorted(obj_jsons, key=lambda k: k[sort_by]):  # type: ignore
            fetch_obj = self.pavlova.from_mapping(obj_json, obj_type) # type: T
            yield fetch_obj


    # ----------------------------------------------------------------------------------------------------------------------------
    # Datatracker API endpoints returning information about people:
    # * https://datatracker.ietf.org/api/v1/person/person/
    # * https://datatracker.ietf.org/api/v1/person/person/20209/
    # * https://datatracker.ietf.org/api/v1/person/historicalperson/
    # * https://datatracker.ietf.org/api/v1/person/alias/

    def person(self, person_uri: PersonURI) -> Optional[Person]:
        return self._retrieve(person_uri, Person)


    def person_from_email(self, email_addr: str) -> Optional[Person]:
        email = self.email(EmailURI(F"/api/v1/person/email/{email_addr}/"))
        if email is not None and email.person is not None:
            return self.person(email.person)
        else:
            return None


    def person_aliases(self,
            person        : Optional[Person] = None,
            name          : Optional[str] = None,
            name_contains : Optional[str] = None) -> Iterator[PersonAlias]:
        url = PersonAliasURI("/api/v1/person/alias/")
        if person is not None:
            url.params["person"] = person.id
        if name is not None:
            url.params["name"] = name
        if name_contains is not None:
            url.params["name__contains"] = name_contains
        return self._retrieve_multi(url, PersonAlias)


    def person_history(self, person: Person) -> Iterator[HistoricalPerson]:
        url = HistoricalPersonURI("/api/v1/person/historicalperson/")
        url.params["id"] = person.id
        return self._retrieve_multi(url, HistoricalPerson)


    def person_events(self, person: Person) -> Iterator[PersonEvent]:
        url = PersonEventURI("/api/v1/person/personevent/")
        url.params["person"] = person.id
        return self._retrieve_multi(url, PersonEvent)


    def people(self,
            since : str ="1970-01-01T00:00:00",
            until : str ="2038-01-19T03:14:07",
            name                : Optional[str] = None,
            name_contains       : Optional[str] = None,
            name_ascii          : Optional[str] = None,
            name_ascii_contains : Optional[str] = None,
            name_plain          : Optional[str] = None,
            name_plain_contains : Optional[str] = None) -> Iterator[Person]:
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
        url = PersonURI("/api/v1/person/person/")
        url.params["time__gte"] = since
        url.params["time__lt"]  = until
        if name is not None:
            url.params["name"] = name
        if name_contains is not None:
            url.params["name__contains"] = name_contains
        if name_ascii is not None:
            url.params["ascii"] = name_ascii
        if name_ascii_contains is not None:
            url.params["ascii__contains"] = name_ascii_contains
        if name_plain is not None:
            url.params["plain"] = name_plain
        if name_plain_contains is not None:
            url.params["plain__contains"] = name_plain_contains
        return self._retrieve_multi(url, Person)


    # ----------------------------------------------------------------------------------------------------------------------------
    # Datatracker API endpoints returning information about email addresses:
    # * https://datatracker.ietf.org/api/v1/person/email/csp@csperkins.org/
    # * https://datatracker.ietf.org/api/v1/person/historicalemail/

    def email(self, email_uri: EmailURI) -> Optional[Email]:
        return self._retrieve(email_uri, Email)


    def email_for_address(self, email_addr: str) -> Optional[Email]:
        uri = EmailURI(F"/api/v1/person/email/{email_addr}/")
        return self.email(uri)


    def email_for_person(self, person: Person) -> Iterator[Email]:
        uri = EmailURI("/api/v1/person/email/")
        uri.params["person"] = person.id
        return self._retrieve_multi(uri, Email)


    def email_history_for_address(self, email_addr: str) -> Iterator[HistoricalEmail]:
        uri = HistoricalEmailURI("/api/v1/person/historicalemail/")
        uri.params["address"] = email_addr
        return self._retrieve_multi(uri, HistoricalEmail)


    def email_history_for_person(self, person: Person) -> Iterator[HistoricalEmail]:
        uri = HistoricalEmailURI("/api/v1/person/historicalemail/")
        uri.params["person"] = person.id
        return self._retrieve_multi(uri, HistoricalEmail)


    def emails(self,
               since : str ="1970-01-01T00:00:00",
               until : str ="2038-01-19T03:14:07",
               addr_contains : Optional[str] = None) -> Iterator[Email]:
        """
        A generator that returns email addresses recorded in the datatracker.

        Parameters:
            since         -- Only return email addresses with timestamp after this
            until         -- Only return email addresses with timestamp before this
            addr_contains -- Only return email addresses containing this substring

        Returns:
            An iterator, where each element is an Email object
        """
        url = EmailURI("/api/v1/person/email/")
        url.params["time__gte"] = since
        url.params["time__lt"]   = until
        if addr_contains is not None:
            url.params["address__contains"] = addr_contains
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
            stream  : Optional[Stream]       = None,
            group   : Optional[Group]        = None) -> Iterator[Document]:
        url = DocumentURI("/api/v1/doc/document/")
        url.params["time__gte"] = since
        url.params["time__lt"] = until
        if doctype is not None:
            url.params["type"] = doctype.slug
        if stream is not None:
            url.params["stream"] = stream.slug
        if group is not None:
            url.params["group"] = group.id
        return self._retrieve_multi(url, Document)


    # Datatracker API endpoints returning information about document aliases:
    # * https://datatracker.ietf.org/api/v1/doc/docalias/?name=/                 - draft that became the given RFC

    def document_alias(self, document_alias_uri: DocumentAliasURI) -> Optional[DocumentAlias]:
        return self._retrieve(document_alias_uri, DocumentAlias)


    def document_aliases(self, name: Optional[str] = None) -> Iterator[DocumentAlias]:
        """
        Returns a list of DocumentAlias objects that correspond to the specified name.

        Parameters:
            name -- The name to lookup, for example "rfc3550", "std68", "bcp25", "draft-ietf-quic-transport"

        Returns:
            A list of DocumentAlias objects
        """
        url = DocumentAliasURI("/api/v1/doc/docalias/")
        if name is not None:
            url.params["name"] = name
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
        assert not "," in draft
        return self.document(DocumentURI("/api/v1/doc/document/" + draft + "/"))


    def document_from_rfc(self, rfc: str) -> Optional[Document]:
        """
        Returns the document that became the specified RFC.

        Parameters:
            rfc -- The RFC to lookup (e.g., "rfc3550" or "RFC3550")

        Returns:
            A Document object
        """
        assert rfc.lower().startswith("rfc")
        alias = self.document_alias(DocumentAliasURI(F"/api/v1/doc/docalias/{rfc.lower()}/"))
        if alias is None:
            return None
        else:
            return self.document(alias.document)


    def documents_from_bcp(self, bcp: str) -> Iterator[Document]:
        """
        Returns the document that became the specified BCP.

        Parameters:
            bcp -- The BCP to lookup (e.g., "bcp205" or "BCP205")

        Returns:
            A list of Document objects
        """
        assert bcp.lower().startswith("bcp")
        for alias in self.document_aliases(name=bcp.lower()):
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
        for alias in self.document_aliases(name=std.lower()):
            doc = self.document(alias.document)
            if doc is not None:
                yield doc


    # Datatracker API endpoints returning information about document types:
    # * https://datatracker.ietf.org/api/v1/name/doctypename/

    def document_type(self, doc_type_uri: DocumentTypeURI) -> Optional[DocumentType]:
        return self._retrieve(doc_type_uri, DocumentType)


    def document_type_from_slug(self, slug: str) -> Optional[DocumentType]:
        return self._retrieve(DocumentTypeURI(F"/api/v1/name/doctypename/{slug}/"), DocumentType)


    def document_types(self) -> Iterator[DocumentType]:
        return self._retrieve_multi(DocumentTypeURI("/api/v1/name/doctypename/"), DocumentType)


    # Datatracker API endpoints returning information about document states:
    # * https://datatracker.ietf.org/api/v1/doc/state/                           - Types of state a document can be in
    # * https://datatracker.ietf.org/api/v1/doc/statetype/                       - Possible types of state for a document

    def document_state(self, state_uri: DocumentStateURI) -> Optional[DocumentState]:
        return self._retrieve(state_uri, DocumentState)


    def document_states(self,
            state_type : Optional[DocumentStateType] = None,
            slug       : Optional[str]               = None) -> Iterator[DocumentState]:
        url = DocumentStateURI("/api/v1/doc/state/")
        if state_type is not None:
            url.params["type"] = state_type.slug
        if slug is not None:
            url.params["slug"] = slug
        return self._retrieve_multi(url, DocumentState)


    def document_state_type(self, state_type_uri : DocumentStateTypeURI) -> Optional[DocumentStateType]:
        return self._retrieve(state_type_uri, DocumentStateType)


    def document_state_type_from_slug(self, slug: str) -> Optional[DocumentStateType]:
        return self._retrieve(DocumentStateTypeURI(F"/api/v1/doc/statetype/{slug}/"), DocumentStateType)


    def document_state_types(self) -> Iterator[DocumentStateType]:
        url = DocumentStateTypeURI("/api/v1/doc/statetype/")
        return self._retrieve_multi(url, DocumentStateType)


    # Datatracker API endpoints returning information about document events:
    # * https://datatracker.ietf.org/api/v1/doc/docevent/                        - list of document events
    # * https://datatracker.ietf.org/api/v1/doc/docevent/?doc=...                - events for a document
    # * https://datatracker.ietf.org/api/v1/doc/docevent/?by=...                 - events by a person (as /api/v1/person/person)
    # * https://datatracker.ietf.org/api/v1/doc/docevent/?time=...               - events by time
    #   https://datatracker.ietf.org/api/v1/doc/statedocevent/                   - subset of /api/v1/doc/docevent/; same parameters
    #   https://datatracker.ietf.org/api/v1/doc/newrevisiondocevent/             -               "                "
    #   https://datatracker.ietf.org/api/v1/doc/submissiondocevent/              -               "                "
    #   https://datatracker.ietf.org/api/v1/doc/writeupdocevent/                 -               "                "
    #   https://datatracker.ietf.org/api/v1/doc/consensusdocevent/               -               "                "
    #   https://datatracker.ietf.org/api/v1/doc/reviewrequestdocevent/           -               "                "
    #   https://datatracker.ietf.org/api/v1/doc/lastcalldocevent/                -               "                "
    #   https://datatracker.ietf.org/api/v1/doc/telechatdocevent/                -               "                "
    #   https://datatracker.ietf.org/api/v1/doc/initialreviewdocevent/           -               "                "
    #   https://datatracker.ietf.org/api/v1/doc/editedauthorsdocevent/           -               "                "

    def document_event(self, event_uri : DocumentEventURI) -> Optional[DocumentEvent]:
        return self._retrieve(event_uri, DocumentEvent)


    def document_events(self,
                        since      : str = "1970-01-01T00:00:00",
                        until      : str = "2038-01-19T03:14:07",
                        doc        : Optional[Document] = None,
                        by         : Optional[Person]   = None,
                        event_type : Optional[str]      = None) -> Iterator[DocumentEvent]:
        """
        A generator returning information about document events.

        Parameters:
            since      -- Only return document events with timestamp after this
            until      -- Only return document events with timestamp after this
            doc        -- Only return document events for this document
            by         -- Only return document events by this person
            event_type -- Only return document events with this type

        Returns:
           A sequence of DocumentEvent objects
        """
        url = DocumentEventURI("/api/v1/doc/docevent/")
        url.params["time__gte"] = since
        url.params["time__lt"] = until
        if doc is not None:
            url.params["doc"]  = doc.id
        if by is not None:
            url.params["by"]   = by.id
        if event_type is not None:
            url.params["type"] = event_type
        return self._retrieve_multi(url, DocumentEvent)


    # Datatracker API endpoints returning information about document authorship:
    # * https://datatracker.ietf.org/api/v1/doc/documentauthor/?document=...     - authors of a document
    # * https://datatracker.ietf.org/api/v1/doc/documentauthor/?person=...       - documents by person
    # * https://datatracker.ietf.org/api/v1/doc/documentauthor/?email=...        - documents by person

    def document_authors(self, document : Document) -> Iterator[DocumentAuthor]:
        url = DocumentAuthorURI("/api/v1/doc/documentauthor/")
        url.params["document"] = document.id
        return self._retrieve_multi(url, DocumentAuthor)


    def documents_authored_by_person(self, person : Person) -> Iterator[DocumentAuthor]:
        url = DocumentAuthorURI("/api/v1/doc/documentauthor/")
        url.params["person"] = person.id
        for author in self._retrieve_multi(url, DocumentAuthor):
            # When fetching DocumentAuthor records, retrieve the corresponding Document so the cache updates correctly
            if self.db is not None:
                self.document(author.document)
            yield author


    def documents_authored_by_email(self, email : Email) -> Iterator[DocumentAuthor]:
        url = DocumentAuthorURI("/api/v1/doc/documentauthor/")
        url.params["email"] = email.address
        for author in self._retrieve_multi(url, DocumentAuthor):
            # When fetching DocumentAuthor records, retrieve the corresponding Document so the cache updates correctly
            if self.db is not None:
                self.document(author.document)
            yield author


    # Datatracker API endpoints returning information about related documents:
    #   https://datatracker.ietf.org/api/v1/doc/relateddocument/?source=...      - documents that source draft relates to
    #   https://datatracker.ietf.org/api/v1/doc/relateddocument/?target=...      - documents that relate to target draft
    #   https://datatracker.ietf.org/api/v1/doc/relateddochistory/

    def related_documents(self,
        source               : Optional[Document]         = None,
        target               : Optional[DocumentAlias]    = None,
        relationship_type    : Optional[RelationshipType] = None) -> Iterator[RelatedDocument]:

        url = RelatedDocumentURI("/api/v1/doc/relateddocument/")
        if source is not None:
            url.params["source"] = source.id
        if target is not None:
            url.params["target"] = target.id
        if relationship_type is not None:
            url.params["relationship"] = relationship_type.slug
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


    def relationship_type_from_slug(self, slug: str) -> Optional[RelationshipType]:
        return self._retrieve(RelationshipTypeURI(F"/api/v1/name/docrelationshipname/{slug}/"), RelationshipType)


    def relationship_types(self) -> Iterator[RelationshipType]:
        """
        A generator returning the possible relationship types

        Parameters:
           None

        Returns:
            An iterator of RelationshipType objects
        """
        url = RelationshipTypeURI("/api/v1/name/docrelationshipname/")
        return self._retrieve_multi(url, RelationshipType)


    # Datatracker API endpoints returning information about document history:
    #   https://datatracker.ietf.org/api/v1/doc/dochistory/
    #   https://datatracker.ietf.org/api/v1/doc/dochistoryauthor/

    # FIXME: implement document history methods


    # ----------------------------------------------------------------------------------------------------------------------------
    # Datatracker API endpoints returning information about ballots and document approval:
    # * https://datatracker.ietf.org/api/v1/name/ballotpositionname/
    #   https://datatracker.ietf.org/api/v1/doc/ballotpositiondocevent/
    # * https://datatracker.ietf.org/api/v1/doc/ballottype/
    # * https://datatracker.ietf.org/api/v1/doc/ballotdocevent/

    def ballot_position_name(self, ballot_position_name_uri : BallotPositionNameURI) -> Optional[BallotPositionName]:
        return self._retrieve(ballot_position_name_uri, BallotPositionName)


    def ballot_position_name_from_slug(self, slug: str) -> Optional[BallotPositionName]:
        return self._retrieve(BallotPositionNameURI(F"/api/v1/name/ballotpositionname/{slug}/"), BallotPositionName)


    def ballot_position_names(self) -> Iterator[BallotPositionName]:
        """
        A generator returning information about ballot position names. These describe
        the names of the responses that a person can give to a ballot (e.g., "Discuss",
        "Abstain", "No Objection", ...).

        Returns:
           A sequence of BallotPositionName objects
        """
        url = BallotPositionNameURI("/api/v1/name/ballotpositionname/")
        return self._retrieve_multi(url, BallotPositionName)


    def ballot_type(self, ballot_type_uri : BallotTypeURI) -> Optional[BallotType]:
        return self._retrieve(ballot_type_uri, BallotType)


    def ballot_types(self, doc_type : Optional[DocumentType]) -> Iterator[BallotType]:
        """
        A generator returning information about ballot types.

        Parameters:
            doc_type     -- Only return ballot types relating to this document type

        Returns:
           A sequence of BallotType objects
        """
        url = BallotTypeURI("/api/v1/doc/ballottype/")
        if doc_type is not None:
            url.params["doc_type"] = doc_type.slug
        return self._retrieve_multi(url, BallotType)



    def ballot_document_event(self, ballot_event_uri : BallotDocumentEventURI) -> Optional[BallotDocumentEvent]:
        return self._retrieve(ballot_event_uri, BallotDocumentEvent)


    def ballot_document_events(self,
                        since       : str = "1970-01-01T00:00:00",
                        until       : str = "2038-01-19T03:14:07",
                        ballot_type : Optional[BallotType]    = None,
                        event_type  : Optional[str]           = None,
                        by          : Optional[Person]        = None,
                        doc         : Optional[Document]      = None) -> Iterator[BallotDocumentEvent]:
        """
        A generator returning information about ballot document events.

        Parameters:
            since        -- Only return ballot document events with timestamp after this
            until        -- Only return ballot document events with timestamp after this
            ballot_type  -- Only return ballot document events of this ballot type
            event_type   -- Only return ballot document events with this type
            by           -- Only return ballot document events by this person
            doc          -- Only return ballot document events that relate to this document

        Returns:
           A sequence of BallotDocumentEvent objects
        """
        url = BallotDocumentEventURI("/api/v1/doc/ballotdocevent/")
        url.params["time__gte"] = since
        url.params["time__lt"] = until
        if ballot_type is not None:
            url.params["ballot_type"] = ballot_type.id
        if by is not None:
            url.params["by"] = by.id
        if doc is not None:
            url.params["doc"] = doc.id
        if event_type is not None:
            url.params["type"] = event_type
        return self._retrieve_multi(url, BallotDocumentEvent)


    # ----------------------------------------------------------------------------------------------------------------------------
    # Datatracker API endpoints returning information about document submissions:
    # * https://datatracker.ietf.org/api/v1/submit/submission/
    # * https://datatracker.ietf.org/api/v1/submit/submissionevent/
    #   https://datatracker.ietf.org/api/v1/submit/submissioncheck/
    #   https://datatracker.ietf.org/api/v1/submit/preapproval/

    def submission(self, submission_uri: SubmissionURI) -> Optional[Submission]:
        return self._retrieve(submission_uri, Submission)


    def submissions(self,
            date_since           : str = "1970-01-01",
            date_until           : str = "2038-01-19") -> Iterator[Submission]:
        url = SubmissionURI("/api/v1/submit/submission/")
        url.params["submission_date__gte"] = date_since
        url.params["submission_date__lt"] = date_until
        return self._retrieve_multi(url, Submission)


    def submission_event(self, event_uri: SubmissionEventURI) -> Optional[SubmissionEvent]:
        return self._retrieve(event_uri, SubmissionEvent)


    def submission_events(self,
                        since      : str = "1970-01-01T00:00:00",
                        until      : str = "2038-01-19T03:14:07",
                        by         : Optional[Person]     = None,
                        submission : Optional[Submission] = None) -> Iterator[SubmissionEvent]:
        """
        A generator returning information about submission events.

        Parameters:
            since      -- Only return submission events with timestamp after this
            until      -- Only return submission events with timestamp after this
            by         -- Only return submission events by this person
            submission -- Only return submission events about this submission

        Returns:
           A sequence of SubmissionEvent objects
        """
        url = SubmissionEventURI("/api/v1/submit/submissionevent/")
        url.params["time__gte"] = since
        url.params["time__lt"] = until
        if by is not None:
            url.params["by"] = by.id
        if submission is not None:
            url.params["submission"] = submission.id
        return self._retrieve_multi(url, SubmissionEvent)

    # ----------------------------------------------------------------------------------------------------------------------------
    # Datatracker API endpoints returning miscellaneous information about documents:
    #   https://datatracker.ietf.org/api/v1/doc/docreminder/
    #   https://datatracker.ietf.org/api/v1/doc/documenturl/
    #   https://datatracker.ietf.org/api/v1/doc/deletedevent/

    # FIXME: implement these


    # ----------------------------------------------------------------------------------------------------------------------------
    # Datatracker API endpoints returning information about RFC publication streams:
    # * https://datatracker.ietf.org/api/v1/name/streamname/

    def stream(self, stream_uri: StreamURI) -> Optional[Stream]:
        return self._retrieve(stream_uri, Stream)


    def stream_from_slug(self, slug: str) -> Optional[Stream]:
        return self._retrieve(StreamURI(F"/api/v1/name/streamname/{slug}/"), Stream)


    def streams(self) -> Iterator[Stream]:
        return self._retrieve_multi(StreamURI("/api/v1/name/streamname/"), Stream)


    # ----------------------------------------------------------------------------------------------------------------------------
    # Datatracker API endpoints returning information about working groups:
    # * https://datatracker.ietf.org/api/v1/group/group/                               - list of groups
    # * https://datatracker.ietf.org/api/v1/group/group/2161/                          - info about group 2161
    # * https://datatracker.ietf.org/api/v1/group/grouphistory/?group=2161             - history
    # * https://datatracker.ietf.org/api/v1/group/groupurl/?group=2161                 - URLs
    # * https://datatracker.ietf.org/api/v1/group/groupevent/?group=2161               - events
    # * https://datatracker.ietf.org/api/v1/group/groupmilestone/?group=2161           - Current milestones
    # * https://datatracker.ietf.org/api/v1/group/groupmilestonehistory/?group=2161    - Previous milestones
    # * https://datatracker.ietf.org/api/v1/group/milestonegroupevent/?group=2161      - changed milestones
    # * https://datatracker.ietf.org/api/v1/group/role/?group=2161                     - The current WG chairs and ADs of a group
    # * https://datatracker.ietf.org/api/v1/group/role/?person=20209                   - Groups a person is currently involved with
    # * https://datatracker.ietf.org/api/v1/group/role/?email=csp@csperkins.org        - Groups a person is currently involved with
    # * https://datatracker.ietf.org/api/v1/group/rolehistory/?group=2161              - The previous WG chairs and ADs of a group
    # * https://datatracker.ietf.org/api/v1/group/rolehistory/?person=20209            - Groups person was previously involved with
    # * https://datatracker.ietf.org/api/v1/group/rolehistory/?email=csp@csperkins.org - Groups person was previously involved with
    # * https://datatracker.ietf.org/api/v1/group/changestategroupevent/?group=2161    - Group state changes
    #   https://datatracker.ietf.org/api/v1/group/groupstatetransitions                - ???
    # * https://datatracker.ietf.org/api/v1/name/groupstatename/
    # * https://datatracker.ietf.org/api/v1/name/grouptypename/

    def group(self, group_uri: GroupURI) -> Optional[Group]:
        return self._retrieve(group_uri, Group)


    def group_from_acronym(self, acronym: str) -> Optional[Group]:
        url = GroupURI("/api/v1/group/group/")
        url.params["acronym"] = acronym
        groups = list(self._retrieve_multi(url, Group))
        if len(groups) == 0:
            return None
        elif len(groups) == 1:
            return groups[0]
        else:
            raise RuntimeError("group_from_acronym: multiple groups returned, expected 0 or 1")


    def groups(self,
            since         : str                  = "1970-01-01T00:00:00",
            until         : str                  = "2038-01-19T03:14:07",
            name_contains : Optional[str]        = None,
            state         : Optional[GroupState] = None,
            parent        : Optional[Group]      = None) -> Iterator[Group]:
        url = GroupURI("/api/v1/group/group/")
        url.params["time__gte"]       = since
        url.params["time__lt"]       = until
        if name_contains is not None:
            url.params["name__contains"] = name_contains
        if state is not None:
            url.params["state"] = state.slug
        if parent is not None:
            url.params["parent"] = parent.id
        return self._retrieve_multi(url, Group)


    def group_history(self, group_history_uri: GroupHistoryURI) -> Optional[GroupHistory]:
        return self._retrieve(group_history_uri, GroupHistory)


    def group_histories_from_acronym(self, acronym: str) -> Iterator[GroupHistory]:
        url = GroupHistoryURI("/api/v1/group/grouphistory/")
        url.params["acronym"] = acronym
        return self._retrieve_multi(url, GroupHistory)


    def group_histories(self,
            since         : str                  = "1970-01-01T00:00:00",
            until         : str                  = "2038-01-19T03:14:07",
            group         : Optional[Group]      = None,
            state         : Optional[GroupState] = None,
            parent        : Optional[Group]      = None) -> Iterator[GroupHistory]:
        url = GroupHistoryURI("/api/v1/group/grouphistory/")
        url.params["time__gte"]  = since
        url.params["time__lt"]  = until
        if group is not None:
            url.params["group"] = group.id
        if state is not None:
            url.params["state"] = state.slug
        if parent is not None:
            url.params["parent"] = parent.id
        return self._retrieve_multi(url, GroupHistory)


    def group_event(self, group_event_uri : GroupEventURI) -> Optional[GroupEvent]:
        return self._retrieve(group_event_uri, GroupEvent)


    def group_events(self,
            since         : str                  = "1970-01-01T00:00:00",
            until         : str                  = "2038-01-19T03:14:07",
            by            : Optional[Person]     = None,
            group         : Optional[Group]      = None,
            type          : Optional[str]        = None) -> Iterator[GroupEvent]:
        url = GroupEventURI("/api/v1/group/groupevent/")
        url.params["time__gte"] = since
        url.params["time__lt"]  = until
        if by is not None:
            url.params["by"] = by.id
        if group is not None:
            url.params["group"] = group.id
        if type is not None:
            url.params["type"]  = type
        return self._retrieve_multi(url, GroupEvent)

    def group_url(self, group_url_uri: GroupUrlURI) -> Optional[GroupUrl]:
        return self._retrieve(group_url_uri, GroupUrl)


    def group_urls(self, group: Optional[Group] = None) -> Iterator[GroupUrl]:
        url = GroupUrlURI("/api/v1/group/groupurl/")
        if group is not None:
            url.params["group"] = group.id
        return self._retrieve_multi(url, GroupUrl)


    def group_milestone_statename(self, group_milestone_statename_uri: GroupMilestoneStateNameURI) -> Optional[GroupMilestoneStateName]:
        return self._retrieve(group_milestone_statename_uri, GroupMilestoneStateName)


    def group_milestone_statenames(self) -> Iterator[GroupMilestoneStateName]:
        return self._retrieve_multi(GroupMilestoneStateNameURI("/api/v1/name/groupmilestonestatename/"), GroupMilestoneStateName)


    def group_milestone(self, group_milestone_uri : GroupMilestoneURI) -> Optional[GroupMilestone]:
        return self._retrieve(group_milestone_uri, GroupMilestone)


    def group_milestones(self,
            since         : str                               = "1970-01-01T00:00:00",
            until         : str                               = "2038-01-19T03:14:07",
            group         : Optional[Group]                   = None,
            state         : Optional[GroupMilestoneStateName] = None) -> Iterator[GroupMilestone]:
        url = GroupMilestoneURI("/api/v1/group/groupmilestone/")
        url.params["time__gte"]       = since
        url.params["time__lt"]       = until
        if group is not None:
            url.params["group"] = group.id
        if state is not None:
            url.params["state"] = state.slug
        return self._retrieve_multi(url, GroupMilestone)


    def role_name(self, role_name_uri: RoleNameURI) -> Optional[RoleName]:
        return self._retrieve(role_name_uri, RoleName)


    def role_name_from_slug(self, slug: str) -> Optional[RoleName]:
        return self._retrieve(RoleNameURI(F"/api/v1/name/rolename/{slug}/"), RoleName)


    def role_names(self) -> Iterator[RoleName]:
        return self._retrieve_multi(RoleNameURI("/api/v1/name/rolename/"), RoleName)


    def group_role(self, group_role_uri : GroupRoleURI) -> Optional[GroupRole]:
        return self._retrieve(group_role_uri, GroupRole)


    def group_roles(self,
            email         : Optional[str]           = None,
            group         : Optional[Group]         = None,
            name          : Optional[RoleName]      = None,
            person        : Optional[Person]        = None) -> Iterator[GroupRole]:
        url = GroupRoleURI("/api/v1/group/role/")
        if email is not None:
            url.params["email"] = email
        if group is not None:
            url.params["group"] = group.id
        if name is not None:
            url.params["name"] = name.slug
        if person is not None:
            url.params["person"] = person.id
        return self._retrieve_multi(url, GroupRole)


    def group_role_history(self, group_role_history_uri : GroupRoleHistoryURI) -> Optional[GroupRoleHistory]:
        return self._retrieve(group_role_history_uri, GroupRoleHistory)


    def group_role_histories(self,
            email         : Optional[str]           = None,
            group         : Optional[Group]         = None,
            name          : Optional[RoleName]      = None,
            person        : Optional[Person]        = None) -> Iterator[GroupRoleHistory]:
        url = GroupRoleHistoryURI("/api/v1/group/rolehistory/")
        if email is not None:
            url.params["email"] = email
        if group is not None:
            url.params["group"] = group.id
        if name is not None:
            url.params["name"] = name.slug
        if person is not None:
            url.params["person"] = person.id
        return self._retrieve_multi(url, GroupRoleHistory)


    def group_milestone_history(self, group_milestone_history_uri : GroupMilestoneHistoryURI) -> Optional[GroupMilestoneHistory]:
        return self._retrieve(group_milestone_history_uri, GroupMilestoneHistory)


    def group_milestone_histories(self,
            since         : str                               = "1970-01-01T00:00:00",
            until         : str                               = "2038-01-19T03:14:07",
            group         : Optional[Group]                   = None,
            milestone     : Optional[GroupMilestone]          = None,
            state         : Optional[GroupMilestoneStateName] = None) -> Iterator[GroupMilestoneHistory]:
        url = GroupMilestoneHistoryURI("/api/v1/group/groupmilestonehistory/")
        url.params["time__gte"]       = since
        url.params["time__lt"]       = until
        if group is not None:
            url.params["group"] = group.id
        if milestone is not None:
            url.params["milestone"] = milestone.id
        if state is not None:
            url.params["state"] = state.slug
        return self._retrieve_multi(url, GroupMilestoneHistory)


    def group_milestone_event(self, group_milestone_event_uri : GroupMilestoneEventURI) -> Optional[GroupMilestoneEvent]:
        return self._retrieve(group_milestone_event_uri, GroupMilestoneEvent)


    def group_milestone_events(self,
            since         : str                        = "1970-01-01T00:00:00",
            until         : str                        = "2038-01-19T03:14:07",
            by            : Optional[Person]           = None,
            group         : Optional[Group]            = None,
            milestone     : Optional[GroupMilestone]   = None,
            type          : Optional[str]              = None) -> Iterator[GroupMilestoneEvent]:
        url = GroupMilestoneEventURI("/api/v1/group/milestonegroupevent/")
        url.params["time__gte"] = since
        url.params["time__lt"]  = until
        if by is not None:
            url.params["by"] = by.id
        if group is not None:
            url.params["group"] = group.id
        if milestone is not None:
            url.params["milestone"] = milestone.id
        if type is not None:
            url.params["type"] = type
        return self._retrieve_multi(url, GroupMilestoneEvent)


    def group_state_change_event(self, group_state_change_event_uri : GroupStateChangeEventURI) -> Optional[GroupStateChangeEvent]:
        return self._retrieve(group_state_change_event_uri, GroupStateChangeEvent)


    def group_state_change_events(self,
            since         : str                        = "1970-01-01T00:00:00",
            until         : str                        = "2038-01-19T03:14:07",
            by            : Optional[Person]           = None,
            group         : Optional[Group]            = None,
            state         : Optional[GroupState]       = None) -> Iterator[GroupStateChangeEvent]:
        url = GroupStateChangeEventURI("/api/v1/group/changestategroupevent/")
        url.params["time__gte"]       = since
        url.params["time__lt"]       = until
        if by is not None:
            url.params["by"] = by.id
        if group is not None:
            url.params["group"] = group.id
        if state is not None:
            url.params["state"] = state.slug
        return self._retrieve_multi(url, GroupStateChangeEvent)


    def group_state(self, group_state_uri : GroupStateURI) -> Optional[GroupState]:
        return self._retrieve(group_state_uri, GroupState)


    def group_state_from_slug(self, slug : str) -> Optional[GroupState]:
        return self._retrieve(GroupStateURI(F"/api/v1/name/groupstatename/{slug}/"), GroupState)


    def group_states(self) -> Iterator[GroupState]:
        url = GroupStateURI("/api/v1/name/groupstatename/")
        return self._retrieve_multi(url, GroupState)


    def group_type_name(self, group_type_name_uri : GroupTypeNameURI) -> Optional[GroupTypeName]:
        return self._retrieve(group_type_name_uri, GroupTypeName)


    def group_type_name_from_slug(self, slug : str) -> Optional[GroupTypeName]:
        return self._retrieve(GroupTypeNameURI(F"/api/v1/name/grouptypename/{slug}/"), GroupTypeName)


    def group_type_names(self) -> Iterator[GroupTypeName]:
        return self._retrieve_multi(GroupTypeNameURI("/api/v1/name/grouptypename/"), GroupTypeName)


    # ----------------------------------------------------------------------------------------------------------------------------
    # Datatracker API endpoints returning information about meetings:
    # * https://datatracker.ietf.org/api/v1/meeting/meeting/                        - list of meetings
    # * https://datatracker.ietf.org/api/v1/meeting/meeting/747/                    - information about meeting number 747
    # * https://datatracker.ietf.org/api/v1/meeting/schedule/791/                   - a version of the meeting agenda
    # * https://datatracker.ietf.org/api/v1/meeting/session/25886/                  - a session within a meeting
    # * https://datatracker.ietf.org/api/v1/meeting/session/                        - list of sessions within meetings
    # * https://datatracker.ietf.org/api/v1/meeting/session/?meeting=747            - sessions in meeting number 747
    # * https://datatracker.ietf.org/api/v1/meeting/session/?meeting=747&group=2161 - sessions in meeting number 747 for group 2161
    # * https://datatracker.ietf.org/api/v1/meeting/schedtimesessassignment/59003/  - a schededuled session within a meeting
    # * https://datatracker.ietf.org/api/v1/meeting/schedulingevent/                - sessions being scheduled
    #   https://datatracker.ietf.org/api/v1/meeting/timeslot/9480/                  - a time slot within a meeting (time, duration, location)
    #
    #   https://datatracker.ietf.org/api/v1/meeting/room/537/                       - a room at a meeting
    #   https://datatracker.ietf.org/api/v1/meeting/floorplan/14/                   - floor plan for a meeting venue
    #
    #   https://datatracker.ietf.org/meeting/107/agenda.json
    #   https://datatracker.ietf.org/meeting/interim-2020-hrpc-01/agenda.json
    #
    # * https://datatracker.ietf.org/api/v1/name/sessionstatusname/
    #   https://datatracker.ietf.org/api/v1/name/agendatypename/
    #   https://datatracker.ietf.org/api/v1/name/timeslottypename/
    #   https://datatracker.ietf.org/api/v1/name/roomresourcename/
    # * https://datatracker.ietf.org/api/v1/name/meetingtypename/
    #   https://datatracker.ietf.org/api/v1/name/importantdatename/

    def meeting_session_assignment(self, assignment_uri : SessionAssignmentURI) -> Optional[SessionAssignment]:
        return self._retrieve(assignment_uri, SessionAssignment)


    def meeting_session_assignments(self, schedule : Schedule) -> Iterator[SessionAssignment]:
        """
        The assignment of sessions to timeslots in a meeting schedule.
        """
        url = SessionAssignmentURI("/api/v1/meeting/schedtimesessassignment/")
        url.params["schedule"] = schedule.id
        return self._retrieve_multi(url, SessionAssignment)


    def meeting_session_status(self, session: Session) -> SessionStatusName:
        last_event  = list(self.meeting_scheduling_events(session=session))[-1]
        status_name = self.meeting_session_status_name(last_event.status)
        assert status_name is not None
        return status_name


    def meeting_session_status_name(self, ssn_uri: SessionStatusNameURI) -> Optional[SessionStatusName]:
        return self._retrieve(ssn_uri, SessionStatusName)


    def meeting_session_status_name_from_slug(self, slug: str) -> Optional[SessionStatusName]:
        return self._retrieve(SessionStatusNameURI(F"/api/v1/name/sessionstatusname/{slug}/"), SessionStatusName)


    def meeting_session_status_names(self) -> Iterator[SessionStatusName]:
        return self._retrieve_multi(SessionStatusNameURI("/api/v1/name/sessionstatusname/"), SessionStatusName)


    def meeting_session(self, session_uri : SessionURI) -> Optional[Session]:
        return self._retrieve(session_uri, Session)


    def meeting_sessions(self,
            meeting : Meeting,
            group   : Optional[Group] = None) -> Iterator[Session]:
        url = SessionURI("/api/v1/meeting/session/")
        url.params["meeting"]  = meeting.id
        if group is not None:
            url.params["group"] = group.id
        return self._retrieve_multi(url, Session)


    def meeting_timeslot(self, timeslot_uri: TimeslotURI) -> Optional[Timeslot]:
        return self._retrieve(timeslot_uri, Timeslot)


    def meeting_scheduling_event(self, scheduling_event_uri: SchedulingEventURI) -> Optional[SchedulingEvent]:
        return self._retrieve(scheduling_event_uri, SchedulingEvent)


    def meeting_scheduling_events(self,
            by      : Optional[Person]  = None,
            session : Optional[Session] = None) -> Iterator[SchedulingEvent]:
        url = SchedulingEventURI("/api/v1/meeting/schedulingevent/")
        if session is not None:
            url.params["session"] = session.id
        if by is not None:
            url.params["by"] = by.id
        return self._retrieve_multi(url, SchedulingEvent)


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

        A meeting comprises a number of `Session`s organised into a `Schedule`.
        Use `meeting_sessions()` to find the sessions that occurred during the
        meeting. Use `meeting_session_assignments()` to find the timeslots when
        those sessions occurred.
        """
        return self._retrieve(meeting_uri, Meeting)


    def meetings(self,
            start_date   : str = "1970-01-01",
            end_date     : str = "2038-01-19",
            meeting_type : Optional[MeetingType] = None) -> Iterator[Meeting]:
        """
        Return information about meetings taking place within a particular date range.
        """
        url = MeetingURI("/api/v1/meeting/meeting/")
        url.params["date__gte"] = start_date
        url.params["date__lte"] = end_date
        if meeting_type is not None:
            url.params["type"] = meeting_type.slug
        return self._retrieve_multi(url, Meeting)



    def meeting_type(self, meeting_type_uri: MeetingTypeURI) -> Optional[MeetingType]:
        return self._retrieve(meeting_type_uri, MeetingType)


    def meeting_type_from_slug(self, slug: str) -> Optional[MeetingType]:
        return self._retrieve(MeetingTypeURI(F"/api/v1/name/meetingtypename/{slug}/"), MeetingType)


    def meeting_types(self) -> Iterator[MeetingType]:
        """
        A generator returning the possible meeting types

        Parameters:
           None

        Returns:
            An iterator of MeetingType objects
        """
        return self._retrieve_multi(MeetingTypeURI("/api/v1/name/meetingtypename/"), MeetingType)


    # ----------------------------------------------------------------------------------------------------------------------------
    # Datatracker API endpoints returning information about IPR disclosures:
    #
    #   https://datatracker.ietf.org/api/v1/ipr/iprdocrel/
    # * https://datatracker.ietf.org/api/v1/ipr/iprdisclosurebase/
    #
    # * https://datatracker.ietf.org/api/v1/ipr/genericiprdisclosure/
    # * https://datatracker.ietf.org/api/v1/ipr/holderiprdisclosure/
    # * https://datatracker.ietf.org/api/v1/ipr/thirdpartyiprdisclosure
    #
    #   https://datatracker.ietf.org/api/v1/ipr/nondocspecificiprdisclosure/
    #   https://datatracker.ietf.org/api/v1/ipr/relatedipr/
    #
    #   https://datatracker.ietf.org/api/v1/ipr/iprevent/
    #   https://datatracker.ietf.org/api/v1/ipr/legacymigrationiprevent/
    #
    # * https://datatracker.ietf.org/api/v1/name/iprdisclosurestatename/
    #   https://datatracker.ietf.org/api/v1/name/ipreventtypename/
    # * https://datatracker.ietf.org/api/v1/name/iprlicensetypename/

    def ipr_disclosure_state(self, ipr_disclosure_state_uri: IPRDisclosureStateURI) -> Optional[IPRDisclosureState]:
        return self._retrieve(ipr_disclosure_state_uri, IPRDisclosureState)


    def ipr_disclosure_states(self) -> Iterator[IPRDisclosureState]:
        return self._retrieve_multi(IPRDisclosureStateURI("/api/v1/name/iprdisclosurestatename/"), IPRDisclosureState)


    def ipr_disclosure_base(self, ipr_disclosure_base_uri: IPRDisclosureBaseURI) -> Optional[IPRDisclosureBase]:
        return self._retrieve(ipr_disclosure_base_uri, IPRDisclosureBase)


    def ipr_disclosure_bases(self,
            since              : str                             = "1970-01-01T00:00:00",
            until              : str                             = "2038-01-19T03:14:07",
            by                 : Optional[Person]                = None,
            holder_legal_name  : Optional[str]                   = None,
            state              : Optional[IPRDisclosureState]    = None,
            submitter_email    : Optional[str]                   = None,
            submitter_name     : Optional[str]                   = None) -> Iterator[IPRDisclosureBase]:
        url = IPRDisclosureBaseURI("/api/v1/ipr/iprdisclosurebase/")
        url.params["time__gte"] = since
        url.params["time__lt"]  = until
        if by is not None:
            url.params["by"] = by.id
        if holder_legal_name is not None:
            url.params["holder_legal_name"] = holder_legal_name
        if state is not None:
            url.params["state"] = state.slug
        if submitter_email is not None:
            url.params["submitter_email"] = submitter_email
        if submitter_name is not None:
            url.params["submitter_name"] = submitter_name
        return self._retrieve_multi(url, IPRDisclosureBase)


    def generic_ipr_disclosure(self, generic_ipr_disclosure_uri: GenericIPRDisclosureURI) -> Optional[GenericIPRDisclosure]:
        return self._retrieve(generic_ipr_disclosure_uri, GenericIPRDisclosure)


    def generic_ipr_disclosures(self,
            since               : str                             = "1970-01-01T00:00:00",
            until               : str                             = "2038-01-19T03:14:07",
            by                  : Optional[Person]                = None,
            holder_legal_name   : Optional[str]                   = None,
            holder_contact_name : Optional[str]                   = None,
            state               : Optional[IPRDisclosureState]    = None,
            submitter_email     : Optional[str]                   = None,
            submitter_name      : Optional[str]                   = None) -> Iterator[GenericIPRDisclosure]:
        url = GenericIPRDisclosureURI("/api/v1/ipr/genericiprdisclosure/")
        url.params["time__gte"] = since
        url.params["time__lt"]  = until
        if by is not None:
            url.params["by"] = by.id
        if holder_legal_name is not None:
            url.params["holder_legal_name"] = holder_legal_name
        if holder_contact_name is not None:
            url.params["holder_contact_name"] = holder_contact_name
        if state is not None:
            url.params["state"] = state.slug
        if submitter_email is not None:
            url.params["submitter_email"] = submitter_email
        if submitter_name is not None:
            url.params["submitter_name"] = submitter_name
        return self._retrieve_multi(url, GenericIPRDisclosure)


    def ipr_license_type(self, ipr_license_type_uri: IPRLicenseTypeURI) -> Optional[IPRLicenseType]:
        return self._retrieve(ipr_license_type_uri, IPRLicenseType)


    def ipr_license_types(self) -> Iterator[IPRLicenseType]:
        return self._retrieve_multi(IPRLicenseTypeURI("/api/v1/name/iprlicensetypename/"), IPRLicenseType)


    def holder_ipr_disclosure(self, holder_ipr_disclosure_uri: HolderIPRDisclosureURI) -> Optional[HolderIPRDisclosure]:
        return self._retrieve(holder_ipr_disclosure_uri, HolderIPRDisclosure)


    def holder_ipr_disclosures(self,
            since                : str                             = "1970-01-01T00:00:00",
            until                : str                             = "2038-01-19T03:14:07",
            by                   : Optional[Person]                = None,
            holder_legal_name    : Optional[str]                   = None,
            holder_contact_name  : Optional[str]                   = None,
            ietfer_contact_email : Optional[str]                   = None,
            ietfer_name          : Optional[str]                   = None,
            licensing            : Optional[IPRLicenseType]        = None,
            state                : Optional[IPRDisclosureState]    = None,
            submitter_email      : Optional[str]                   = None,
            submitter_name       : Optional[str]                   = None) -> Iterator[HolderIPRDisclosure]:
        url = HolderIPRDisclosureURI("/api/v1/ipr/holderiprdisclosure/")
        url.params["time__gte"] = since
        url.params["time__lt"]  = until
        if by is not None:
            url.params["by"] = by.id
        if holder_legal_name is not None:
            url.params["holder_legal_name"] = holder_legal_name
        if holder_contact_name is not None:
            url.params["holder_contact_name"] = holder_contact_name
        if ietfer_contact_email is not None:
            url.params["ietfer_contact_email"] = ietfer_contact_email
        if ietfer_name is not None:
            url.params["ietfer_name"] = ietfer_name
        if licensing is not None:
            url.params["licensing"] = licensing.slug
        if state is not None:
            url.params["state"] = state.slug
        if submitter_email is not None:
            url.params["submitter_email"] = submitter_email
        if submitter_name is not None:
            url.params["submitter_name"] = submitter_name
        return self._retrieve_multi(url, HolderIPRDisclosure)


    def thirdparty_ipr_disclosure(self, thirdparty_ipr_disclosure_uri: ThirdPartyIPRDisclosureURI) -> Optional[ThirdPartyIPRDisclosure]:
        return self._retrieve(thirdparty_ipr_disclosure_uri, ThirdPartyIPRDisclosure)


    def thirdparty_ipr_disclosures(self,
            since                : str                             = "1970-01-01T00:00:00",
            until                : str                             = "2038-01-19T03:14:07",
            by                   : Optional[Person]                = None,
            holder_legal_name    : Optional[str]                   = None,
            ietfer_contact_email : Optional[str]                   = None,
            ietfer_name          : Optional[str]                   = None,
            state                : Optional[IPRDisclosureState]    = None,
            submitter_email      : Optional[str]                   = None,
            submitter_name       : Optional[str]                   = None) -> Iterator[HolderIPRDisclosure]:
        url = ThirdPartyIPRDisclosureURI("/api/v1/ipr/thirdpartyiprdisclosure/")
        url.params["time__gte"] = since
        url.params["time__lt"]  = until
        if by is not None:
            url.params["by"] = by.id
        if holder_legal_name is not None:
            url.params["holder_legal_name"] = holder_legal_name
        if ietfer_contact_email is not None:
            url.params["ietfer_contact_email"] = ietfer_contact_email
        if ietfer_name is not None:
            url.params["ietfer_name"] = ietfer_name
        if state is not None:
            url.params["state"] = state.slug
        if submitter_email is not None:
            url.params["submitter_email"] = submitter_email
        if submitter_name is not None:
            url.params["submitter_name"] = submitter_name
        return self._retrieve_multi(url, HolderIPRDisclosure)


    # ----------------------------------------------------------------------------------------------------------------------------
    # Datatracker API endpoints returning information about liaison statements:
    #
    #   https://datatracker.ietf.org/api/v1/liaisons/liaisonstatement/
    #   https://datatracker.ietf.org/api/v1/liaisons/liaisonstatementevent/
    #   https://datatracker.ietf.org/api/v1/liaisons/liaisonstatementgroupcontacts/
    #   https://datatracker.ietf.org/api/v1/liaisons/relatedliaisonstatement/
    #   https://datatracker.ietf.org/api/v1/liaisons/liaisonstatementattachment/
    #
    #   https://datatracker.ietf.org/api/v1/name/liaisonstatementeventtypename/
    #   https://datatracker.ietf.org/api/v1/name/liaisonstatementpurposename/
    #   https://datatracker.ietf.org/api/v1/name/liaisonstatementstate/
    #   https://datatracker.ietf.org/api/v1/name/liaisonstatementtagname/

    # FIXME: implement these


    # ----------------------------------------------------------------------------------------------------------------------------
    # Datatracker API endpoints returning information about reviews:
    #
    # * https://datatracker.ietf.org/api/v1/review/reviewassignment/
    # * https://datatracker.ietf.org/api/v1/review/reviewrequest/
    # * https://datatracker.ietf.org/api/v1/review/reviewwish/
    # * https://datatracker.ietf.org/api/v1/review/reviewteamsettings/
    # * https://datatracker.ietf.org/api/v1/review/nextreviewerinteam/
    # * https://datatracker.ietf.org/api/v1/review/historicalunavailableperiod/
    # * https://datatracker.ietf.org/api/v1/review/historicalreviewrequest/
    # * https://datatracker.ietf.org/api/v1/review/reviewersettings/
    # * https://datatracker.ietf.org/api/v1/review/unavailableperiod/
    # * https://datatracker.ietf.org/api/v1/review/historicalreviewersettings/
    # * https://datatracker.ietf.org/api/v1/review/historicalreviewassignment/
    # * https://datatracker.ietf.org/api/v1/review/reviewsecretarysettings/

    # * https://datatracker.ietf.org/api/v1/name/reviewresultname/
    # * https://datatracker.ietf.org/api/v1/name/reviewassignmentstatename/
    # * https://datatracker.ietf.org/api/v1/name/reviewrequeststatename/
    # * https://datatracker.ietf.org/api/v1/name/reviewtypename/

    def review_assignment_state(self, review_assignment_state_uri: ReviewAssignmentStateURI) -> Optional[ReviewAssignmentState]:
        return self._retrieve(review_assignment_state_uri, ReviewAssignmentState)


    def review_assignment_state_from_slug(self, slug: str) -> Optional[ReviewAssignmentState]:
        return self._retrieve(ReviewAssignmentStateURI(F"/api/v1/name/reviewassignmentstatename/{slug}/"), ReviewAssignmentState)


    def review_assignment_states(self) -> Iterator[ReviewAssignmentState]:
        return self._retrieve_multi(ReviewAssignmentStateURI("/api/v1/name/reviewassignmentstatename/"), ReviewAssignmentState)


    def review_result_type(self, review_result_uri: ReviewResultTypeURI) -> Optional[ReviewResultType]:
        return self._retrieve(review_result_uri, ReviewResultType)


    def review_result_type_from_slug(self, slug: str) -> Optional[ReviewResultType]:
        return self._retrieve(ReviewResultTypeURI(F"/api/v1/name/reviewresultname/{slug}/"), ReviewResultType)


    def review_result_types(self) -> Iterator[ReviewResultType]:
        return self._retrieve_multi(ReviewResultTypeURI("/api/v1/name/reviewresultname/"), ReviewResultType)


    def review_type(self, review_type_uri: ReviewTypeURI) -> Optional[ReviewType]:
        return self._retrieve(review_type_uri, ReviewType)


    def review_type_from_slug(self, slug: str) -> Optional[ReviewType]:
        return self._retrieve(ReviewTypeURI(F"/api/v1/name/reviewtypename/{slug}/"), ReviewType)


    def review_types(self) -> Iterator[ReviewType]:
        return self._retrieve_multi(ReviewTypeURI("/api/v1/name/reviewtypename/"), ReviewType)


    def review_request_state(self, review_request_state_uri: ReviewRequestStateURI) -> Optional[ReviewRequestState]:
        return self._retrieve(review_request_state_uri, ReviewRequestState)


    def review_request_state_from_slug(self, slug: str) -> Optional[ReviewRequestState]:
        return self._retrieve(ReviewRequestStateURI(F"/api/v1/name/reviewrequeststatename/{slug}/"), ReviewRequestState)


    def review_request_states(self) -> Iterator[ReviewRequestState]:
        return self._retrieve_multi(ReviewRequestStateURI("/api/v1/name/reviewrequeststatename/"), ReviewRequestState)


    def review_request(self, review_request_uri: ReviewRequestURI) -> Optional[ReviewRequest]:
        return self._retrieve(review_request_uri, ReviewRequest)


    def review_requests(self,
            since         : str                          = "1970-01-01T00:00:00",
            until         : str                          = "2038-01-19T03:14:07",
            doc           : Optional[Document]           = None,
            requested_by  : Optional[Person]             = None,
            state         : Optional[ReviewRequestState] = None,
            team          : Optional[Group]              = None,
            type          : Optional[ReviewType]         = None) -> Iterator[ReviewRequest]:
        url = ReviewRequestURI("/api/v1/review/reviewrequest/")
        url.params["time__gte"] = since
        url.params["time__lt"]  = until
        if doc is not None:
            url.params["doc"] = doc.id
        if requested_by is not None:
            url.params["requested_by"] = requested_by.id
        if state is not None:
            url.params["state"] = state.slug
        if team is not None:
            url.params["team"] = team.id
        if type is not None:
            url.params["type"] = type.slug
        return self._retrieve_multi(url, ReviewRequest)


    def review_assignment(self, review_assignment_uri: ReviewAssignmentURI) -> Optional[ReviewAssignment]:
        return self._retrieve(review_assignment_uri, ReviewAssignment)


    def review_assignments(self,
            assigned_since         : str                             = "1970-01-01T00:00:00",
            assigned_until         : str                             = "2038-01-19T03:14:07",
            completed_since        : str                             = "1970-01-01T00:00:00",
            completed_until        : str                             = "2038-01-19T03:14:07",
            result                 : Optional[ReviewResultType]      = None,
            review_request         : Optional[ReviewRequest]         = None,
            reviewer               : Optional[Email]                 = None,
            state                  : Optional[ReviewAssignmentState] = None) -> Iterator[ReviewAssignment]:
        url = ReviewAssignmentURI("/api/v1/review/reviewassignment/")
        url.params["assigned_on__gt"]       = assigned_since
        url.params["assigned_on__lt"]       = assigned_until
        url.params["completed_on__gt"]      = completed_since
        url.params["completed_on__lt"]      = completed_until
        if result is not None:
            url.params["result"] = result.slug
        if review_request is not None:
            url.params["review_request"] = review_request.id
        if reviewer is not None:
            url.params["reviewer"] = reviewer.address
        if state is not None:
            url.params["state"] = state.slug
        return self._retrieve_multi(url, ReviewAssignment)


    def review_wish(self, review_wish_uri: ReviewWishURI) -> Optional[ReviewWish]:
        return self._retrieve(review_wish_uri, ReviewWish)


    def review_wishes(self,
            since         : str                          = "1970-01-01T00:00:00",
            until         : str                          = "2038-01-19T03:14:07",
            doc           : Optional[Document]           = None,
            person        : Optional[Person]             = None,
            team          : Optional[Group]              = None) -> Iterator[ReviewWish]:
        url = ReviewWishURI("/api/v1/review/reviewwish/")
        url.params["time__gte"]       = since
        url.params["time__lt"]       = until
        if doc is not None:
            url.params["doc"] = doc.id
        if person is not None:
            url.params["person"] = person.id
        if team is not None:
            url.params["team"] = team.id
        return self._retrieve_multi(url, ReviewWish)


    def historical_unavailable_period(self, historical_unavailable_period_uri: HistoricalUnavailablePeriodURI) -> Optional[HistoricalUnavailablePeriod]:
        return self._retrieve(historical_unavailable_period_uri, HistoricalUnavailablePeriod)


    def historical_unavailable_periods(self,
            history_type  : Optional[str]                = None,
            id            : Optional[int]                = None,
            person        : Optional[Person]             = None,
            team          : Optional[Group]              = None) -> Iterator[HistoricalUnavailablePeriod]:
        url = HistoricalUnavailablePeriodURI("/api/v1/review/historicalunavailableperiod/")
        if history_type is not None:
            url.params["history_type"] = history_type
        if id is not None:
            url.params["id"] = id
        if person is not None:
            url.params["person"] = person.id
        if team is not None:
            url.params["team"] = team.id
        return self._retrieve_multi(url, HistoricalUnavailablePeriod)


    def historical_review_request(self, historical_review_request_uri: HistoricalReviewRequestURI) -> Optional[HistoricalReviewRequest]:
        return self._retrieve(historical_review_request_uri, HistoricalReviewRequest)


    def historical_review_requests(self,
            since         : str                          = "1970-01-01T00:00:00",
            until         : str                          = "2038-01-19T03:14:07",
            history_since : str                          = "1970-01-01T00:00:00",
            history_until : str                          = "2038-01-19T03:14:07",
            history_type  : str                          = None,
            id            : int                          = None,
            doc           : Optional[Document]           = None,
            requested_by  : Optional[Person]             = None,
            state         : Optional[ReviewRequestState] = None,
            team          : Optional[Group]              = None,
            type          : Optional[ReviewType]         = None) -> Iterator[HistoricalReviewRequest]:
        url = HistoricalReviewRequestURI("/api/v1/review/historicalreviewrequest/")
        url.params["time__gte"]         = since
        url.params["time__lt"]         = until
        url.params["history_date__gt"] = history_since
        url.params["history_date__lt"] = history_until
        if doc is not None:
            url.params["doc"] = doc.id
        if requested_by is not None:
            url.params["requested_by"] = requested_by.id
        if state is not None:
            url.params["state"] = state.slug
        if team is not None:
            url.params["team"] = team.id
        if type is not None:
            url.params["type"] = type.slug
        return self._retrieve_multi(url, HistoricalReviewRequest)


    def next_reviewer_in_team(self, next_reviewer_in_team_uri: NextReviewerInTeamURI) -> Optional[NextReviewerInTeam]:
        return self._retrieve(next_reviewer_in_team_uri, NextReviewerInTeam)


    def next_reviewers_in_teams(self,
            team          : Optional[Group] = None) -> Iterator[NextReviewerInTeam]:
        url = NextReviewerInTeamURI("/api/v1/review/nextreviewerinteam/")
        if team is not None:
            url.params["team"] = team.id
        return self._retrieve_multi(url, NextReviewerInTeam)


    def review_team_settings(self, review_team_settings_uri: ReviewTeamSettingsURI) -> Optional[ReviewTeamSettings]:
        return self._retrieve(review_team_settings_uri, ReviewTeamSettings)


    def review_team_settings_all(self,
            group                    : Optional[Group] = None) -> Iterator[ReviewTeamSettings]:
        url = ReviewTeamSettingsURI("/api/v1/review/reviewteamsettings/")
        if group is not None:
            url.params["group"] = group.id
        return self._retrieve_multi(url, ReviewTeamSettings)


    def reviewer_settings(self, reviewer_settings_uri: ReviewerSettingsURI) -> Optional[ReviewerSettings]:
        return self._retrieve(reviewer_settings_uri, ReviewerSettings)


    def reviewer_settings_all(self,
            person        : Optional[Person]             = None,
            team          : Optional[Group]              = None) -> Iterator[ReviewerSettings]:
        url = ReviewerSettingsURI("/api/v1/review/reviewersettings/")
        if person is not None:
            url.params["person"] = person.id
        if team is not None:
            url.params["team"] = team.id
        return self._retrieve_multi(url, ReviewerSettings)


    def unavailable_period(self, unavailable_period_uri: UnavailablePeriodURI) -> Optional[UnavailablePeriod]:
        return self._retrieve(unavailable_period_uri, UnavailablePeriod)


    def unavailable_periods(self,
            person        : Optional[Person]             = None,
            team          : Optional[Group]              = None) -> Iterator[UnavailablePeriod]:
        url = UnavailablePeriodURI("/api/v1/review/unavailableperiod/")
        if person is not None:
            url.params["person"] = person.id
        if team is not None:
            url.params["team"] = team.id
        return self._retrieve_multi(url, UnavailablePeriod)


    def historical_reviewer_settings(self, historical_reviewer_settings_uri: HistoricalReviewerSettingsURI) -> Optional[HistoricalReviewerSettings]:
        return self._retrieve(historical_reviewer_settings_uri, HistoricalReviewerSettings)


    def historical_reviewer_settings_all(self,
            history_since : str                          = "1970-01-01T00:00:00",
            history_until : str                          = "2038-01-19T03:14:07",
            id            : int                          = None,
            person        : Optional[Person]             = None,
            team          : Optional[Group]              = None) -> Iterator[HistoricalReviewerSettings]:
        url = HistoricalReviewerSettingsURI("/api/v1/review/historicalreviewersettings/")
        url.params["history_date__gt"]       = history_since
        url.params["history_date__lt"]       = history_until
        if id is not None:
            url.params["id"] = id
        if person is not None:
            url.params["person"] = person.id
        if team is not None:
            url.params["team"] = team.id
        return self._retrieve_multi(url, HistoricalReviewerSettings)


    def historical_review_assignment(self, historical_review_assignment_uri: HistoricalReviewAssignmentURI) -> Optional[HistoricalReviewAssignment]:
        return self._retrieve(historical_review_assignment_uri, HistoricalReviewAssignment)


    def historical_review_assignments(self,
            assigned_since         : str                             = "1970-01-01T00:00:00",
            assigned_until         : str                             = "2038-01-19T03:14:07",
            completed_since        : str                             = "1970-01-01T00:00:00",
            completed_until        : str                             = "2038-01-19T03:14:07",
            id                     : int                             = None,
            result                 : Optional[ReviewResultType]      = None,
            review_request         : Optional[ReviewRequest]         = None,
            reviewer               : Optional[Email]                 = None,
            state                  : Optional[ReviewAssignmentState] = None) -> Iterator[HistoricalReviewAssignment]:
        url = HistoricalReviewAssignmentURI("/api/v1/review/historicalreviewassignment/")
        url.params["assigned_on__gt"]       = assigned_since
        url.params["assigned_on__lt"]       = assigned_until
        url.params["completed_on__gt"]      = completed_since
        url.params["completed_on__lt"]      = completed_until
        if id is not None:
            url.params["id"] = id
        if result is not None:
            url.params["result"] = result.slug
        if review_request is not None:
            url.params["review_request"] = review_request.id
        if reviewer is not None:
            url.params["reviewer"] = reviewer.address
        if state is not None:
            url.params["state"] = state.slug
        return self._retrieve_multi(url, HistoricalReviewAssignment)


    def review_secretary_settings(self, review_secretary_settings_uri: ReviewSecretarySettingsURI) -> Optional[ReviewSecretarySettings]:
        return self._retrieve(review_secretary_settings_uri, ReviewSecretarySettings)


    def review_secretary_settings_all(self,
            person        : Optional[Person]             = None,
            team          : Optional[Group]              = None) -> Iterator[ReviewSecretarySettings]:
        url = ReviewSecretarySettingsURI("/api/v1/review/reviewsecretarysettings/")
        if person is not None:
            url.params["person"] = person.id
        if team is not None:
            url.params["team"] = team.id
        return self._retrieve_multi(url, ReviewSecretarySettings)


    # ----------------------------------------------------------------------------------------------------------------------------
    # Datatracker API endpoints returning information about mailing lists:
    #
    #   https://datatracker.ietf.org/api/v1/mailinglists/list/
    #   https://datatracker.ietf.org/api/v1/mailinglists/subscribed/

    def email_list(self, email_list_uri: EmailListURI) -> Optional[EmailList]:
        return self._retrieve(email_list_uri, EmailList)


    def email_lists(self, name : Optional[str] = None) -> Iterator[EmailList]:
        url = EmailListURI("/api/v1/mailinglists/list/")
        if name is not None:
            url.params["name"] = name
        return self._retrieve_multi(url, EmailList)


    def email_list_subscriptions(self,
            email_addr : Optional[str] = None,
            email_list : Optional[EmailList] = None) -> Iterator[EmailListSubscriptions]:
        url = EmailListSubscriptionsURI("/api/v1/mailinglists/subscribed/")
        if email_addr is not None:
            url.params["email"] = email_addr
        if email_list is not None:
            url.params["lists"] = email_list.id
        return self._retrieve_multi(url, EmailListSubscriptions)


    # ----------------------------------------------------------------------------------------------------------------------------
    # Datatracker API endpoints returning information about names:
    #
    # FIXME: move these into the appropriate place
    #
    #   https://datatracker.ietf.org/api/v1/name/dbtemplatetypename/
    #   https://datatracker.ietf.org/api/v1/name/docrelationshipname/
    #   https://datatracker.ietf.org/api/v1/name/doctagname/
    #   https://datatracker.ietf.org/api/v1/name/docurltagname/
    #   https://datatracker.ietf.org/api/v1/name/formallanguagename/
    #   https://datatracker.ietf.org/api/v1/name/stdlevelname/
    #   https://datatracker.ietf.org/api/v1/name/groupmilestonestatename/
    #   https://datatracker.ietf.org/api/v1/name/feedbacktypename/
    #   https://datatracker.ietf.org/api/v1/name/topicaudiencename/
    #   https://datatracker.ietf.org/api/v1/name/nomineepositionstatename/
    #   https://datatracker.ietf.org/api/v1/name/constraintname/
    #   https://datatracker.ietf.org/api/v1/name/docremindertypename/
    #   https://datatracker.ietf.org/api/v1/name/intendedstdlevelname/
    #   https://datatracker.ietf.org/api/v1/name/draftsubmissionstatename/
    #   https://datatracker.ietf.org/api/v1/name/rolename/

    # ----------------------------------------------------------------------------------------------------------------------------
    # Datatracker API endpoints returning information about countries:
    # * https://datatracker.ietf.org/api/v1/stats/countryalias/
    # * https://datatracker.ietf.org/api/v1/name/countryname/
    # * https://datatracker.ietf.org/api/v1/name/continentname/

    def continent(self, continent_uri : ContinentURI) -> Optional[Continent]:
        return self._retrieve(continent_uri, Continent)


    def continent_from_slug(self, slug : str) -> Optional[Continent]:
        return self._retrieve(ContinentURI(F"/api/v1/name/continentname/{slug}/"), Continent)


    def continents(self) -> Iterator[Continent]:
        url = ContinentURI("/api/v1/name/continentname/")
        return self._retrieve_multi(url, Continent)


    def country(self, country_uri: CountryURI) -> Optional[Country]:
        return self._retrieve(country_uri, Country)


    def country_from_slug(self, slug : str) -> Optional[Country]:
        return self._retrieve(CountryURI(F"/api/v1/name/countryname/{slug}/"), Country)


    def countries(self,
                  continent_slug : Optional[str]  = None,
                  in_eu          : Optional[bool] = None,
                  slug           : Optional[str]  = None,
                  name           : Optional[str]  = None) -> Iterator[Country]:
        url = CountryURI("/api/v1/name/countryname/")
        if continent_slug is not None:
            url.params["continent"] = continent_slug
        if in_eu is not None:
            url.params["in_eu"] = in_eu
        if slug is not None:
            url.params["slug"] = slug
        if name is not None:
            url.params["name"] = name
        return self._retrieve_multi(url, Country)


    def country_alias(self, country_alias_uri : CountryAliasURI) -> Optional[CountryAlias]:
        return self._retrieve(country_alias_uri, CountryAlias)


    def country_aliases(self, alias : str) -> Iterator[CountryAlias]:
        url = CountryAliasURI("/api/v1/stats/countryalias/")
        url.params["alias"] = alias
        return self._retrieve_multi(url, CountryAlias)


    # ----------------------------------------------------------------------------------------------------------------------------
    # Datatracker API endpoints returning information about statistics:
    #
    #   https://datatracker.ietf.org/api/v1/stats/affiliationalias/
    #   https://datatracker.ietf.org/api/v1/stats/affiliationignoredending/
    #   https://datatracker.ietf.org/api/v1/stats/meetingregistration/

    def meeting_registration(self, meeting_registration_uri: MeetingRegistrationURI) -> Optional[MeetingRegistration]:
        return self._retrieve(meeting_registration_uri, MeetingRegistration)


    def meeting_registrations(self,
                affiliation   : Optional[str]             = None,
                attended      : Optional[bool]            = None,
                country_code  : Optional[str]             = None,
                email         : Optional[str]             = None,
                first_name    : Optional[str]             = None,
                last_name     : Optional[str]             = None,
                meeting       : Optional[Meeting]         = None,
                person        : Optional[Person]          = None,
                reg_type      : Optional[str]             = None,
                ticket_type   : Optional[str]             = None) -> Iterator[MeetingRegistration]:
        url = MeetingRegistrationURI("/api/v1/stats/meetingregistration/")
        if affiliation is not None:
            url.params["affiliation"] = affiliation
        if attended is not None:
            url.params["attended"] = attended
        if country_code is not None:
            url.params["country_code"] = country_code
        if email is not None:
            url.params["email"] = email
        if first_name is not None:
            url.params["first_name"] = first_name
        if last_name is not None:
            url.params["last_name"] = last_name
        if meeting is not None:
            url.params["meeting"] = meeting.id
        if person is not None:
            url.params["person"] = person.id
        if reg_type is not None:
            url.params["reg_type"] = reg_type
        if ticket_type is not None:
            url.params["ticket_type"] = ticket_type
        return self._retrieve_multi(url, MeetingRegistration)


    # ----------------------------------------------------------------------------------------------------------------------------
    # Datatracker API endpoints returning information about messages:
    #
    # * https://datatracker.ietf.org/api/v1/message/announcementfrom/
    # * https://datatracker.ietf.org/api/v1/message/message/
    # - https://datatracker.ietf.org/api/v1/message/messageattachment/ [not used]
    # * https://datatracker.ietf.org/api/v1/message/sendqueue/

    def announcement_from(self, announcement_from_uri: AnnouncementFromURI) -> Optional[AnnouncementFrom]:
        return self._retrieve(announcement_from_uri, AnnouncementFrom)


    def announcements_from(self,
                address : Optional[str]          = None,
                group   : Optional[Group]        = None,
                name    : Optional[RoleName]     = None) -> Iterator[AnnouncementFrom]:
        url = AnnouncementFromURI("/api/v1/message/announcementfrom/")
        if address is not None:
            url.params["address"] = address
        if group is not None:
            url.params["group"] = group.id
        if name is not None:
            url.params["name"] = name.slug
        return self._retrieve_multi(url, AnnouncementFrom)


    #def message(self, message_uri: MessageURI) -> Optional[Message]:
    #    return self._retrieve(message_uri, Message)


    #def messages(self,
    #            since : str                           = "1970-01-01T00:00:00",
    #            until : str                           = "2038-01-19T03:14:07",
    #            by               : Optional[Person]   = None,
    #            frm              : Optional[str]      = None,
    #            related_doc      : Optional[Document] = None,
    #            subject_contains : Optional[str]      = None,
    #            body_contains    : Optional[str]      = None) -> Iterator[Message]:
    #    url = MessageURI("/api/v1/message/message/")
    #    url.params["time__gte"]       = since
    #    url.params["time__lt"]       = until
    #    if by is not None:
    #        url.params["by"] = by.id
    #    if frm is not None:
    #        url.params["frm"] = frm
    #    if related_doc is not None:
    #        url.params["related_docs__contains"] = related_doc.id
    #    if subject_contains is not None:
    #        url.params["subject__contains"] = subject_contains
    #    if body_contains is not None:
    #        url.params["body__contains"] = body_contains
    #    return self._retrieve_multi(url, Message)


    def send_queue_entry(self, send_queue_uri: SendQueueURI) -> Optional[SendQueueEntry]:
        return self._retrieve(send_queue_uri, SendQueueEntry)


    def send_queue(self,
                since   : str                = "1970-01-01T00:00:00",
                until   : str                = "2038-01-19T03:14:07",
                by      : Optional[Person]   = None,
                message : Optional[Message]  = None) -> Iterator[SendQueueEntry]:
        url = SendQueueURI("/api/v1/message/sendqueue/")
        url.params["time__gte"] = since
        url.params["time__lt"]  = until
        if by is not None:
            url.params["by"] = by.id
        if message is not None:
            url.params["message"] = message.id
        return self._retrieve_multi(url, SendQueueEntry)


# =================================================================================================================================
# vim: set tw=0 ai:
