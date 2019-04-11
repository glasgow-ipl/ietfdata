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

from typing import List, Optional, Tuple, Dict, Iterator

import datetime
import glob
import json
import requests
import unittest

# =================================================================================================================================
# Classes representing objects in the datatracker:

class DTPerson:
    """
    A person in the datatracker.
    """
    person_id        : int            # 20209
    person_uri       : str            # "/api/v1/person/person/20209/"
    name             : str            # "Colin Perkins"
    name_from_draft  : str            # "Colin Perkins"
    name_ascii       : str            # "Colin Perkins"
    name_ascii_short : Optional[str]  # None
    photo            : Optional[str]  # "https://www.ietf.org/lib/dt/media/photo/Colin-Perkins-sm.jpg"
    photo_thumb      : Optional[str]  # "https://www.ietf.org/lib/dt/media/photo/Colin-Perkins-sm_PMIAhXi.jpg"
    user             : Optional[str]  #
    consent          : Optional[bool] # True
    timestamp        : str            # "2012-02-26T00:03:54"
    biography        : str            # "Colin Perkins is a..."

    def __init__(self, json):
        """
        Initialise based on the JSON supplied by the datatracker.
        """
        self.person_id        = json["id"]
        self.person_uri       = json["resource_uri"]
        self.name             = json["name"]
        self.name_from_draft  = json["name_from_draft"]
        self.name_ascii       = json["ascii"]
        self.name_ascii_short = json["ascii_short"]
        self.photo            = json["photo"]
        self.photo_thumb      = json["photo_thumb"]
        self.user             = json["user"]
        self.consent          = json["consent"]
        self.timestamp        = json["time"]
        self.biography        = json["biography"]
        assert self.person_uri.startswith("/api/v1/person/person/")

    def __str__(self) -> str:
        return "DTPerson {\n" \
             + "   person_id        = {}\n".format(self.person_id) \
             + "   person_uri       = {}\n".format(self.person_uri) \
             + "   name             = {}\n".format(self.name) \
             + "   name_from_draft  = {}\n".format(self.name_from_draft) \
             + "   name_ascii       = {}\n".format(self.name_ascii) \
             + "   name_ascii_short = {}\n".format(self.name_ascii_short) \
             + "   photo            = {}\n".format(self.photo) \
             + "   photo_thumb      = {}\n".format(self.photo_thumb) \
             + "   user             = {}\n".format(self.user) \
             + "   consent          = {}\n".format(self.consent) \
             + "   timestamp        = {}\n".format(self.timestamp) \
             + "   biography        = {}\n".format(self.biography) \
             + "}\n"


class DTEmail:
    """
    A mapping from an email address to a person.
    """
    email      : str   # "csp@csperkins.org"
    email_uri  : str   # "/api/v1/person/email/csp@csperkins.org/"
    person_uri : str   # "/api/v1/person/person/20209/" - suitable for use with person()
    origin     : str   # "author: draft-ietf-mmusic-rfc4566bis"
    timestamp  : str   # "1970-01-01T23:59:59"
    active     : bool  # True
    primary    : bool  # True

    def __init__(self, json):
        """
        Initialise based on the JSON supplied by the datatracker.
        """
        self.email      = json["address"]
        self.email_uri  = json["resource_uri"]
        self.person_uri = json["person"]
        self.origin     = json["origin"]
        self.timestamp  = json["time"]
        self.active     = json["active"]
        self.primary    = json["primary"]
        assert self. email_uri.startswith("/api/v1/person/email/")
        assert self.person_uri.startswith("/api/v1/person/person/")


    def __str__(self) -> str:
        return "DTEmail {\n" \
             + "   email      = {}\n".format(self.email) \
             + "   email_uri  = {}\n".format(self.email_uri) \
             + "   person_uri = {}\n".format(self.person_uri) \
             + "   origin     = {}\n".format(self.origin) \
             + "   timestamp  = {}\n".format(self.timestamp) \
             + "   active     = {}\n".format(self.active) \
             + "   primary    = {}\n".format(self.primary) \
             + "}\n"


class DTDocument:
    document_uri       : str           # "/api/v1/doc/document/draft-ietf-avt-rtp-new/"
    document_type      : Optional[str] # "draft"
    group_uri          : Optional[str] # "/api/v1/group/group/941/"
    std_level          : Optional[str] # "std"
    intended_std_level : Optional[str] # "std"
    rfc                : str           # "3550"
    timestamp          : str           # "2015-10-14T13:49:52"
    note               : str           # ""
    rev                : str           # "12"
    pages              : int           # 104
    words              : int           # 34861
    order              : int           # 1
    tags               : List[str]     # ["/api/v1/name/doctagname/app-min/", "/api/v1/name/doctagname/errata/"]
    area_director_uri  : Optional[str] # "/api/v1/person/person/2515/"
    shepherd           : Optional[str] # "/api/v1/person/email/..."? (see draft-ietf-roll-useofrplinfo)
    internal_comments  : str           # ""
    abstract           : str           # "This memorandum describes RTP, the real-time transport protocol..."
    title              : str           # "RTP: A Transport Protocol for Real-Time Applications"
    expires            : str           # "2003-09-08T00:00:12"
    notify             : str           # "magnus.westerlund@ericsson.com, csp@csperkins.org"
    name               : str           # "draft-ietf-avt-rtp-new"
    stream             : Optional[str] # "ietf"
    uploaded_filename  : str           # ""
    states             : List[str]     # ["/api/v1/doc/state/3/", "/api/v1/doc/state/7/"]
    submissions        : List[str]     # []
    external_url       : str           # ""

    def __init__(self, json):
        """
        Initialise based on the JSON supplied by the datatracker.
        """
        self.document_uri       = json["resource_uri"]
        self.document_type      = json["type"]
        self.group_uri          = json["group"]
        self.std_level          = json["std_level"]
        self.intended_std_level = json["intended_std_level"]
        self.rfc                = json["rfc"]
        self.timestamp          = json["time"]
        self.note               = json["note"]
        self.rev                = json["rev"]
        self.pages              = json["pages"]
        self.words              = json["words"]
        self.order              = json["order"]
        self.tags               = json["tags"]
        self.area_director_uri  = json["ad"]
        self.shepherd           = json["shepherd"]
        self.internal_comments  = json["internal_comments"]
        self.abstract           = json["abstract"]
        self.title              = json["title"]
        self.expires            = json["expires"]
        self.notify             = json["notify"]
        self.name               = json["name"]
        self.stream             = json["stream"]
        self.uploaded_filename  = json["uploaded_filename"]
        self.states             = json["states"]
        self.submissions        = json["submissions"]
        self.external_url       = json["external_url"]

        if self.document_type == "/api/v1/name/doctypename/agenda/":
            meeting = self.name.split("-")[1]
            if self.external_url.startswith("agenda-" + meeting + "-"):
                self.external_url = "https://datatracker.ietf.org/meeting/" + meeting + "/materials/" + self.external_url
            else:
                self.external_url = "https://datatracker.ietf.org/meeting/" + meeting + "/materials/" + self.name
        elif self.document_type == "/api/v1/name/doctypename/minutes/":
            assert self.external_url == "" # No external URL supplied, generate one
            meeting = self.name.split("-")[1]
            self.external_url = "https://datatracker.ietf.org/meeting/" + meeting + "/materials/" + self.name + "-" + self.rev
        elif self.document_type == "/api/v1/name/doctypename/bluesheets/":
            assert self.external_url == "" # No external URL supplied, generate one
            meeting = self.name.split("-")[1]
            self.external_url = "https://www.ietf.org/proceedings/" + meeting + "/bluesheets/" + self.external_url
        elif self.document_type == "/api/v1/name/doctypename/charter/":
            assert self.external_url == "" # No external URL supplied, generate one
            self.external_url = "https://www.ietf.org/charter/"    + self.name + "-" + self.rev + ".txt"
        elif self.document_type == "/api/v1/name/doctypename/conflrev/":
            assert self.external_url == "" # No external URL supplied, generate one
            self.external_url = "https://www.ietf.org/cr/"         + self.name + "-" + self.rev + ".txt"
        elif self.document_type == "/api/v1/name/doctypename/draft/":
            assert self.external_url == "" # No external URL supplied, generate one
            self.external_url = "https://www.ietf.org/archive/id/" + self.name + "-" + self.rev + ".txt"
        elif self.document_type == "/api/v1/name/doctypename/slides/":
            assert self.external_url == "" # No external URL supplied, generate one
            self.external_url = "https://www.ietf.org/archive/id/" + self.name + "-" + self.rev + ".txt"
        elif self.document_type == "/api/v1/name/doctypename/statchg/":
            assert self.external_url == "" # No external URL supplied, generate one
            self.external_url = "https://www.ietf.org/sc/"         + self.name + "-" + self.rev + ".txt"
        elif self.document_type == "/api/v1/name/doctypename/liaison/":
            assert self.external_url == "" # No external URL supplied, generate one
            self.external_url = "https://www.ietf.org/lib/dt/documents/LIAISON/" + self.external_url
        elif self.document_type == "/api/v1/name/doctypename/liai-att/":
            assert self.external_url == "" # No external URL supplied, generate one
            self.external_url = "https://www.ietf.org/lib/dt/documents/LIAISON/" + self.external_url
        elif self.document_type == "/api/v1/name/doctypename/recording/":
            pass
        elif self.document_type == "/api/v1/name/doctypename/review/":
            pass
        elif self.document_type == "/api/v1/name/doctypename/shepwrit/":
            pass
        else:
            raise NotImplementedError

        assert self.document_uri.startswith("/api/v1/doc/document/")
        assert self.area_director_uri is None or self.area_director_uri.startswith("/api/v1/person/person")
        assert self.shepherd          is None or self.shepherd.startswith("/api/v1/person/email")


    def __str__(self) -> str:
        return "DTDocument {\n" \
             + "   document_uri       = {}\n".format(self.document_uri) \
             + "   document_type      = {}\n".format(self.document_type) \
             + "   group_uri          = {}\n".format(self.group_uri) \
             + "   std_level          = {}\n".format(self.std_level) \
             + "   intended_std_level = {}\n".format(self.intended_std_level) \
             + "   rfc                = {}\n".format(self.rfc) \
             + "   timestamp          = {}\n".format(self.timestamp) \
             + "   note               = {}\n".format(self.note) \
             + "   rev                = {}\n".format(self.rev) \
             + "   pages              = {}\n".format(self.pages) \
             + "   words              = {}\n".format(self.words) \
             + "   order              = {}\n".format(self.order) \
             + "   tags               = {}\n".format(self.tags) \
             + "   area_director_uri  = {}\n".format(self.area_director_uri) \
             + "   shepherd           = {}\n".format(self.shepherd) \
             + "   internal_comments  = {}\n".format(self.internal_comments) \
             + "   abstract           = {}\n".format(self.abstract) \
             + "   title              = {}\n".format(self.title) \
             + "   expires            = {}\n".format(self.expires) \
             + "   notify             = {}\n".format(self.notify) \
             + "   name               = {}\n".format(self.name) \
             + "   stream             = {}\n".format(self.stream) \
             + "   uploaded_filename  = {}\n".format(self.uploaded_filename) \
             + "   states             = {}\n".format(self.states) \
             + "   submissions        = {}\n".format(self.submissions) \
             + "   external_url       = {}\n".format(self.external_url) \
             + "}\n"

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

    def email(self, email: str) -> Optional[DTEmail]:
        """
        Lookup an email address in the datatracker, returning a mapping from the email address to a Person.

        email : the email address to lookup
        """
        url      = self.base_url + "/api/v1/person/email/" + email + "/"
        response = self.session.get(url, verify=True)
        if response.status_code == 200:
            return DTEmail(response.json())
        else:
            return None


    def person(self, person_uri: str) -> Optional[DTPerson]: 
        """
        Lookup a Person in the datatracker.

        person_uri : a URI of the form "/api/v1/person/person/20209/"
        """
        assert person_uri.startswith("/api/v1/person/person/")
        url      = self.base_url + person_uri
        response = self.session.get(url, verify=True)
        if response.status_code == 200:
            return DTPerson(response.json())
        else:
            return None


    def people(self, since="1970-01-01T00:00:00", until="2038-01-19T03:14:07", name_contains=None) -> Iterator[DTPerson]:
        """
        A generator that returns people recorded in the datatracker. As of April
        2018, there are approximately 21500 people recorded. The since and until
        parameters can be used to contrain output to only entries with timestamp
        in a particular range. The name_contains paramter filters results based
        on whether the name field contains the specified value.
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
                yield DTPerson(obj)


    # Datatracker API endpoints returning information about documents:
    # * https://datatracker.ietf.org/api/v1/doc/document/                        - list of documents
    # * https://datatracker.ietf.org/api/v1/doc/document/draft-ietf-avt-rtp-new/ - info about document

    def document(self, document_uri) -> Optional[DTDocument]:
        """
        Lookup a document in the datatracker.

        document_uri : a URI of the form "/api/v1/doc/document/draft-ietf-avt-rtp-new/"
        """
        assert document_uri.startswith("/api/v1/doc/document/")
        url      = self.base_url + document_uri
        response = self.session.get(url, verify=True)
        if response.status_code == 200:
            return DTDocument(response.json())
        else:
            return None


    def documents(self, since="1970-01-01T00:00:00", until="2038-01-19T03:14:07", doctype=None, group_uri=None) -> Iterator[DTDocument]:
        """
        A generator that returns JSON objects representing all documents
        recorded in the datatracker. As of 29 April 2018, approximately
        84000 documents are recorded. The since and until parameters can
        be used to contrain output to only those entries with timestamps
        in a particular time range. 

        The doctype parameter can be one of:
             "agenda"     - Agenda
             "bluesheets" - Bluesheets
             "charter"    - Charter
             "conflrev"   - Conflict Review
             "draft"      - Draft
             "liaison"    - Liaison
             "liai-att"   - Liaison Attachment
             "minutes"    - Minutes
             "recording"  - Recording
             "review"     - Review
             "shepwrit"   - Shepherd's writeup
             "slides"     - Slides
             "statchg"    - Status Change
        and will constrain the type of document returned. 

        The group can be a group_uri, as used by the group() method, and
        will constrain the results to documents from the specified group.
        """
        url = self.base_url + "/api/v1/doc/document/?time__gt=" + since + "&time__lt=" + until 
        if doctype != None:
            url = url + "&type=" + doctype
        if group_uri != None:
            url = url + "&group=" + group_uri
        while url != None:
            r = self.session.get(url, verify=True)
            meta = r.json()['meta']
            objs = r.json()['objects']
            url  = meta['next']
            for obj in objs:
                yield DTDocument(obj)


    # Datatracker API endpoints returning information about documents aliases:
    # * https://datatracker.ietf.org/api/v1/doc/docalias/rfcXXXX/                - draft that became the given RFC
    #   https://datatracker.ietf.org/api/v1/doc/docalias/bcpXXXX/                - draft that became the given BCP
    #   https://datatracker.ietf.org/api/v1/doc/docalias/stdXXXX/                - RFC that is the given STD

    def document_for_rfc(self, rfc: str) -> Optional[DTDocument]:
        """
        Returns the document that became the specified RFC.
        The rfc parameter is of the form "rfc3550" or "RFC3550".
        """
        assert rfc.lower().startswith("rfc")
        url  = self.base_url + "/api/v1/doc/docalias/" + rfc.lower() + "/"
        response = self.session.get(url, verify=True)
        if response.status_code == 200:
            return self.document(response.json()['document'])
        else:
            return None


    # * https://datatracker.ietf.org/api/v1/doc/state/                           - Types of state a document can be in
    # * https://datatracker.ietf.org/api/v1/doc/statetype/                       - Possible types of state for a document

#    def document_state(self, state):
#        """
#        Returns a JSON object representing the state of a document, for example:
#            {
#              'desc': 'The ID has been published as an RFC.', 
#              'id': 7, 
#              'name': 'RFC Published', 
#              'next_states': ['8'], 
#              'order': 32, 
#              'resource_uri': '/api/v1/doc/state/7/', 
#              'slug': 'pub', 
#              'type': 'draft-iesg', 
#              'used': True
#            }
#        The state parameter is one of the 'states' from a document object.
#        """
#        api_url  = "/api/v1/doc/state/" + state
#        response = self.session.get(self.base_url + api_url, verify=True)
#        if response.status_code == 200:
#            resp = response.json()
#            resp['next_states'] = list(map(lambda s : s.replace("/api/v1/doc/state/", "").rstrip('/'), resp['next_states']))
#            resp['type']        = resp['type'].replace("/api/v1/doc/statetype/", "").rstrip('/')
#            return resp
#        else:
#            return None


#    def document_states(self, statetype=""):
#        """
#        A generator returning the possible states a document can be in.
#        Each element is a state, as returned by document_state(). 
#        The statetype parameter allows subsetting of the possible states,
#        for example specifying statetype="draft-rfceditor" returns the
#        states a document can be in during RFC Editor processing.
#        """
#        api_url   = "/api/v1/doc/state/"
#        if statetype != "":
#            api_url = api_url + "?type=" + statetype
#        while api_url != None:
#            r = self.session.get(self.base_url + api_url, verify=True)
#            meta = r.json()['meta']
#            objs = r.json()['objects']
#            api_url = meta['next']
#            for obj in objs:
#                obj['next_states'] = list(map(lambda s : s.replace("/api/v1/doc/state/", "").rstrip('/'), obj['next_states']))
#                obj['type']        = obj['type'].replace("/api/v1/doc/statetype/", "").rstrip('/')
#                yield obj


#    def document_state_types(self):
#        """
#        A generator returning possible state types for a document.
#        These are the possible values of the 'type' field in the 
#        output of document_state(), or the statetype parameter to
#        document_states().
#        """
#        api_url   = "/api/v1/doc/statetype/"
#        while api_url != None:
#            r = self.session.get(self.base_url + api_url, verify=True)
#            meta = r.json()['meta']
#            objs = r.json()['objects']
#            api_url = meta['next']
#            for obj in objs:
#                yield obj['slug']


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

#    def submission(self, submission):
#        """
#        Returns a JSON object giving information about a document submission.
#        """
#        api_url = "/api/v1/submit/submission/" + submission + "/"
#        response = self.session.get(self.base_url + api_url, verify=True)
#        if response.status_code == 200:
#            resp = response.json()
#            resp['group'] = resp['group'].replace("/api/v1/group/group/", "").rstrip('/')
#            # FIXME: there is more tidying that can be done here
#            return resp
#        else:
#            return None

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

#    def group(self, group_id):
#        # FIXME
#        pass

#    def group_from_acronym(self, acronym):
#        api_url  = "/api/v1/group/group/?acronym=" + acronym
#        response = self.session.get(self.base_url + api_url, verify=True)
#        if response.status_code == 200:
#            return response.json()["objects"][0]
#        else:
#            return None

#    def groups(self, since="1970-01-01T00:00:00", until="2038-01-19T03:14:07", name_contains=None):
#        # FIXME: no tests for this
#        """
#        A generator that returns JSON objects representing all groups recorded
#        in the datatracker. The since and until parameters can be used to contrain
#        the output to only entries with timestamps in a particular time range.
#        If provided, name_contains filters based on the whether the name field
#        contains the specified value.
#        """
#        api_url = "/api/v1/group/group/?time__gt=" + since + "&time__lt=" + until
#        if name_contains != None:
#            api_url = api_url + "&name__contains=" + name_contains
#        while api_url != None:
#            r = self.session.get(self.base_url + api_url, verify=True)
#            meta = r.json()['meta']
#            objs = r.json()['objects']
#            api_url = meta['next']
#            for obj in objs:
#                yield obj

    # Datatracker API endpoints returning information about meetings:
    #   https://datatracker.ietf.org/api/v1/meeting/meeting/                        - list of meetings
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

# =================================================================================================================================
# Unit tests:

class TestDatatracker(unittest.TestCase):
    def test_person(self):
        dt = DataTracker()
        p  = dt.person("/api/v1/person/person/20209")
        self.assertEqual(p.person_id,        20209)
        self.assertEqual(p.person_uri,       "/api/v1/person/person/20209/")
        self.assertEqual(p.name,             "Colin Perkins")
        self.assertEqual(p.name_from_draft,  "Colin Perkins")
        self.assertEqual(p.name_ascii,       "Colin Perkins")
        self.assertEqual(p.name_ascii_short, None)
        self.assertEqual(p.user,             "")
        self.assertEqual(p.timestamp,        "2012-02-26T00:03:54")
        self.assertEqual(p.photo,            "https://www.ietf.org/lib/dt/media/photo/Colin-Perkins-sm.jpg")
        self.assertEqual(p.photo_thumb,      "https://www.ietf.org/lib/dt/media/photo/Colin-Perkins-sm_PMIAhXi.jpg")
        self.assertEqual(p.biography,        "Colin Perkins is a Senior Lecturer (Associate Professor) in the School of Computing Science at the University of Glasgow. His research interests are on transport protocols for real-time and interactive multimedia, and on network protocol design, implementation, and specification. He’s been a participant in the IETF and IRTF since 1996, working primarily in the transport area where he co-chairs the RMCAT working group and is a past chair of the AVT and MMUSIC working groups, and in related IRTF research groups. He proposed and co-chaired the first Applied Networking Research Workshop (ANRW), and has been a long-term participant in the Applied Networking Research Prize (ANRP) awarding committee. He received his BEng in Electronic Engineering in 1992, and my PhD in 1996, both from the Department of Electronics at the University of York.")
        self.assertEqual(p.consent,          True)


    def test_email(self):
        dt = DataTracker()
        e  = dt.email("csp@csperkins.org")
        self.assertEqual(e.email,     "csp@csperkins.org")
        self.assertEqual(e.email_uri, "/api/v1/person/email/csp@csperkins.org/")
        self.assertEqual(e.person_uri,"/api/v1/person/person/20209/")
        self.assertEqual(e.origin,    "author: draft-ietf-mmusic-rfc4566bis")
        self.assertEqual(e.timestamp, "1970-01-01T23:59:59")
        self.assertEqual(e.active,    True)
        self.assertEqual(e.primary,   True)


#    def test_people(self):
#        dt = DataTracker()
#        for person in list(dt.people(since="2018-04-01T00:00:00", until="2018-04-30T23:59:59")):
#            print(person)


    def test_document(self):
        dt = DataTracker()
        d  = dt.document("/api/v1/doc/document/draft-ietf-mmusic-rfc4566bis/")
        print(d)

#    def test_documents(self):
#        dt = DataTracker()
#        documents = list(dt.documents(since="2007-01-01T00:00:00", until="2007-12-31T23:59:59", doctype="draft", group="941"))

    def test_document_for_rfc(self):
        dt = DataTracker()
        d  = dt.document_for_rfc("rfc3550")
        self.assertEqual(d.document_uri, "/api/v1/doc/document/draft-ietf-avt-rtp-new/")

#    def test_document_state(self):
#        dt = DataTracker()
#        s = dt.document_state('7')
#        self.assertEqual(s['desc'], 'The ID has been published as an RFC.')
#        self.assertEqual(s['id'], 7)
#        self.assertEqual(s['name'], 'RFC Published')
#        self.assertEqual(s['next_states'], ['8'])
#        self.assertEqual(s['order'], 32)
#        self.assertEqual(s['resource_uri'], '/api/v1/doc/state/7/')
#        self.assertEqual(s['slug'], 'pub')
#        self.assertEqual(s['type'], 'draft-iesg')
#        self.assertEqual(s['used'], True)

#    def test_document_states(self):
#        dt = DataTracker()
#        states = list(dt.document_states(statetype="draft-rfceditor"))
#        self.assertEqual(states[ 0]['name'], 'AUTH')
#        self.assertEqual(states[ 1]['name'], 'AUTH48')
#        self.assertEqual(states[ 2]['name'], 'EDIT')
#        self.assertEqual(states[ 3]['name'], 'IANA')
#        self.assertEqual(states[ 4]['name'], 'IESG')
#        self.assertEqual(states[ 5]['name'], 'ISR')
#        self.assertEqual(states[ 6]['name'], 'ISR-AUTH')
#        self.assertEqual(states[ 7]['name'], 'REF')
#        self.assertEqual(states[ 8]['name'], 'RFC-EDITOR')
#        self.assertEqual(states[ 9]['name'], 'TO')
#        self.assertEqual(states[10]['name'], 'MISSREF')
#        self.assertEqual(states[11]['name'], 'AUTH48-DONE')
#        self.assertEqual(states[12]['name'], 'AUTH48-DONE')
#        self.assertEqual(states[13]['name'], 'EDIT')
#        self.assertEqual(states[14]['name'], 'IANA')
#        self.assertEqual(states[15]['name'], 'IESG')
#        self.assertEqual(states[16]['name'], 'ISR-AUTH')
#        self.assertEqual(states[17]['name'], 'Pending')

#    def test_document_state_types(self):
#        dt = DataTracker()
#        st = list(dt.document_state_types())
#        self.assertEqual(st[ 0], 'draft')
#        self.assertEqual(st[ 1], 'draft-iesg')
#        self.assertEqual(st[ 2], 'draft-iana')
#        self.assertEqual(st[ 3], 'draft-rfceditor')
#        self.assertEqual(st[ 4], 'draft-stream-ietf')
#        self.assertEqual(st[ 5], 'draft-stream-irtf')
#        self.assertEqual(st[ 6], 'draft-stream-ise')
#        self.assertEqual(st[ 7], 'draft-stream-iab')
#        self.assertEqual(st[ 8], 'slides')
#        self.assertEqual(st[ 9], 'minutes')
#        self.assertEqual(st[10], 'agenda')
#        self.assertEqual(st[11], 'liai-att')
#        self.assertEqual(st[12], 'charter')
#        self.assertEqual(st[13], 'conflrev')
#        self.assertEqual(st[14], 'draft-iana-action')
#        self.assertEqual(st[15], 'draft-iana-review')
#        self.assertEqual(st[16], 'statchg')
#        self.assertEqual(st[17], 'recording')
#        self.assertEqual(st[18], 'bluesheets')
#        self.assertEqual(st[19], 'reuse_policy')
#        self.assertEqual(st[20], 'review')
#        self.assertEqual(st[21], 'liaison')
#        self.assertEqual(st[22], 'shepwrit')

#    def test_submission(self):
#        dt = DataTracker()
#        sub = dt.submission('24225')

#    def test_group_from_acronym(self):
#        dt = DataTracker()
#        group = dt.group_from_acronym("avt")
#        self.assertEqual(group['id'], 941)

if __name__ == '__main__':
    unittest.main()

# =================================================================================================================================
