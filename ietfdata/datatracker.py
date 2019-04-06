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

import datetime
import glob
import json
import requests
import unittest

# =============================================================================
# Class to query the IETF Datatracker:

class DataTracker:
    """
    A class for interacting with the IETF DataTracker.
    """

    def __init__(self):
        self.session      = requests.Session()
        self.base_url     = "https://datatracker.ietf.org"
        self._people      = {}
        self._documents   = {}
        self._states      = {}
        self._submissions = {}
        self._groups      = {}

    def __del__(self):
        self.session.close()

    # Datatracker API endpoints returning information about people:
    # * https://datatracker.ietf.org/api/v1/person/person/                          - list of people
    # * https://datatracker.ietf.org/api/v1/person/person/20209/                    - info about person 20209
    # * https://datatracker.ietf.org/api/v1/person/email/csp@csperkins.org/         - map from email address to person
    #   https://datatracker.ietf.org/api/v1/person/personhistory/                   - ???
    #   https://datatracker.ietf.org/api/v1/person/personevent/                     - ???
    #   https://datatracker.ietf.org/api/v1/person/alias/                           - ???

    def person(self, person_id): 
        """
        Returns a JSON dictionary representing the person, for example:
            {
                "time" : "2012-02-26T00:03:54",
                "biography" : "",
                "ascii" : "Colin Perkins",
                "name_from_draft" : "Colin Perkins",
                "photo_thumb" : null,
                "id" : 20209,
                "photo" : null,
                "name" : "Colin Perkins",
                "resource_uri" : "/api/v1/person/person/20209/",
                "user" : "",
                "consent" : null,
                "ascii_short" : ""
            }
        """
        if person_id not in self._people:
            api_url  = "/api/v1/person/person/" + person_id
            response = self.session.get(self.base_url + api_url, verify=True)
            if response.status_code == 200:
                self._people[person_id] = response.json()
            else:
                return None
        return self._people[person_id]

    def person_from_email(self, person_email):
        """
        Returns the same JSON dictionary as the person() method, but found
        by email address rather than ID number.
        """
        api_url   = "/api/v1/person/email/" + person_email + "/"
        response  = self.session.get(self.base_url + api_url, verify=True)
        if response.status_code == 200:
            person_id = response.json()['person'].replace("/api/v1/person/person/", "").rstrip('/')
            return self.person(person_id)
        else:
            return None

    def people(self, since="1970-01-01T00:00:00", until="2038-01-19T03:14:07", name_contains=None):
        """
        A generator that returns JSON objects representing all people recorded
        in the datatracker. As of 29 April 2018, there are approximately 21500
        people recorded. The since and until parameters can be used to contrain
        the output to only entries with timestamps in a particular time range.
        If provided, name_contains filters based on the whether the name field
        contains the specified value.
        """
        api_url = "/api/v1/person/person/?time__gt=" + since + "&time__lt=" + until
        if name_contains != None:
            api_url = api_url + "&name__contains=" + name_contains
        while api_url != None:
            r = self.session.get(self.base_url + api_url, verify=True)
            meta = r.json()['meta']
            objs = r.json()['objects']
            api_url = meta['next']
            for obj in objs:
                self._people[obj['id']] = obj
                yield obj

    # Datatracker API endpoints returning information about documents:
    # * https://datatracker.ietf.org/api/v1/doc/document/                        - list of documents
    # * https://datatracker.ietf.org/api/v1/doc/document/draft-ietf-avt-rtp-new/ - info about document
    #   https://datatracker.ietf.org/api/v1/doc/docevent/                        - list of document events
    #   https://datatracker.ietf.org/api/v1/doc/docevent/?doc=...                - events for a document
    #   https://datatracker.ietf.org/api/v1/doc/docevent/?by=...                 - events by a person (as /api/v1/person/person)
    #   https://datatracker.ietf.org/api/v1/doc/docevent/?time=...               - events by time
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
    #   https://datatracker.ietf.org/api/v1/doc/documentauthor/?document=...     - authors of a document
    #   https://datatracker.ietf.org/api/v1/doc/documentauthor/?person=...       - documents by person (as /api/v1/person/person)
    #   https://datatracker.ietf.org/api/v1/doc/documentauthor/?email=...        - documents by person with particular email
    #   https://datatracker.ietf.org/api/v1/doc/relateddocument/?source=...      - documents that source draft relates to (references, replaces, etc)
    #   https://datatracker.ietf.org/api/v1/doc/relateddocument/?target=...      - documents that relate to target draft
    # * https://datatracker.ietf.org/api/v1/doc/docalias/rfcXXXX/                - draft that became the given RFC
    #   https://datatracker.ietf.org/api/v1/doc/docalias/bcpXXXX/                - draft that became the given BCP
    #   https://datatracker.ietf.org/api/v1/doc/docalias/stdXXXX/                - RFC that is the given STD
    # * https://datatracker.ietf.org/api/v1/doc/state/                           - Types of state a document can be in
    #   https://datatracker.ietf.org/api/v1/doc/ballottype/                      - Types of ballot that can be issued on a document
    #
    #   https://datatracker.ietf.org/api/v1/doc/relateddochistory/
    #   https://datatracker.ietf.org/api/v1/doc/dochistoryauthor/
    #   https://datatracker.ietf.org/api/v1/doc/initialreviewdocevent/
    #   https://datatracker.ietf.org/api/v1/doc/deletedevent/
    #   https://datatracker.ietf.org/api/v1/doc/addedmessageevent/
    #   https://datatracker.ietf.org/api/v1/doc/documenturl/
    #   https://datatracker.ietf.org/api/v1/doc/docreminder/
    # * https://datatracker.ietf.org/api/v1/doc/statetype/                       - Possible types of state for a document
    #   https://datatracker.ietf.org/api/v1/doc/editedauthorsdocevent/
    #   https://datatracker.ietf.org/api/v1/doc/dochistory/

    def __fix_document(self, document):
        if document['std_level'] != None:
            document['std_level'] = document['std_level'].replace("/api/v1/name/stdlevelname/", "").rstrip('/')
        if document['intended_std_level'] != None:
            document['intended_std_level'] = document['intended_std_level'].replace("/api/v1/name/intendedstdlevelname/", "").rstrip('/')
        if document['group'] != None:
            document['group']  = document['group'].replace("/api/v1/group/group/", "").rstrip('/')
        if document['type'] != None:
            document['type']   = document['type'].replace("/api/v1/name/doctypename/", "").rstrip('/')
        if document['stream'] != None:
            document['stream'] = document['stream'].replace("/api/v1/name/streamname/", "").rstrip('/')
        if document['ad'] != None:
            document['ad'] = document['ad'].replace("/api/v1/person/person/", "").rstrip('/')
        if document['shepherd'] != None:
            document['shepherd'] = document['shepherd'].replace("/api/v1/person/person/", "").rstrip('/')
        document['submissions'] = list(map(lambda s : s.replace("/api/v1/submit/submission/", "").rstrip('/'), document['submissions']))
        document['states']      = list(map(lambda s : s.replace("/api/v1/doc/state/",         "").rstrip('/'), document['states']))
        document['tags']        = list(map(lambda s : s.replace("/api/v1/name/doctagname/",   "").rstrip('/'), document['tags']))

        # Rewrite the external_url field to be an absolute, dereferencable, URL:
        if document['type'] == "agenda":
            meeting = document['name'].split("-")[1]
            if document["external_url"].startswith("agenda-" + meeting + "-"):
                new_url = "https://datatracker.ietf.org/meeting/" + meeting + "/materials/" + document["external_url"]
            else:
                new_url = "https://datatracker.ietf.org/meeting/" + meeting + "/materials/" + document["name"]
        elif document['type'] == "bluesheets":
            meeting = document['name'].split("-")[1]
            new_url = "https://www.ietf.org/proceedings/" + meeting + "/bluesheets/" + document["external_url"]
        elif document['type'] == "charter":
            new_url = "https://www.ietf.org/charter/" + document["name"] + "-" + document["rev"] + ".txt"
        elif document['type'] == "conflrev":
            new_url = "https://www.ietf.org/cr/" + document["name"] + "-" + document["rev"] + ".txt"
        elif document['type'] == "draft":
            new_url = "https://www.ietf.org/archive/id/" + document["name"] + "-" + document["rev"] + ".txt"
        elif document['type'] == "liaison":
            new_url = "https://www.ietf.org/lib/dt/documents/LIAISON/" + document["external_url"]
        elif document['type'] == "liai-att":
            new_url = "https://www.ietf.org/lib/dt/documents/LIAISON/" + document["external_url"]
        elif document['type'] == "minutes":
            meeting = document['name'].split("-")[1]
            new_url = "https://datatracker.ietf.org/meeting/" + meeting + "/materials/" + document["name"] + "-" + document["rev"]
        elif document['type'] == "recording":
            new_url = document["external_url"]
        elif document['type'] == "review":
            new_url = document["external_url"]
        elif document['type'] == "shepwrit":
            new_url = document["external_url"]
        elif document['type'] == "slides":
            new_url = "https://www.ietf.org/archive/id/" + document["name"] + "-" + document["rev"] + ".txt"
        elif document['type'] == "statchg":
            new_url = "https://www.ietf.org/sc/" + document["name"] + "-" + document["rev"] + ".txt"
        document['external_url'] = new_url

        return document

    def documents(self, since="1970-01-01T00:00:00", until="2038-01-19T03:14:07", doctype="", group=""):
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

        The group can be a group identifier, as used by the group() method, and
        will constrain the results to documents from the specified group.

        The JSON objects returned are the same format as those returned by the 
        document() method.
        """
        api_url   = "/api/v1/doc/document/?time__gt=" + since + "&time__lt=" + until 
        if doctype != "":
            api_url = api_url + "&type=" + doctype
        if group != "":
            api_url = api_url + "&group=" + group
        while api_url != None:
            r = self.session.get(self.base_url + api_url, verify=True)
            meta = r.json()['meta']
            objs = r.json()['objects']
            api_url = meta['next']
            for obj in objs:
                self._documents[obj['name']] = obj
                yield self.__fix_document(obj)

    def document(self, name):
        """
        Returns a JSON object representing a document identified by name, for example:
            {
               "states" : [ '1', '38' ],
               "rev" : "11",
               "name" : "draft-ietf-quic-transport",
               "intended_std_level" : "ps",
               "std_level" : null,
               "pages" : 105,
               "abstract" : "This document defines the core of the QUIC transport protocol...",
               "type" : "draft",
               "rfc" : null,
               "group" : "2161",
               "external_url" : "",
               "resource_uri" : "/api/v1/doc/document/draft-ietf-quic-transport/",
               "tags" : [],
               "shepherd" : null,
               "order" : 1,
               "stream" : "ietf",
               "expires" : "2018-10-19T16:10:12",
               "ad" : null,
               "notify" : "",
               "title" : "QUIC: A UDP-Based Multiplexed and Secure Transport",
               "words" : 24198,
               "internal_comments" : "",
               "submissions" : [
                  '82995', '83773', '85557', '86717', '87084', '88860',
                  '89569', '89982', '91554', '92517', '93617', '94830'
               ],
               "time" : "2018-04-17T16:10:12",
               "note" : ""
            }
        The document_state() method can be used to get additional information on states.
        The group() method can be used to get additional information on the group.
        The submissions() method can be used to get additional information on submissions.
        """
        if name not in self._documents:
            api_url  = "/api/v1/doc/document/" + name + "/"
            response = self.session.get(self.base_url + api_url, verify=True)
            if response.status_code == 200:
                self._documents[name] = self.__fix_document(response.json())
            else:
                return None
        return self._documents[name]

    def document_from_rfc(self, rfc):
        """
        Returns the document that became the specified RFC.
        The rfc parameter is of the form "rfc3550".
        """
        api_url  = "/api/v1/doc/docalias/" + rfc + "/"
        response = self.session.get(self.base_url + api_url, verify=True)
        if response.status_code == 200:
            name = response.json()['document'].replace("/api/v1/doc/document/", "").rstrip('/')
            return self.document(name)
        else:
            return None

    def document_state(self, state):
        """
        Returns a JSON object representing the state of a document, for example:
            {
              'desc': 'The ID has been published as an RFC.', 
              'id': 7, 
              'name': 'RFC Published', 
              'next_states': ['8'], 
              'order': 32, 
              'resource_uri': '/api/v1/doc/state/7/', 
              'slug': 'pub', 
              'type': 'draft-iesg', 
              'used': True
            }
        The state parameter is one of the 'states' from a document object.
        """
        if state not in self._states:
            api_url  = "/api/v1/doc/state/" + state
            response = self.session.get(self.base_url + api_url, verify=True)
            if response.status_code == 200:
                resp = response.json()
                resp['next_states'] = list(map(lambda s : s.replace("/api/v1/doc/state/", "").rstrip('/'), resp['next_states']))
                resp['type']        = resp['type'].replace("/api/v1/doc/statetype/", "").rstrip('/')
                self._states[state] = resp
            else:
                return None
        return self._states[state]

    def document_states(self, statetype=""):
        """
        A generator returning the possible states a document can be in.
        Each element is a state, as returned by document_state(). 
        The statetype parameter allows subsetting of the possible states,
        for example specifying statetype="draft-rfceditor" returns the
        states a document can be in during RFC Editor processing.
        """
        api_url   = "/api/v1/doc/state/"
        if statetype != "":
            api_url = api_url + "?type=" + statetype
        while api_url != None:
            r = self.session.get(self.base_url + api_url, verify=True)
            meta = r.json()['meta']
            objs = r.json()['objects']
            api_url = meta['next']
            for obj in objs:
                obj['next_states'] = list(map(lambda s : s.replace("/api/v1/doc/state/", "").rstrip('/'), obj['next_states']))
                obj['type']        = obj['type'].replace("/api/v1/doc/statetype/", "").rstrip('/')
                self._states[obj['id']] = obj
                yield obj

    def document_state_types(self):
        """
        A generator returning possible state types for a document.
        These are the possible values of the 'type' field in the 
        output of document_state(), or the statetype parameter to
        document_states().
        """
        api_url   = "/api/v1/doc/statetype/"
        while api_url != None:
            r = self.session.get(self.base_url + api_url, verify=True)
            meta = r.json()['meta']
            objs = r.json()['objects']
            api_url = meta['next']
            for obj in objs:
                yield obj['slug']

    def submission(self, submission):
        """
        Returns a JSON object giving information about a document submission.
        """
        if submission not in self._submissions:
            api_url = "/api/v1/submit/submission/" + submission + "/"
            response = self.session.get(self.base_url + api_url, verify=True)
            if response.status_code == 200:
                resp = response.json()
                resp['group'] = resp['group'].replace("/api/v1/group/group/", "").rstrip('/')
                # FIXME: there is more tidying that can be done here
                self._submissions[submission] = resp
            else:
                return None
        return self._submissions[submission]

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
        # FIXME
        pass

    def group_from_acronym(self, acronym):
        api_url  = "/api/v1/group/group/?acronym=" + acronym
        response = self.session.get(self.base_url + api_url, verify=True)
        if response.status_code == 200:
            return response.json()["objects"][0]
        else:
            return None

    def groups(self, since="1970-01-01T00:00:00", until="2038-01-19T03:14:07", name_contains=None):
        # FIXME: no tests for this
        """
        A generator that returns JSON objects representing all groups recorded
        in the datatracker. The since and until parameters can be used to contrain
        the output to only entries with timestamps in a particular time range.
        If provided, name_contains filters based on the whether the name field
        contains the specified value.
        """
        api_url = "/api/v1/group/group/?time__gt=" + since + "&time__lt=" + until
        if name_contains != None:
            api_url = api_url + "&name__contains=" + name_contains
        while api_url != None:
            r = self.session.get(self.base_url + api_url, verify=True)
            meta = r.json()['meta']
            objs = r.json()['objects']
            api_url = meta['next']
            for obj in objs:
                self._people[obj['id']] = obj
                yield obj

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

# =============================================================================
# Unit tests:

class TestDatatracker(unittest.TestCase):
    def test_person(self):
        dt = DataTracker()
        p1 = dt.person("20209")

    def test_person_from_email(self):
        dt = DataTracker()

    def test_people(self):
        dt = DataTracker()
        people = list(dt.people(since="2018-04-01T00:00:00", until="2018-04-30T23:59:59"))

    def test_document(self):
        dt = DataTracker()
        d1 = dt.document("draft-ietf-avt-rtp-cnames")

    def test_documents(self):
        dt = DataTracker()
        documents = list(dt.documents(since="2007-01-01T00:00:00", until="2007-12-31T23:59:59", doctype="draft", group="941"))

    def test_document_from_rfc(self):
        dt = DataTracker()
        d  = dt.document_from_rfc("rfc3550")

    def test_document_state(self):
        dt = DataTracker()
        s = dt.document_state('7')
        # self.assertEqual(s['desc'], 'The ID has been published as an RFC.')
        # self.assertEqual(s['id'], 7)
        # self.assertEqual(s['name'], 'RFC Published')
        # self.assertEqual(s['next_states'], ['8'])
        # self.assertEqual(s['order'], 32)
        # self.assertEqual(s['resource_uri'], '/api/v1/doc/state/7/')
        # self.assertEqual(s['slug'], 'pub')
        # self.assertEqual(s['type'], 'draft-iesg')
        # self.assertEqual(s['used'], True)

    def test_document_states(self):
        dt = DataTracker()
        states = list(dt.document_states(statetype="draft-rfceditor"))
        # self.assertEqual(states[ 0]['name'], 'AUTH')
        # self.assertEqual(states[ 1]['name'], 'AUTH48')
        # self.assertEqual(states[ 2]['name'], 'EDIT')
        # self.assertEqual(states[ 3]['name'], 'IANA')
        # self.assertEqual(states[ 4]['name'], 'IESG')
        # self.assertEqual(states[ 5]['name'], 'ISR')
        # self.assertEqual(states[ 6]['name'], 'ISR-AUTH')
        # self.assertEqual(states[ 7]['name'], 'REF')
        # self.assertEqual(states[ 8]['name'], 'RFC-EDITOR')
        # self.assertEqual(states[ 9]['name'], 'TO')
        # self.assertEqual(states[10]['name'], 'MISSREF')
        # self.assertEqual(states[11]['name'], 'AUTH48-DONE')
        # self.assertEqual(states[12]['name'], 'AUTH48-DONE')
        # self.assertEqual(states[13]['name'], 'EDIT')
        # self.assertEqual(states[14]['name'], 'IANA')
        # self.assertEqual(states[15]['name'], 'IESG')
        # self.assertEqual(states[16]['name'], 'ISR-AUTH')
        # self.assertEqual(states[17]['name'], 'Pending')

    def test_document_state_types(self):
        dt = DataTracker()
        st = list(dt.document_state_types())
        # self.assertEqual(st[ 0], 'draft')
        # self.assertEqual(st[ 1], 'draft-iesg')
        # self.assertEqual(st[ 2], 'draft-iana')
        # self.assertEqual(st[ 3], 'draft-rfceditor')
        # self.assertEqual(st[ 4], 'draft-stream-ietf')
        # self.assertEqual(st[ 5], 'draft-stream-irtf')
        # self.assertEqual(st[ 6], 'draft-stream-ise')
        # self.assertEqual(st[ 7], 'draft-stream-iab')
        # self.assertEqual(st[ 8], 'slides')
        # self.assertEqual(st[ 9], 'minutes')
        # self.assertEqual(st[10], 'agenda')
        # self.assertEqual(st[11], 'liai-att')
        # self.assertEqual(st[12], 'charter')
        # self.assertEqual(st[13], 'conflrev')
        # self.assertEqual(st[14], 'draft-iana-action')
        # self.assertEqual(st[15], 'draft-iana-review')
        # self.assertEqual(st[16], 'statchg')
        # self.assertEqual(st[17], 'recording')
        # self.assertEqual(st[18], 'bluesheets')
        # self.assertEqual(st[19], 'reuse_policy')
        # self.assertEqual(st[20], 'review')
        # self.assertEqual(st[21], 'liaison')
        # self.assertEqual(st[22], 'shepwrit')

    def test_submission(self):
        dt = DataTracker()
        sub = dt.submission('24225')

    def test_group_from_acronym(self):
        dt = DataTracker()
        group = dt.group_from_acronym("avt")
        #self.assertEqual(group['id'], 941)

if __name__ == '__main__':
    unittest.main()

# =============================================================================
