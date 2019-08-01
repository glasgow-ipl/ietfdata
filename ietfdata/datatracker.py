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

from typing      import List, Optional, Tuple, Dict, Iterator
from dataclasses import dataclass
from pavlova     import Pavlova

import datetime
import glob
import json
import requests
import unittest
import re

# =================================================================================================================================
# Classes to represent the JSON-serialised objects returned by the Datatracker API:

@dataclass
class Person:
    resource_uri    : str
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

@dataclass
class Email:
    resource_uri : str
    address      : str
    person       : str
    time         : str
    origin       : str
    primary      : bool
    active       : bool

@dataclass
class Document:
    resource_uri       : str
    name               : str
    title              : str
    pages              : Optional[int]
    words              : Optional[int]
    time               : str
    notify             : str
    expires            : Optional[str]
    type               : str
    rev                : str
    abstract           : str
    internal_comments  : str
    order              : int
    note               : str
    states             : List[str]
    ad                 : Optional[str]
    shepherd           : Optional[str]
    group              : Optional[str]
    stream             : Optional[str]
    rfc                : Optional[int]
    std_level          : Optional[str]
    intended_std_level : Optional[str]
    submissions        : List[str]
    tags               : List[str]
    uploaded_filename  : str
    external_url       : str
    
    def derive_document_url(self) -> str:
        if self.type == "/api/v1/name/doctypename/agenda/":
            # FIXME: This doesn't work for interim meetings
            # FIXME: This doesn't work for PDF agenda files
            meeting = self.name.split("-")[1]
            document_url = "https://datatracker.ietf.org/meeting/" + meeting + "/materials/" + self.uploaded_filename
        elif self.type == "/api/v1/name/doctypename/minutes/":
            meeting = self.name.split("-")[1]
            document_url = "https://datatracker.ietf.org/meeting/" + meeting + "/materials/" + self.uploaded_filename
        elif self.type == "/api/v1/name/doctypename/bluesheets/":
            meeting = self.name.split("-")[1]
            document_url = "https://www.ietf.org/proceedings/" + meeting + "/bluesheets/" + self.uploaded_filename
        elif self.type == "/api/v1/name/doctypename/charter/":
            document_url = "https://www.ietf.org/charter/"     + self.name + "-" + self.rev + ".txt"
        elif self.type == "/api/v1/name/doctypename/conflrev/":
            document_url = "https://www.ietf.org/cr/"          + self.name + "-" + self.rev + ".txt"
        elif self.type == "/api/v1/name/doctypename/draft/":
            document_url = "https://www.ietf.org/archive/id/"  + self.name + "-" + self.rev + ".txt"
        elif self.type == "/api/v1/name/doctypename/slides/":
            meeting = self.name.split("-")[1]
            document_url = "https://www.ietf.org/proceedings/" + meeting + "/slides/" + self.uploaded_filename
        elif self.type == "/api/v1/name/doctypename/statchg/":
            document_url = "https://www.ietf.org/sc/"          + self.name + "-" + self.rev + ".txt"
        elif self.type == "/api/v1/name/doctypename/liaison/":
            document_url = "https://www.ietf.org/lib/dt/documents/LIAISON/" + self.uploaded_filename
        elif self.type == "/api/v1/name/doctypename/liai-att/":
            document_url = "https://www.ietf.org/lib/dt/documents/LIAISON/" + self.uploaded_filename
        elif self.type == "/api/v1/name/doctypename/recording/":
            document_url = self.external_url
        elif self.type == "/api/v1/name/doctypename/review/":
            # FIXME: This points to the formatted HTML page containing the message, but we really want the raw message
            document_url = "https://datatracker.ietf.org/doc/" + self.name
        elif self.type == "/api/v1/name/doctypename/shepwrit/":
            document_url = self.external_url
        else:
            raise NotImplementedError
        return document_url

@dataclass
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

@dataclass
class StateType:
    resource_uri : str
    label        : str
    slug         : str

@dataclass
class DocumentType:
    resource_uri : str
    name         : str
    used         : bool
    prefix       : str
    slug         : str
    desc         : str
    order        : int

@dataclass
class Stream:
    resource_uri : str
    name         : str
    desc         : str
    used         : bool
    slug         : str
    order        : int

@dataclass
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

@dataclass
class GroupState:
    resource_uri   : str
    slug           : str
    desc           : str
    name           : str
    used           : bool
    order          : int

@dataclass
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

# =================================================================================================================================
# A class to represent the datatracker:

class DataTracker:
    """
    A class for interacting with the IETF DataTracker.
    """
    def __init__(self):
        self.session      = requests.Session()
        self.base_url     = "https://datatracker.ietf.org"


    def __del__(self):
        self.session.close()


    # Datatracker API endpoints returning information about people:
    # * https://datatracker.ietf.org/api/v1/person/person/                  - list of people
    # * https://datatracker.ietf.org/api/v1/person/person/20209/            - info about person 20209
    # * https://datatracker.ietf.org/api/v1/person/email/csp@csperkins.org/ - map from email address to person
    #   https://datatracker.ietf.org/api/v1/person/historicalperson/        - ???
    #   https://datatracker.ietf.org/api/v1/person/historicalemail/         - ???
    #   https://datatracker.ietf.org/api/v1/person/alias/                   - ???

    def email(self, email: str) -> Optional[Email]:
        """
        Lookup information about an email address in the datatracker.

        Parameters:
           email : the email address to lookup

        Returns:
            An Email object
        """
        response = self.session.get(self.base_url + "/api/v1/person/email/" + email + "/", verify=True)
        if response.status_code == 200:
            return Pavlova().from_mapping(response.json(), Email)
        else:
            return None


    def person_from_email(self, email: str) -> Optional[Person]:
        """
        Lookup a person in the datatracker based on their email address.

        Parameters:
            email : the email address to lookup

        Returns:
            A Person object
        """
        return self.person("/api/v1/person/email/" + email + "/")


    def person(self, person_uri: str) -> Optional[Person]:
        """
        Lookup a Person in the datatracker.

        Parameters:
            person_uri : a URI of the form "/api/v1/person/person/20209/" or "api/v1/person/email/csp@csperkins.org/"

        Returns:
            A Person object
        """
        assert person_uri.startswith("/api/v1/person/")
        assert person_uri.endswith("/")
        if person_uri.startswith("/api/v1/person/person/"):
            response = self.session.get(self.base_url + person_uri, verify=True)
            if response.status_code == 200:
                return Pavlova().from_mapping(response.json(), Person)
            else:
                return None
        elif person_uri.startswith("/api/v1/person/email/"):
            response = self.session.get(self.base_url + person_uri, verify=True)
            if response.status_code == 200:
                return self.person(response.json()["person"])
            else:
                return None
        else:
            raise RuntimeError


    def people(self, since="1970-01-01T00:00:00", until="2038-01-19T03:14:07", name_contains=None) -> Iterator[Person]:
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
        url = self.base_url + "/api/v1/person/person/?time__gt=" + since + "&time__lt=" + until
        if name_contains is not None:
            url = url + "&name__contains=" + name_contains
        while url is not None:
            r = self.session.get(url, verify=True)
            meta = r.json()['meta']
            objs = r.json()['objects']
            url  = meta['next']
            for obj in objs:
                yield obj


    # Datatracker API endpoints returning information about documents:
    # * https://datatracker.ietf.org/api/v1/doc/document/                        - list of documents
    # * https://datatracker.ietf.org/api/v1/doc/document/draft-ietf-avt-rtp-new/ - info about document

    def document(self, document_uri: str) -> Optional[Document]:
        # FIXME: complete documentation
        # FIXME: add method relating to std_level
        # FIXME: add method relating to intended_std_level
        # FIXME: add method relating to submissions
        # FIXME: add method relating to tags
        """
        Lookup metadata about a document in the datatracker.

        Parameters:
            document_uri : a URI of the form "/api/v1/doc/document/draft-ietf-avt-rtp-new/"

        Returns:
            A Document object
        """
        assert document_uri.startswith("/api/v1/doc/document/")
        assert document_uri.endswith("/")
        response = self.session.get(self.base_url + document_uri, verify=True)
        if response.status_code == 200:
            doc = Pavlova().from_mapping(response.json(), Document)
            assert doc.resource_uri.startswith("/api/v1/doc/document/")
            assert doc.ad       is None or doc.ad.startswith("/api/v1/person/person")
            assert doc.shepherd is None or doc.shepherd.startswith("/api/v1/person/email")
            return doc
        else:
            return None


    def documents(self, since="1970-01-01T00:00:00", until="2038-01-19T03:14:07", doctype=None, group_uri=None) -> Iterator[Document]:
        """
        A generator that returns all documents recorded in the datatracker.
        As of 29 April 2018, approximately 84000 documents are recorded.

        Parameters:
           since     -- Only return people with timestamp after this
           until     -- Only return people with timestamp before this
           doctype   -- The 'slug' field from one of the dicts returned by the
                        document_types() method; constrains the results to that
                        particular state type.
           group_uri -- Constrain the results to documents from the specified group.

        Returns:
            An iterator, where each element is as returned by the document() method
        """
        url = self.base_url + "/api/v1/doc/document/?time__gt=" + since + "&time__lt=" + until 
        if doctype != None:
            url = url + "&type=" + doctype
        if group_uri != None:
            url = url + "&group=" + group_uri
        while url != None:
            r = self.session.get(url, verify=True)
            objs = r.json()['objects']
            for doc in objs:
                assert doc["resource_uri"].startswith("/api/v1/doc/document/")
                assert doc[      "ad"] is None or doc[      "ad"].startswith("/api/v1/person/person/")
                assert doc["shepherd"] is None or doc["shepherd"].startswith("/api/v1/person/email/")
                #self._derive_document_url(doc)
                yield doc
            meta = r.json()['meta']
            if meta['next'] == None:
                url = None
            else:
                url  = self.base_url + meta['next']

    # Datatracker API endpoints returning information about document aliases:
    # * https://datatracker.ietf.org/api/v1/doc/docalias/?name=/                 - draft that became the given RFC

    def documents_from_alias(self, alias: str) -> Iterator[Document]:
        """
        Returns the documents that correspond to the specified alias.

        Parameters:
            alias -- The alias to lookup, for example "rfc3550", "std68", "bcp25", "draft-ietf-quic-transport"

        Returns:
            A list of Document objects
        """
        url = self.base_url + "/api/v1/doc/docalias/?name=" + alias
        while url != None:
            r = self.session.get(url, verify=True)
            objs = r.json()['objects']
            for doc in objs:
                assert doc["resource_uri"].startswith("/api/v1/doc/docalias/")
                assert doc[    "document"].startswith("/api/v1/doc/document/")
                yield self.document(doc["document"])
            meta = r.json()['meta']
            if meta['next'] == None:
                url = None
            else:
                url  = self.base_url + meta['next']


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
            return docs[0]
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
            return docs[0]
        else:
            raise RuntimeError


    def documents_from_bcp(self, bcp: str) -> List[Document]:
        """
        Returns the document that became the specified BCP.

        Parameters:
            bcp -- The BCP to lookup (e.g., "bcp205" or "BCP205")

        Returns:
            A list of Document objects
        """
        assert bcp.lower().startswith("bcp")
        return list(self.documents_from_alias(bcp.lower()))


    def documents_from_std(self, std: str) -> List[Document]:
        """
        Returns the document that became the specified STD.

        Parameters:
            std -- The STD to lookup (e.g., "std68" or "STD68")

        Returns:
            A list of Document objects
        """
        assert std.lower().startswith("std")
        return list(self.documents_from_alias(std.lower()))


    # Datatracker API endpoints returning information about document states:
    # * https://datatracker.ietf.org/api/v1/doc/state/                           - Types of state a document can be in
    # * https://datatracker.ietf.org/api/v1/doc/statetype/                       - Possible types of state for a document

    def document_state(self, state_uri: str):
        """
        Information about the state of a document.

        Parameters:
           state_uri -- A URI representing a document state, e.g., as returned
                        in the states entry of the dict returned by document()

        Returns:
            A State object
        """
        assert state_uri.startswith("/api/v1/doc/state/") and state_uri.endswith("/")
        response = self.session.get(self.base_url + state_uri, verify=True)
        if response.status_code == 200:
            return Pavlova().from_mapping(response.json(), State)
        else:
            return None


    def document_states(self, statetype=None):
        """
        A generator returning the possible states a document can be in.

        Parameters:
           statetype -- The 'slug' field from one of the dicts returned by the
                        document_state_types() method; constrains the results
                        to that particular state type.

        Returns:
            A sequence of Document objects, as returned by document_state()
        """
        api_url   = "/api/v1/doc/state/"
        if statetype is not None:
            api_url = api_url + "?type=" + statetype
        while api_url != None:
            r = self.session.get(self.base_url + api_url, verify=True)
            meta = r.json()['meta']
            objs = r.json()['objects']
            api_url = meta['next']
            for obj in objs:
                yield Pavlova().from_mapping(obj, State)


    def document_state_types(self):
        """
        A generator returning possible state types for a document.
        These are the possible values of the 'type' field in the 
        output of document_state(), or the statetype parameter to
        document_states().

        Returns:
           A sequence of StateType objects
        """
        api_url   = "/api/v1/doc/statetype/"
        while api_url != None:
            r = self.session.get(self.base_url + api_url, verify=True)
            meta = r.json()['meta']
            objs = r.json()['objects']
            api_url = meta['next']
            for obj in objs:
                yield Pavlova().from_mapping(obj, StateType)


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

    def submission(self, submission_uri):
        """
        Information about a document submission.

        Parameters:
           submission_uri -- A submission URI of the form /api/v1/submit/submission/2402/                             

        Returns:
            A Submission object
        """

        assert submission_uri.startswith("/api/v1/submit/submission/")
        assert submission_uri.endswith("/")
        response = self.session.get(self.base_url + submission_uri, verify=True)
        if response.status_code == 200:
            return Pavlova().from_mapping(response.json(), Submission)
        else:
            return None

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
    #   https://datatracker.ietf.org/api/v1/name/meetingtypename/
    #   https://datatracker.ietf.org/api/v1/name/grouptypename/
    #   https://datatracker.ietf.org/api/v1/name/draftsubmissionstatename/
    #   https://datatracker.ietf.org/api/v1/name/rolename/


    def document_type(self, doctype_uri: str):
        """
        Lookup information about a document type in the datatracker.

        Parameters:
            doctype_uri : a URI of the form, e.g., "/api/v1/name/doctypename/draft/",
                          as returned by document_types() or the "type" field of the
                          return from a call to document().

        Returns:
            A DocumentType object
        """
        assert doctype_uri.startswith("/api/v1/name/doctypename/") and doctype_uri.endswith("/")
        response = self.session.get(self.base_url + doctype_uri, verify=True)
        if response.status_code == 200:
            return Pavlova().from_mapping(response.json(), DocumentType)
        else:
            return None


    def document_types(self):
        """
        A generator returning possible document types.

        Parameters:
            none

        Returns:
            A sequence of DocumentType objects, as returned by document_type()
        """
        url = "/api/v1/name/doctypename/"
        while url != None:
            r = self.session.get(self.base_url + url, verify=True)
            meta = r.json()['meta']
            objs = r.json()['objects']
            url  = meta['next']
            for obj in objs:
                yield Pavlova().from_mapping(obj, DocumentType)


    def stream(self, stream_uri: str):
        """
        Lookup information about a document stream in the datatracker.

        Parameters:
            stream_uri : a URI of the form, e.g., "/api/v1/name/streamname/.../"

        Returns:
            A Stream object
        """
        assert stream_uri.startswith("/api/v1/name/streamname/") and stream_uri.endswith("/")
        response = self.session.get(self.base_url + stream_uri, verify=True)
        if response.status_code == 200:
            return Pavlova().from_mapping(response.json(), Stream)
        else:
            return None


    def streams(self):
        """
        A generator returning possible document streams.

        Parameters:
            none

        Returns:
            A sequence of Stream objects, as returned by stream()
        """
        url = "/api/v1/name/streamname/"
        while url != None:
            r = self.session.get(self.base_url + url, verify=True)
            meta = r.json()['meta']
            objs = r.json()['objects']
            url  = meta['next']
            for obj in objs:
                yield Pavlova().from_mapping(obj, Stream)


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

    def group(self, group_id):
        # FIXME: add documentation
        api_url  = "/api/v1/group/group/%d/" % (group_id) 
        response = self.session.get(self.base_url + api_url, verify=True)
        if response.status_code == 200:
            return Pavlova().from_mapping(response.json(), Group)
        else:
            return None

    def group_from_acronym(self, acronym) -> Group:
        # FIXME: add documentation
        api_url  = "/api/v1/group/group/?acronym=" + acronym
        response = self.session.get(self.base_url + api_url, verify=True)
        if response.status_code == 200:
            return Pavlova().from_mapping(response.json()["objects"][0], Group)
        else:
            return None

    def groups(self, since="1970-01-01T00:00:00",
                     until="2038-01-19T03:14:07",
                     name_contains=None,
                     state=None,
                     parent:Group=None) -> Iterator[Group]:
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
        api_url = "/api/v1/group/group/?time__gt=" + since + "&time__lt=" + until
        if name_contains != None:
            api_url = api_url + "&name__contains=" + name_contains
        if state != None:
            api_url = api_url + "&state=" + state
        if parent != None:
            api_url = api_url + "&parent=" + str(parent.id)
        while api_url != None:
            r = self.session.get(self.base_url + api_url, verify=True)
            meta = r.json()['meta']
            objs = r.json()['objects']
            api_url = meta['next']
            for obj in objs:
                yield Pavlova().from_mapping(obj, Group)



    def group_states(self) -> Iterator[GroupState]:
        """
        A generator returning possible group states.

        Parameters:
            none

        Returns:
            A sequence of Stream objects, as returned by stream()
        """
        url = "/api/v1/name/groupstatename/"
        while url != None:
            r = self.session.get(self.base_url + url, verify=True)
            meta = r.json()['meta']
            objs = r.json()['objects']
            url  = meta['next']
            for obj in objs:
                yield Pavlova().from_mapping(obj, GroupState)
        

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
    #   ...

    def meetings(self, since="1970-01-01T00:00:00", until="2038-01-19T03:14:07") -> Iterator[Meeting]:
        """
        A generator returning information about meetings.

        Parameters:
           since     -- Only return meetings with timestamp after this
           until     -- Only return meetings with timestamp before this

        Returns:
            An iterator of Meeting objects
        """
        url = "/api/v1/meeting/meeting/?time__gt=" + since + "&time__lt=" + until 
        while url != None:
            r = self.session.get(self.base_url + url, verify=True)
            meta = r.json()['meta']
            objs = r.json()['objects']
            url  = meta['next']
            for obj in objs:
                yield Pavlova().from_mapping(obj, Meeting)

# =================================================================================================================================
# Unit tests:

class TestDatatracker(unittest.TestCase):
    def test_email(self):
        dt = DataTracker()
        e  = dt.email("csp@csperkins.org")
        self.assertEqual(e.resource_uri, "/api/v1/person/email/csp@csperkins.org/")
        self.assertEqual(e.address,      "csp@csperkins.org")
        self.assertEqual(e.person,       "/api/v1/person/person/20209/")
        self.assertEqual(e.time,         "1970-01-01T23:59:59")
        self.assertEqual(e.origin,       "author: draft-ietf-taps-transport-security")
        self.assertEqual(e.primary,      True)
        self.assertEqual(e.active,       True)


    def test_person_from_email(self):
        dt = DataTracker()
        p  = dt.person_from_email("csp@csperkins.org")
        self.assertEqual(p.resource_uri, "/api/v1/person/person/20209/")


    def test_person_person(self):
        dt = DataTracker()
        p  = dt.person("/api/v1/person/person/20209/")
        self.assertEqual(p.id,              20209)
        self.assertEqual(p.resource_uri,    "/api/v1/person/person/20209/")
        self.assertEqual(p.name,            "Colin Perkins")
        self.assertEqual(p.name_from_draft, "Colin Perkins")
        self.assertEqual(p.ascii,           "Colin Perkins")
        self.assertEqual(p.ascii_short,     None)
        self.assertEqual(p.user,            "")
        self.assertEqual(p.time,            "2012-02-26T00:03:54")
        self.assertEqual(p.photo,           "https://www.ietf.org/lib/dt/media/photo/Colin-Perkins-sm.jpg")
        self.assertEqual(p.photo_thumb,     "https://www.ietf.org/lib/dt/media/photo/Colin-Perkins-sm_PMIAhXi.jpg")
        self.assertEqual(p.biography,       "Colin Perkins is a Senior Lecturer (Associate Professor) in the School of Computing Science at the University of Glasgow. His research interests are on transport protocols for real-time and interactive multimedia, and on network protocol design, implementation, and specification. He’s been a participant in the IETF and IRTF since 1996, working primarily in the transport area where he co-chairs the RMCAT working group and is a past chair of the AVT and MMUSIC working groups, and in related IRTF research groups. He proposed and co-chaired the first Applied Networking Research Workshop (ANRW), and has been a long-term participant in the Applied Networking Research Prize (ANRP) awarding committee. He received his BEng in Electronic Engineering in 1992, and my PhD in 1996, both from the Department of Electronics at the University of York.")
        self.assertEqual(p.consent,         True)

    def test_person_email(self):
        dt = DataTracker()
        p  = dt.person("/api/v1/person/email/csp@csperkins.org/")
        self.assertEqual(p.resource_uri,    "/api/v1/person/person/20209/")


#    def test_people(self):
#        dt = DataTracker()
#        for person in list(dt.people(since="2018-04-01T00:00:00", until="2018-04-30T23:59:59")):
#            print(person["resource_uri"])


    def test_document_draft(self):
        dt = DataTracker()
        d  = dt.document("/api/v1/doc/document/draft-ietf-avt-rtp-new/")
        self.assertEqual(d.resource_uri, "/api/v1/doc/document/draft-ietf-avt-rtp-new/")
        self.assertEqual(d.time, "2015-10-14T13:49:52")
        self.assertEqual(d.notify, "magnus.westerlund@ericsson.com, csp@csperkins.org")
        self.assertEqual(d.expires, "2003-09-08T00:00:12")
        self.assertEqual(d.type, "/api/v1/name/doctypename/draft/")
        self.assertEqual(d.rev, "12")
        self.assertEqual(d.abstract, "This memorandum describes RTP, the real-time transport protocol.  RTP provides end-to-end network transport functions suitable for applications transmitting real-time data, such as audio, video or simulation data, over multicast or unicast network services.  RTP does not address resource reservation and does not guarantee quality-of- service for real-time services.  The data transport is augmented by a control protocol (RTCP) to allow monitoring of the data delivery in a manner scalable to large multicast networks, and to provide minimal control and identification functionality.  RTP and RTCP are designed to be independent of the underlying transport and network layers.  The protocol supports the use of RTP-level translators and mixers.  Most of the text in this memorandum is identical to RFC 1889 which it obsoletes.  There are no changes in the packet formats on the wire, only changes to the rules and algorithms governing how the protocol is used.  The biggest change is an enhancement to the scalable timer algorithm for calculating when to send RTCP packets in order to minimize transmission in excess of the intended rate when many participants join a session simultaneously. [STANDARDS-TRACK]")
        self.assertEqual(d.internal_comments, "")
        self.assertEqual(d.states, ["/api/v1/doc/state/3/", "/api/v1/doc/state/7/"])
        self.assertEqual(d.ad, "/api/v1/person/person/2515/")
        self.assertEqual(d.group, "/api/v1/group/group/941/")
        self.assertEqual(d.stream, "/api/v1/name/streamname/ietf/")
        self.assertEqual(d.rfc, 3550)
        self.assertEqual(d.intended_std_level, "/api/v1/name/intendedstdlevelname/std/")
        self.assertEqual(d.std_level, "/api/v1/name/stdlevelname/std/")
        self.assertEqual(d.external_url, "")
        self.assertEqual(d.order, 1)
        self.assertEqual(d.shepherd, None)
        self.assertEqual(d.note, "")
        self.assertEqual(d.submissions, [])
        self.assertEqual(d.tags, ["/api/v1/name/doctagname/app-min/", "/api/v1/name/doctagname/errata/"])
        self.assertEqual(d.words, 34861)
        self.assertEqual(d.uploaded_filename, "")
        self.assertEqual(d.pages, 104)
        self.assertEqual(d.name, "draft-ietf-avt-rtp-new")
        self.assertEqual(d.title, "RTP: A Transport Protocol for Real-Time Applications")
        self.assertEqual(d.derive_document_url(), "https://www.ietf.org/archive/id/draft-ietf-avt-rtp-new-12.txt")
        self.assertEqual(dt.session.get(d.derive_document_url()).status_code, 200)

    def test_document_agenda(self):
        dt = DataTracker()
        d  = dt.document("/api/v1/doc/document/agenda-90-precis/")
        self.assertEqual(d.resource_uri,          "/api/v1/doc/document/agenda-90-precis/")
        self.assertEqual(d.derive_document_url(), "https://datatracker.ietf.org/meeting/90/materials/agenda-90-precis.txt")
        self.assertEqual(d.uploaded_filename,     "agenda-90-precis.txt")
        self.assertEqual(dt.session.get(d.derive_document_url()).status_code, 200)

    def test_document_minutes(self):
        dt = DataTracker()
        d  = dt.document("/api/v1/doc/document/minutes-89-cfrg/")
        self.assertEqual(d.resource_uri,          "/api/v1/doc/document/minutes-89-cfrg/")
        self.assertEqual(d.derive_document_url(), "https://datatracker.ietf.org/meeting/89/materials/minutes-89-cfrg.txt")
        self.assertEqual(d.uploaded_filename,     "minutes-89-cfrg.txt")
        self.assertEqual(dt.session.get(d.derive_document_url()).status_code, 200)

    def test_document_bluesheets(self):
        dt = DataTracker()
        d  = dt.document("/api/v1/doc/document/bluesheets-95-xrblock-01/")
        self.assertEqual(d.resource_uri,          "/api/v1/doc/document/bluesheets-95-xrblock-01/")
        self.assertEqual(d.derive_document_url(), "https://www.ietf.org/proceedings/95/bluesheets/bluesheets-95-xrblock-01.pdf")
        self.assertEqual(d.uploaded_filename,     "bluesheets-95-xrblock-01.pdf")
        self.assertEqual(dt.session.get(d.derive_document_url()).status_code, 200)

    def test_document_charter(self):
        dt = DataTracker()
        d  = dt.document("/api/v1/doc/document/charter-ietf-vgmib/")
        self.assertEqual(d.resource_uri,          "/api/v1/doc/document/charter-ietf-vgmib/")
        self.assertEqual(d.derive_document_url(), "https://www.ietf.org/charter/charter-ietf-vgmib-01.txt")
        self.assertEqual(d.uploaded_filename,     "")
        self.assertEqual(dt.session.get(d.derive_document_url()).status_code, 200)

    def test_document_conflrev(self):
        dt = DataTracker()
        d  = dt.document("/api/v1/doc/document/conflict-review-kiyomoto-kcipher2/")
        self.assertEqual(d.resource_uri,          "/api/v1/doc/document/conflict-review-kiyomoto-kcipher2/")
        self.assertEqual(d.derive_document_url(), "https://www.ietf.org/cr/conflict-review-kiyomoto-kcipher2-00.txt")
        self.assertEqual(d.uploaded_filename,     "")
        self.assertEqual(dt.session.get(d.derive_document_url()).status_code, 200)

    def test_document_slides(self):
        dt = DataTracker()
        d  = dt.document("/api/v1/doc/document/slides-65-l2vpn-4/")
        self.assertEqual(d.resource_uri,          "/api/v1/doc/document/slides-65-l2vpn-4/")
        self.assertEqual(d.derive_document_url(), "https://www.ietf.org/proceedings/65/slides/l2vpn-4.pdf")
        self.assertEqual(d.uploaded_filename,     "l2vpn-4.pdf")
        self.assertEqual(dt.session.get(d.derive_document_url()).status_code, 200)

    def test_document_statchg(self):
        dt = DataTracker()
        d  = dt.document("/api/v1/doc/document/status-change-rfc3044-rfc3187-orig-urn-regs-to-historic/")
        self.assertEqual(d.resource_uri,          "/api/v1/doc/document/status-change-rfc3044-rfc3187-orig-urn-regs-to-historic/")
        self.assertEqual(d.derive_document_url(), "https://www.ietf.org/sc/status-change-rfc3044-rfc3187-orig-urn-regs-to-historic-00.txt")
        self.assertEqual(d.uploaded_filename,     "")
        self.assertEqual(dt.session.get(d.derive_document_url()).status_code, 200)

    def test_document_liaison(self):
        dt = DataTracker()
        d  = dt.document("/api/v1/doc/document/liaison-2012-05-31-3gpp-mmusic-on-rtcp-bandwidth-negotiation-attachment-1/")
        self.assertEqual(d.resource_uri,          "/api/v1/doc/document/liaison-2012-05-31-3gpp-mmusic-on-rtcp-bandwidth-negotiation-attachment-1/")
        self.assertEqual(d.derive_document_url(), "https://www.ietf.org/lib/dt/documents/LIAISON/liaison-2012-05-31-3gpp-mmusic-on-rtcp-bandwidth-negotiation-attachment-1.doc")
        self.assertEqual(d.uploaded_filename,     "liaison-2012-05-31-3gpp-mmusic-on-rtcp-bandwidth-negotiation-attachment-1.doc")
        self.assertEqual(dt.session.get(d.derive_document_url()).status_code, 200)

    def test_document_liai_att(self):
        dt = DataTracker()
        d  = dt.document("/api/v1/doc/document/liaison-2004-08-23-itu-t-ietf-liaison-statement-to-ietf-and-itu-t-study-groups-countering-spam-pdf-version-attachment-1/")
        self.assertEqual(d.resource_uri,          "/api/v1/doc/document/liaison-2004-08-23-itu-t-ietf-liaison-statement-to-ietf-and-itu-t-study-groups-countering-spam-pdf-version-attachment-1/")
        self.assertEqual(d.derive_document_url(), "https://www.ietf.org/lib/dt/documents/LIAISON/file39.pdf")
        self.assertEqual(d.uploaded_filename,     "file39.pdf")
        self.assertEqual(dt.session.get(d.derive_document_url()).status_code, 200)

    def test_document_recording(self):
        dt = DataTracker()
        d  = dt.document("/api/v1/doc/document/recording-94-taps-1/")
        self.assertEqual(d.resource_uri,          "/api/v1/doc/document/recording-94-taps-1/")
        self.assertEqual(d.derive_document_url(), "https://www.ietf.org/audio/ietf94/ietf94-room304-20151103-1520.mp3")
        self.assertEqual(d.uploaded_filename,     "")
        # Downloading the MP3 is expensive, so check a HEAD request instead:
        self.assertEqual(dt.session.head(d.derive_document_url()).status_code, 200)

    def test_document_review(self):
        dt = DataTracker()
        d  = dt.document("/api/v1/doc/document/review-bchv-rfc6890bis-04-genart-lc-kyzivat-2017-02-28/")
        self.assertEqual(d.resource_uri,          "/api/v1/doc/document/review-bchv-rfc6890bis-04-genart-lc-kyzivat-2017-02-28/")
        self.assertEqual(d.derive_document_url(), "https://datatracker.ietf.org/doc/review-bchv-rfc6890bis-04-genart-lc-kyzivat-2017-02-28")
        self.assertEqual(d.external_url,          "")
        self.assertEqual(d.uploaded_filename,     "")
        self.assertEqual(dt.session.get(d.derive_document_url()).status_code, 200)

    def test_document_shepwrit(self):
        dt = DataTracker()
        for d in dt.documents(doctype="shepwrit"):
            self.fail("shepwrit is not used, so this should return no documents")

#    def test_documents(self):
#        dt = DataTracker()
#        documents = list(dt.documents(since="2007-01-01T00:00:00", until="2007-12-31T23:59:59", doctype="draft", group="941"))

    def test_document_from_draft(self):
        dt = DataTracker()
        d  = dt.document_from_draft("draft-ietf-avt-rtp-new")
        self.assertEqual(d.resource_uri, "/api/v1/doc/document/draft-ietf-avt-rtp-new/")

    def test_document_from_rfc(self):
        dt = DataTracker()
        d  = dt.document_from_rfc("rfc3550")
        self.assertEqual(d.resource_uri, "/api/v1/doc/document/draft-ietf-avt-rtp-new/")

    def test_documents_from_bcp(self):
        dt = DataTracker()
        d  = dt.documents_from_bcp("bcp205")
        self.assertEqual(len(d), 1)
        self.assertEqual(d[0].resource_uri, "/api/v1/doc/document/draft-sheffer-rfc6982bis/")

    def test_documents_from_std(self):
        dt = DataTracker()
        d  = dt.documents_from_std("std68")
        self.assertEqual(len(d), 1)
        self.assertEqual(d[0].resource_uri, "/api/v1/doc/document/draft-crocker-rfc4234bis/")

    def test_document_state(self):
        dt = DataTracker()
        s = dt.document_state('/api/v1/doc/state/7/')
        self.assertEqual(s.desc,         'The ID has been published as an RFC.')
        self.assertEqual(s.id,           7)
        self.assertEqual(s.name,         'RFC Published')
        self.assertEqual(s.next_states,  ['/api/v1/doc/state/8/'])
        self.assertEqual(s.order,        32)
        self.assertEqual(s.resource_uri, '/api/v1/doc/state/7/')
        self.assertEqual(s.slug,         'pub')
        self.assertEqual(s.type,         '/api/v1/doc/statetype/draft-iesg/')
        self.assertEqual(s.used,         True)

    def test_document_states(self):
        dt = DataTracker()
        states = list(dt.document_states(statetype="draft-rfceditor"))
        self.assertEqual(len(states), 18)
        self.assertEqual(states[ 0].name, 'AUTH')
        self.assertEqual(states[ 1].name, 'AUTH48')
        self.assertEqual(states[ 2].name, 'EDIT')
        self.assertEqual(states[ 3].name, 'IANA')
        self.assertEqual(states[ 4].name, 'IESG')
        self.assertEqual(states[ 5].name, 'ISR')
        self.assertEqual(states[ 6].name, 'ISR-AUTH')
        self.assertEqual(states[ 7].name, 'REF')
        self.assertEqual(states[ 8].name, 'RFC-EDITOR')
        self.assertEqual(states[ 9].name, 'TO')
        self.assertEqual(states[10].name, 'MISSREF')
        self.assertEqual(states[11].name, 'AUTH48-DONE')
        self.assertEqual(states[12].name, 'AUTH48-DONE')
        self.assertEqual(states[13].name, 'EDIT')
        self.assertEqual(states[14].name, 'IANA')
        self.assertEqual(states[15].name, 'IESG')
        self.assertEqual(states[16].name, 'ISR-AUTH')
        self.assertEqual(states[17].name, 'Pending')

    def test_document_state_types(self):
        dt = DataTracker()
        st = list(dt.document_state_types())
        self.assertEqual(len(st), 23)
        self.assertEqual(st[ 0].slug, 'draft')
        self.assertEqual(st[ 1].slug, 'draft-iesg')
        self.assertEqual(st[ 2].slug, 'draft-iana')
        self.assertEqual(st[ 3].slug, 'draft-rfceditor')
        self.assertEqual(st[ 4].slug, 'draft-stream-ietf')
        self.assertEqual(st[ 5].slug, 'draft-stream-irtf')
        self.assertEqual(st[ 6].slug, 'draft-stream-ise')
        self.assertEqual(st[ 7].slug, 'draft-stream-iab')
        self.assertEqual(st[ 8].slug, 'slides')
        self.assertEqual(st[ 9].slug, 'minutes')
        self.assertEqual(st[10].slug, 'agenda')
        self.assertEqual(st[11].slug, 'liai-att')
        self.assertEqual(st[12].slug, 'charter')
        self.assertEqual(st[13].slug, 'conflrev')
        self.assertEqual(st[14].slug, 'draft-iana-action')
        self.assertEqual(st[15].slug, 'draft-iana-review')
        self.assertEqual(st[16].slug, 'statchg')
        self.assertEqual(st[17].slug, 'recording')
        self.assertEqual(st[18].slug, 'bluesheets')
        self.assertEqual(st[19].slug, 'reuse_policy')
        self.assertEqual(st[20].slug, 'review')
        self.assertEqual(st[21].slug, 'liaison')
        self.assertEqual(st[22].slug, 'shepwrit')

    def test_submission(self):
        dt = DataTracker()
        s  = dt.submission("/api/v1/submit/submission/2402/")
        self.assertEqual(s.abstract,        "Internet technical specifications often need to define a formal\nsyntax.  Over the years, a modified version of Backus-Naur Form\n(BNF), called Augmented BNF (ABNF), has been popular among many\nInternet specifications.  The current specification documents ABNF.\nIt balances compactness and simplicity, with reasonable\nrepresentational power.  The differences between standard BNF and\nABNF involve naming rules, repetition, alternatives, order-\nindependence, and value ranges.  This specification also supplies\nadditional rule definitions and encoding for a core lexical analyzer\nof the type common to several Internet specifications.")
        self.assertEqual(s.access_key,      "f77d08da6da54f3cbecca13d31646be8")
        self.assertEqual(s.auth_key,        "fMm6hur5dJ7gV58x5SE0vkHUoDOrSuSF")
        self.assertEqual(s.authors,         "[{u'email': u'dcrocker@bbiw.net', u'name': u'Dave Crocker'}, {u'email': u'paul.overell@thus.net', u'name': u'Paul Overell'}]")
        self.assertEqual(s.checks,          ["/api/v1/submit/submissioncheck/386/"])
        self.assertEqual(s.document_date,   "2007-10-09")
        self.assertEqual(s.draft,           "/api/v1/doc/document/draft-crocker-rfc4234bis/")
        self.assertEqual(s.file_size,       27651)
        self.assertEqual(s.file_types,      ".txt,.xml,.pdf")
        self.assertEqual(s.first_two_pages, "\n\n\nNetwork Working Group                                    D. Crocker, Ed.\nInternet-Draft                               Brandenburg InternetWorking\nObsoletes: 4234 (if approved)                                 P. Overell\nIntended status: Standards Track                               THUS plc.\nExpires: April 11, 2008                                  October 9, 2007\n\n\n             Augmented BNF for Syntax Specifications: ABNF\n                      draft-crocker-rfc4234bis-01\n\nStatus of this Memo\n\n   By submitting this Internet-Draft, each author represents that any\n   applicable patent or other IPR claims of which he or she is aware\n   have been or will be disclosed, and any of which he or she becomes\n   aware will be disclosed, in accordance with Section 6 of BCP 79.\n\n   Internet-Drafts are working documents of the Internet Engineering\n   Task Force (IETF), its areas, and its working groups.  Note that\n   other groups may also distribute working documents as Internet-\n   Drafts.\n\n   Internet-Drafts are draft documents valid for a maximum of six months\n   and may be updated, replaced, or obsoleted by other documents at any\n   time.  It is inappropriate to use Internet-Drafts as reference\n   material or to cite them other than as \"work in progress.\"\n\n   The list of current Internet-Drafts can be accessed at\n   http://www.ietf.org/ietf/1id-abstracts.txt.\n\n   The list of Internet-Draft Shadow Directories can be accessed at\n   http://www.ietf.org/shadow.html.\n\n   This Internet-Draft will expire on April 11, 2008.\n\nCopyright Notice\n\n   Copyright (C) The IETF Trust (2007).\n\nAbstract\n\n   Internet technical specifications often need to define a formal\n   syntax.  Over the years, a modified version of Backus-Naur Form\n   (BNF), called Augmented BNF (ABNF), has been popular among many\n   Internet specifications.  The current specification documents ABNF.\n   It balances compactness and simplicity, with reasonable\n   representational power.  The differences between standard BNF and\n   ABNF involve naming rules, repetition, alternatives, order-\n\n\n\nCrocker & Overell        Expires April 11, 2008                 [page 1]\n\nInternet-Draft                    ABNF                      October 2007\n\n\n   independence, and value ranges.  This specification also supplies\n   additional rule definitions and encoding for a core lexical analyzer\n   of the type common to several Internet specifications.\n\n\nTable of Contents\n\n   1.  INTRODUCTION . . . . . . . . . . . . . . . . . . . . . . . . .  3\n   2.  RULE DEFINITION  . . . . . . . . . . . . . . . . . . . . . . .  3\n     2.1.  Rule Naming  . . . . . . . . . . . . . . . . . . . . . . .  3\n     2.2.  Rule Form  . . . . . . . . . . . . . . . . . . . . . . . .  4\n     2.3.  Terminal Values  . . . . . . . . . . . . . . . . . . . . .  4\n     2.4.  External Encodings . . . . . . . . . . . . . . . . . . . .  5\n   3.  OPERATORS  . . . . . . . . . . . . . . . . . . . . . . . . . .  6\n     3.1.  Concatenation:  Rule1 Rule2  . . . . . . . . . . . . . . .  6\n     3.2.  Alternatives:  Rule1 / Rule2 . . . . . . . . . . . . . . .  6\n     3.3.  Incremental Alternatives: Rule1 =/ Rule2 . . . . . . . . .  7\n     3.4.  Value Range Alternatives:  %c##-## . . . . . . . . . . . .  7\n     3.5.  Sequence Group:  (Rule1 Rule2) . . . . . . . . . . . . . .  8\n     3.6.  Variable Repetition:  *Rule  . . . . . . . . . . . . . . .  8\n     3.7.  Specific Repetition:  nRule  . . . . . . . . . . . . . . .  9\n     3.8.  Optional Sequence:  [RULE] . . . . . . . . . . . . . . . .  9\n     3.9.  Comment:  ; Comment  . . . . . . . . . . . . . . . . . . .  9\n     3.10. Operator Precedence  . . . . . . . . . . . . . . . . . . .  9\n   4.  ABNF DEFINITION OF ABNF  . . . . . . . . . . . . . . . . . . . 10\n   5.  SECURITY CONSIDERATIONS  . . . . . . . . . . . . . . . . . . . 11\n   6.  References . . . . . . . . . . . . . . . . . . . . . . . . . . 11\n     6.1.  Normative References . . . . . . . . . . . . . . . . . . . 11\n     6.2.  Informative References . . . . . . . . . . . . . . . . . . 12\n   Appendix A.  ACKNOWLEDGEMENTS  . . . . . . . . . . . . . . . . . . 12\n   Appendix B.  CORE ABNF OF ABNF . . . . . . . . . . . . . . . . . . 13\n     B.1.  Core Rules . . . . . . . . . . . . . . . . . . . . . . . . 13\n     B.2.  Common Encoding  . . . . . . . . . . . . . . . . . . . . . 14\n   Authors' Addresses . . . . . . . . . . . . . . . . . . . . . . . . 14\n   Intellectual Property and Copyright Statements . . . . . . . . . . 16\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\nCrocker & Overell        Expires April 11, 2008                 [page 2]")
        self.assertEqual(s.group,           "/api/v1/group/group/1027/")
        self.assertEqual(s.id,              2402)
        self.assertEqual(s.name,            "draft-crocker-rfc4234bis")
        self.assertEqual(s.note,            "")
        self.assertEqual(s.pages,           13)
        self.assertEqual(s.remote_ip,       "72.255.3.179")
        self.assertEqual(s.replaces,        "")
        self.assertEqual(s.resource_uri,    "/api/v1/submit/submission/2402/")
        self.assertEqual(s.rev,             "01")
        self.assertEqual(s.state,           "/api/v1/name/draftsubmissionstatename/posted/")
        self.assertEqual(s.submission_date, "2007-10-09")
        self.assertEqual(s.submitter,       "Dave Crocker")
        self.assertEqual(s.title,           "Augmented BNF for Syntax Specifications: ABNF")
        self.assertEqual(s.words,           None)

    def test_document_type(self):
        dt      = DataTracker()
        doctype = dt.document_type("/api/v1/name/doctypename/draft/")
        self.assertEqual(doctype.resource_uri, "/api/v1/name/doctypename/draft/")
        self.assertEqual(doctype.name,         "Draft")
        self.assertEqual(doctype.used,         True)
        self.assertEqual(doctype.prefix,       "draft")
        self.assertEqual(doctype.slug,         "draft")
        self.assertEqual(doctype.desc,         "")
        self.assertEqual(doctype.order,        0)

    def test_document_types(self):
        dt    = DataTracker()
        types = list(dt.document_types())
        self.assertEqual(len(types), 13)
        self.assertEqual(types[ 0].slug, "agenda")
        self.assertEqual(types[ 1].slug, "bluesheets")
        self.assertEqual(types[ 2].slug, "charter")
        self.assertEqual(types[ 3].slug, "conflrev")
        self.assertEqual(types[ 4].slug, "draft")
        self.assertEqual(types[ 5].slug, "liaison")
        self.assertEqual(types[ 6].slug, "liai-att")
        self.assertEqual(types[ 7].slug, "minutes")
        self.assertEqual(types[ 8].slug, "recording")
        self.assertEqual(types[ 9].slug, "review")
        self.assertEqual(types[10].slug, "shepwrit")
        self.assertEqual(types[11].slug, "slides")
        self.assertEqual(types[12].slug, "statchg")

    def test_stream(self):
        dt     = DataTracker()
        stream = dt.stream("/api/v1/name/streamname/irtf/")
        self.assertEqual(stream.desc,         "IRTF Stream")
        self.assertEqual(stream.name,         "IRTF")
        self.assertEqual(stream.order,        3)
        self.assertEqual(stream.resource_uri, "/api/v1/name/streamname/irtf/")
        self.assertEqual(stream.slug,         "irtf")
        self.assertEqual(stream.used,         True)

    def test_streams(self):
        dt      = DataTracker()
        streams = list(dt.streams())
        self.assertEqual(len(streams), 5)
        self.assertEqual(streams[ 0].slug, "ietf")
        self.assertEqual(streams[ 1].slug, "ise")
        self.assertEqual(streams[ 2].slug, "irtf")
        self.assertEqual(streams[ 3].slug, "iab")
        self.assertEqual(streams[ 4].slug, "legacy")

    def test_group(self):
        dt = DataTracker()
        group = dt.group(941)
        self.assertEqual(group.acronym,        "avt")
        self.assertEqual(group.ad,             None)
        self.assertEqual(group.charter,        "/api/v1/doc/document/charter-ietf-avt/")
        self.assertEqual(group.comments,       "")
        self.assertEqual(group.description,    "\n  The Audio/Video Transport Working Group was formed to specify a protocol \n  for real-time transmission of audio and video over unicast and multicast \n  UDP/IP. This is the Real-time Transport Protocol, RTP, along with its \n  associated profiles and payload formats.")
        self.assertEqual(group.id,             941)
        self.assertEqual(group.list_archive,   "https://mailarchive.ietf.org/arch/search/?email_list=avt")
        self.assertEqual(group.list_email,     "avt@ietf.org")
        self.assertEqual(group.list_subscribe, "https://www.ietf.org/mailman/listinfo/avt")
        self.assertEqual(group.name,           "Audio/Video Transport")
        self.assertEqual(group.parent,         "/api/v1/group/group/1683/")
        self.assertEqual(group.resource_uri,   "/api/v1/group/group/941/")
        self.assertEqual(group.state,          "/api/v1/name/groupstatename/conclude/")
        self.assertEqual(group.time,           "2011-12-09T12:00:00")
        self.assertEqual(group.type,           "/api/v1/name/grouptypename/wg/")
        self.assertEqual(group.unused_states,  [])
        self.assertEqual(group.unused_tags,    [])

    def test_group_from_acronym(self):
        dt = DataTracker()
        group = dt.group_from_acronym("avt")
        self.assertEqual(group.id, 941)

    def test_groups(self):
        dt = DataTracker()
        # FIXME: split into two tests? _timerange, and _namecontains -- testing without parameters not practical
        groups = list(dt.groups(since="2019-01-01T00:00:00", until="2019-01-31T23:59:59"))
        self.assertEqual(len(groups),  2)
        self.assertEqual(groups[0].id, 1897)
        self.assertEqual(groups[1].id, 2220)

    def test_group_states(self):
        dt = DataTracker()
        states = list(dt.group_states())
        self.assertEqual(len(states),  9)
        self.assertEqual(states[0].slug, "abandon")
        self.assertEqual(states[1].slug, "active")
        self.assertEqual(states[2].slug, "bof")
        self.assertEqual(states[3].slug, "bof-conc")
        self.assertEqual(states[4].slug, "conclude")
        self.assertEqual(states[5].slug, "dormant")
        self.assertEqual(states[6].slug, "proposed")
        self.assertEqual(states[7].slug, "replaced")
        self.assertEqual(states[8].slug, "unknown")

    def test_meetings(self):
        dt = DataTracker()
        for meeting in dt.meetings():
            print(meeting)


if __name__ == '__main__':
    unittest.main()

# =================================================================================================================================
# vim: set tw=0 ai:
